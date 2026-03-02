"""
High-Accuracy Pollination Trainer
===================================
Targets 90-95% accuracy even with small datasets by using:
  - EfficientNet-B3 (beats ResNet50 on small datasets)
  - Heavy augmentation  
  - Full progressive unfreezing
  - Label smoothing
  - Cosine annealing with warm restarts
  - Test-time augmentation (TTA) at evaluation

Run:  python train_high_accuracy.py
"""

import os, copy, time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim import lr_scheduler
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, WeightedRandomSampler
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATA_DIR        = r'C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED'
SAVE_PATH       = r'C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth'

BATCH_SIZE      = 16      # smaller batch = better gradient noise for tiny datasets
NUM_EPOCHS      = 60      # enough epochs to converge
IMAGE_SIZE      = 224
NUM_CLASSES     = 3
LR_HEAD         = 3e-4    # learning rate for new fc layers
LR_BACKBONE     = 3e-5    # 10× lower for pretrained layers
WEIGHT_DECAY    = 1e-4
LABEL_SMOOTHING = 0.1     # regularisation: stops overconfident predictions
EARLY_STOP_PAT  = 12      # stop if val acc doesn't improve for N epochs
TTA_PASSES      = 5       # test-time augmentation inference passes

CLASS_NAMES = ['not_pollinated', 'pollinated', 'pollinating']

torch.manual_seed(42)
np.random.seed(42)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

# ─── TRANSFORMS ───────────────────────────────────────────────────────────────
# Very heavy augmentation — essential for <500 images per class
train_tf = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.6, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.4, contrast=0.4,
                           saturation=0.3, hue=0.08),
    transforms.RandomGrayscale(p=0.05),
    transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.2),          # randomly mask small patches
])

val_tf = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.CenterCrop(IMAGE_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# TTA transform (random crops at test time, results averaged)
tta_tf = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# ─── DATASETS ─────────────────────────────────────────────────────────────────
train_ds = datasets.ImageFolder(os.path.join(DATA_DIR, 'train'), train_tf)
val_ds   = datasets.ImageFolder(os.path.join(DATA_DIR, 'val'),   val_tf)
test_ds  = datasets.ImageFolder(os.path.join(DATA_DIR, 'test'),  val_tf)

print(f"\nDataset sizes:  train={len(train_ds)}  val={len(val_ds)}  test={len(test_ds)}")
print(f"Classes: {train_ds.classes}")

# Weighted sampler to handle class imbalance
labels = [s[1] for s in train_ds.samples]
class_counts = np.bincount(labels)
class_weights = 1.0 / class_counts
sample_weights = torch.tensor([class_weights[l] for l in labels], dtype=torch.float)
sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,
                      num_workers=0, pin_memory=True)
val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                      num_workers=0, pin_memory=True)
test_dl  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                      num_workers=0, pin_memory=True)

# ─── MODEL ────────────────────────────────────────────────────────────────────
def build_model():
    """EfficientNet-B3 — better accuracy/params ratio than ResNet50."""
    model = models.efficientnet_b3(weights='IMAGENET1K_V1')

    # Phase 1: freeze backbone, only train head
    for param in model.parameters():
        param.requires_grad = False

    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 256),
        nn.SiLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, NUM_CLASSES),
    )
    return model

model = build_model().to(device)
total  = sum(p.numel() for p in model.parameters())
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"\nModel: EfficientNet-B3")
print(f"  Total params     : {total:,}")
print(f"  Trainable params : {trainable:,}  ({100*trainable/total:.1f}%)")

# ─── LOSS / OPTIMISER ─────────────────────────────────────────────────────────
criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)

optimizer = optim.AdamW([
    {'params': model.classifier.parameters(), 'lr': LR_HEAD},
], weight_decay=WEIGHT_DECAY)

scheduler = lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer, T_0=10, T_mult=2, eta_min=1e-7)

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def evaluate(loader, tfm=None):
    """Standard accuracy evaluation. Pass tfm for TTA."""
    model.eval()
    correct = total_n = 0
    with torch.no_grad():
        for imgs, labels_b in loader:
            imgs, labels_b = imgs.to(device), labels_b.to(device)
            outputs = model(imgs)
            preds = outputs.argmax(1)
            correct  += (preds == labels_b).sum().item()
            total_n  += labels_b.size(0)
    return correct / total_n


def evaluate_tta(dataset, n_passes=TTA_PASSES):
    """Test-time augmentation: average softmax over N random crops."""
    model.eval()
    correct = total_n = 0
    # rebuild dataset with TTA transform
    tta_ds = datasets.ImageFolder(os.path.join(DATA_DIR, 'test'), tta_tf)
    with torch.no_grad():
        for idx in range(len(dataset)):
            img_path, true_label = dataset.samples[idx]
            img_orig = __import__('PIL').Image.open(img_path).convert('RGB')
            logits_sum = torch.zeros(NUM_CLASSES).to(device)
            for _ in range(n_passes):
                t = tta_tf(img_orig).unsqueeze(0).to(device)
                logits_sum += model(t).squeeze()
            pred = logits_sum.argmax().item()
            correct  += (pred == true_label)
            total_n  += 1
    return correct / total_n


# ─── PHASE 1: TRAIN HEAD ONLY ─────────────────────────────────────────────────
print("\n" + "="*60)
print("PHASE 1 — Train head only (5 epochs, backbone frozen)")
print("="*60)

best_acc   = 0.0
best_wts   = copy.deepcopy(model.state_dict())
no_improve = 0
history    = {'train_loss': [], 'val_acc': []}

for epoch in range(5):
    model.train()
    running_loss = 0.0
    for imgs, labels_b in train_dl:
        imgs, labels_b = imgs.to(device), labels_b.to(device)
        optimizer.zero_grad()
        loss = criterion(model(imgs), labels_b)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * imgs.size(0)

    train_loss = running_loss / len(train_ds)
    val_acc    = evaluate(val_dl)
    scheduler.step()

    if val_acc > best_acc:
        best_acc = val_acc
        best_wts = copy.deepcopy(model.state_dict())

    print(f"  Epoch {epoch+1:2d}/5  loss={train_loss:.4f}  val_acc={val_acc:.1%}")
    history['train_loss'].append(train_loss)
    history['val_acc'].append(val_acc)

# ─── PHASE 2: UNFREEZE FULL BACKBONE ────────────────────────────────────────
print("\n" + "="*60)
print("PHASE 2 — Full fine-tune (backbone unfrozen)")
print("="*60)

# Load best weights from phase 1
model.load_state_dict(best_wts)

# Unfreeze everything
for param in model.parameters():
    param.requires_grad = True

optimizer = optim.AdamW([
    {'params': model.features.parameters(), 'lr': LR_BACKBONE},
    {'params': model.classifier.parameters(), 'lr': LR_HEAD},
], weight_decay=WEIGHT_DECAY)

scheduler = lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer, T_0=10, T_mult=2, eta_min=1e-7)

for epoch in range(NUM_EPOCHS):
    model.train()
    running_loss = 0.0

    for imgs, labels_b in train_dl:
        imgs, labels_b = imgs.to(device), labels_b.to(device)
        optimizer.zero_grad()
        loss = criterion(model(imgs), labels_b)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        running_loss += loss.item() * imgs.size(0)

    train_loss = running_loss / len(train_ds)
    val_acc    = evaluate(val_dl)
    scheduler.step()

    improved = val_acc > best_acc
    if improved:
        best_acc    = val_acc
        best_wts    = copy.deepcopy(model.state_dict())
        no_improve  = 0
        # Save immediately
        torch.save({'epoch': epoch, 'model_state_dict': best_wts,
                    'accuracy': best_acc, 'class_names': CLASS_NAMES}, SAVE_PATH)
    else:
        no_improve += 1

    mark = "✓ BEST" if improved else ""
    print(f"  Epoch {epoch+1:3d}/{NUM_EPOCHS}  loss={train_loss:.4f}  "
          f"val_acc={val_acc:.1%}  best={best_acc:.1%}  {mark}")

    history['train_loss'].append(train_loss)
    history['val_acc'].append(val_acc)

    if no_improve >= EARLY_STOP_PAT:
        print(f"\n  Early stopping at epoch {epoch+1} (no improvement for {EARLY_STOP_PAT} epochs)")
        break

# ─── FINAL EVALUATION ─────────────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL EVALUATION")
print("="*60)

model.load_state_dict(best_wts)

# Standard test accuracy
test_acc = evaluate(test_dl)
print(f"\n  Standard test accuracy : {test_acc:.1%}")

# TTA test accuracy
print(f"  Running TTA ({TTA_PASSES} passes)…")
tta_acc = evaluate_tta(test_ds)
print(f"  TTA test accuracy      : {tta_acc:.1%}")

# Classification report
model.eval()
all_preds, all_labels = [], []
with torch.no_grad():
    for imgs, labels_b in test_dl:
        preds = model(imgs.to(device)).argmax(1).cpu()
        all_preds.extend(preds.numpy())
        all_labels.extend(labels_b.numpy())

print("\n" + classification_report(all_labels, all_preds, target_names=CLASS_NAMES))

# Confusion matrix
cm = confusion_matrix(all_labels, all_preds)
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(cm, cmap='Blues')
ax.set_xticks(range(NUM_CLASSES)); ax.set_yticks(range(NUM_CLASSES))
ax.set_xticklabels(CLASS_NAMES, rotation=30, ha='right')
ax.set_yticklabels(CLASS_NAMES)
for i in range(NUM_CLASSES):
    for j in range(NUM_CLASSES):
        ax.text(j, i, cm[i,j], ha='center', va='center',
                color='white' if cm[i,j] > cm.max()/2 else 'black',
                fontsize=14, fontweight='bold')
ax.set_xlabel('Predicted'); ax.set_ylabel('True')
ax.set_title(f'Confusion Matrix  (test acc={test_acc:.1%}, TTA={tta_acc:.1%})')
plt.colorbar(im); plt.tight_layout()
plt.savefig(r'C:\Users\Admin\Desktop\CAPS\confusion_matrix.png', dpi=150)
plt.show()
print(f"\nSaved confusion matrix → confusion_matrix.png")
print(f"Saved best model      → {SAVE_PATH}")

# Training curve
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
ax1.plot(history['train_loss']); ax1.set_title('Training Loss'); ax1.set_xlabel('Epoch')
ax2.plot(history['val_acc']);    ax2.set_title('Val Accuracy');  ax2.set_xlabel('Epoch')
ax2.axhline(0.9, color='green', linestyle='--', label='90% target')
ax2.legend()
plt.tight_layout()
plt.savefig(r'C:\Users\Admin\Desktop\CAPS\training_curve.png', dpi=150)
plt.show()
print("Saved training curve  → training_curve.png")
