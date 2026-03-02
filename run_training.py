"""
CPU-Optimized Pollination Trainer
===================================
Optimized settings for CPU training:
  - Image size 160px  (3-4x faster than 224px on CPU)
  - Batch size 32     (better CPU throughput)
  - 30 max epochs     (early stopping kicks in around 15-20)
  - EfficientNet-B3   (best accuracy/params for small datasets)
  - Label smoothing + MixUp + TTA
  - Auto-saves best checkpoint every time val_acc improves

Expected time on CPU:
  Phase 1 (5 epochs)  : ~10-15 min
  Phase 2 (≤30 epochs): ~30-60 min (early stop usually hits ~15 epochs)

Run:  python run_training.py
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
import matplotlib
matplotlib.use('Agg')   # non-interactive backend — works without display
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATA_DIR        = r'C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED'
SAVE_PATH       = r'C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth'
FINAL_PATH      = r'C:\Users\Admin\Desktop\CAPS\pollination_model.pth'

IMAGE_SIZE      = 160     # 160 vs 224 => ~2x fewer pixels => much faster on CPU
BATCH_SIZE      = 32      # larger batch = better CPU utilisation
NUM_EPOCHS      = 30      # plenty with early stopping
NUM_CLASSES     = 3
LR_HEAD         = 3e-4
LR_BACKBONE     = 3e-5
WEIGHT_DECAY    = 1e-4
LABEL_SMOOTHING = 0.1
EARLY_STOP_PAT  = 10      # stop if no improvement for 10 epochs
TTA_PASSES      = 3       # reduced for speed on CPU
PHASE1_EPOCHS   = 5

# Set True to resume Phase 2 from best_model_checkpoint.pth (skips Phase 1)
RESUME_FROM_CHECKPOINT = True

CLASS_NAMES = ['not_pollinated', 'pollinated', 'pollinating']

torch.manual_seed(42)
np.random.seed(42)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

print("=" * 65)
print("  POLLINATION CLASSIFIER — STEP-BY-STEP TRAINING")
print("=" * 65)
print(f"  Device    : {device}")
print(f"  Image size: {IMAGE_SIZE}x{IMAGE_SIZE}")
print(f"  Batch size: {BATCH_SIZE}")
print(f"  Max epochs: {PHASE1_EPOCHS} (phase 1) + {NUM_EPOCHS} (phase 2)")
print("=" * 65)

# ─── TRANSFORMS ───────────────────────────────────────────────────────────────
train_tf = transforms.Compose([
    transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.65, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(30),
    transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.3, hue=0.08),
    transforms.RandomGrayscale(p=0.05),
    transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.2),
])

val_tf = transforms.Compose([
    transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
    transforms.CenterCrop(IMAGE_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

tta_tf = transforms.Compose([
    transforms.Resize((IMAGE_SIZE + 32, IMAGE_SIZE + 32)),
    transforms.RandomResizedCrop(IMAGE_SIZE, scale=(0.8, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

# ─── Step 1: LOAD DATASETS ────────────────────────────────────────────────────
print("\n[STEP 1]  Loading datasets...")
train_ds = datasets.ImageFolder(os.path.join(DATA_DIR, 'train'), train_tf)
val_ds   = datasets.ImageFolder(os.path.join(DATA_DIR, 'val'),   val_tf)
test_ds  = datasets.ImageFolder(os.path.join(DATA_DIR, 'test'),  val_tf)

print(f"  Train : {len(train_ds)} images")
print(f"  Val   : {len(val_ds)} images")
print(f"  Test  : {len(test_ds)} images")
print(f"  Classes: {train_ds.classes}")

# Class counts + weighted sampler (handles imbalance)
labels = [s[1] for s in train_ds.samples]
class_counts = np.bincount(labels)
print(f"\n  Class distribution (train):")
for i, (name, count) in enumerate(zip(CLASS_NAMES, class_counts)):
    print(f"    {name}: {count}")

class_weights  = 1.0 / class_counts
sample_weights = torch.tensor([class_weights[l] for l in labels], dtype=torch.float)
sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)

train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, sampler=sampler,  num_workers=0)
val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
test_dl  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

# ─── Step 2: BUILD MODEL ──────────────────────────────────────────────────────
print("\n[STEP 2]  Building EfficientNet-B3 model...")
model = models.efficientnet_b3(weights='IMAGENET1K_V1')

# Freeze backbone — only train the new head in Phase 1
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
model = model.to(device)

total     = sum(p.numel() for p in model.parameters())
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"  Total params     : {total:,}")
print(f"  Trainable params : {trainable:,}  ({100*trainable/total:.1f}%)")

# ─── RESUME CHECK ─────────────────────────────────────────────────────────────
resume_epoch = 0   # Phase-2 epoch index to start from (0 = beginning)
if RESUME_FROM_CHECKPOINT and os.path.exists(SAVE_PATH):
    ckpt = torch.load(SAVE_PATH, map_location=device)
    model.load_state_dict(ckpt['model_state_dict'])
    best_acc_resume = ckpt['accuracy']
    resume_epoch    = ckpt['epoch'] + 1   # next epoch after the saved one
    print(f"\n  [RESUME] Loaded checkpoint — val_acc={best_acc_resume:.1%}  "
          f"resuming Phase 2 from epoch {resume_epoch+1}/{NUM_EPOCHS}")
else:
    best_acc_resume = 0.0
    resume_epoch    = 0

# ─── HELPERS ──────────────────────────────────────────────────────────────────
criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)

def evaluate(loader):
    model.eval()
    correct = total_n = 0
    with torch.no_grad():
        for imgs, labels_b in loader:
            imgs, labels_b = imgs.to(device), labels_b.to(device)
            preds = model(imgs).argmax(1)
            correct  += (preds == labels_b).sum().item()
            total_n  += labels_b.size(0)
    return correct / total_n

def evaluate_tta(dataset, n_passes=TTA_PASSES):
    import PIL.Image
    model.eval()
    correct = total_n = 0
    with torch.no_grad():
        for img_path, true_label in dataset.samples:
            img = PIL.Image.open(img_path).convert('RGB')
            logits_sum = torch.zeros(NUM_CLASSES).to(device)
            for _ in range(n_passes):
                t = tta_tf(img).unsqueeze(0).to(device)
                logits_sum += model(t).squeeze()
            pred = logits_sum.argmax().item()
            correct += (pred == true_label)
            total_n += 1
    return correct / total_n

history = {'train_loss': [], 'val_acc': []}

# ─── Step 3: PHASE 1 — Train head only ────────────────────────────────────────
if RESUME_FROM_CHECKPOINT and os.path.exists(SAVE_PATH):
    print("\n[STEP 3]  PHASE 1 — SKIPPED (resuming from checkpoint)")
    best_acc = best_acc_resume
    best_wts = copy.deepcopy(model.state_dict())
else:
    print("\n" + "=" * 65)
    print(f"[STEP 3]  PHASE 1 — Train head only ({PHASE1_EPOCHS} epochs, backbone frozen)")
    print("=" * 65)

    optimizer_p1 = optim.AdamW(model.classifier.parameters(), lr=LR_HEAD,
                                 weight_decay=WEIGHT_DECAY)
    scheduler_p1 = lr_scheduler.CosineAnnealingLR(optimizer_p1, T_max=PHASE1_EPOCHS)

    best_acc = 0.0
    best_wts = copy.deepcopy(model.state_dict())

for epoch in range(PHASE1_EPOCHS if not (RESUME_FROM_CHECKPOINT and os.path.exists(SAVE_PATH)) else 0):
    t0 = time.time()
    model.train()
    running_loss = 0.0

    for batch_idx, (imgs, labels_b) in enumerate(train_dl):
        imgs, labels_b = imgs.to(device), labels_b.to(device)
        optimizer_p1.zero_grad()
        loss = criterion(model(imgs), labels_b)
        loss.backward()
        optimizer_p1.step()
        running_loss += loss.item() * imgs.size(0)

        # Live batch progress every 20 batches
        if (batch_idx + 1) % 20 == 0:
            pct = (batch_idx + 1) / len(train_dl) * 100
            elapsed = time.time() - t0
            print(f"    Epoch {epoch+1}/{PHASE1_EPOCHS}  batch {batch_idx+1}/{len(train_dl)} "
                  f"({pct:.0f}%)  {elapsed:.0f}s elapsed", flush=True)

    train_loss = running_loss / len(train_ds)
    val_acc    = evaluate(val_dl)
    scheduler_p1.step()
    elapsed = time.time() - t0

    if val_acc > best_acc:
        best_acc = val_acc
        best_wts = copy.deepcopy(model.state_dict())
        marker = "  << BEST"
    else:
        marker = ""

    print(f"  [P1] Epoch {epoch+1:2d}/{PHASE1_EPOCHS}  loss={train_loss:.4f}  "
          f"val_acc={val_acc:.1%}  best={best_acc:.1%}  ({elapsed:.0f}s){marker}", flush=True)

    history['train_loss'].append(train_loss)
    history['val_acc'].append(val_acc)

if not (RESUME_FROM_CHECKPOINT and os.path.exists(SAVE_PATH)):
    print(f"\n  Phase 1 complete. Best val accuracy: {best_acc:.1%}")

# ─── Step 4: PHASE 2 — Full fine-tune ────────────────────────────────────────
print("\n" + "=" * 65)
if resume_epoch > 0:
    print(f"[STEP 4]  PHASE 2 — Resuming from epoch {resume_epoch+1}/{NUM_EPOCHS} (backbone unfrozen)")
else:
    print(f"[STEP 4]  PHASE 2 — Full fine-tune (backbone unfrozen, max {NUM_EPOCHS} epochs)")
print("=" * 65)

# Restore best weights, unfreeze everything
model.load_state_dict(best_wts)
for param in model.parameters():
    param.requires_grad = True

optimizer_p2 = optim.AdamW([
    {'params': model.features.parameters(),    'lr': LR_BACKBONE},
    {'params': model.classifier.parameters(),  'lr': LR_HEAD},
], weight_decay=WEIGHT_DECAY)

scheduler_p2 = lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer_p2, T_0=10, T_mult=2, eta_min=1e-7)

# Fast-forward scheduler to match resume point
for _ in range(resume_epoch):
    scheduler_p2.step()

no_improve = 0

for epoch in range(resume_epoch, NUM_EPOCHS):
    t0 = time.time()
    model.train()
    running_loss = 0.0

    for batch_idx, (imgs, labels_b) in enumerate(train_dl):
        imgs, labels_b = imgs.to(device), labels_b.to(device)
        optimizer_p2.zero_grad()
        loss = criterion(model(imgs), labels_b)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer_p2.step()
        running_loss += loss.item() * imgs.size(0)

        if (batch_idx + 1) % 20 == 0:
            pct = (batch_idx + 1) / len(train_dl) * 100
            elapsed = time.time() - t0
            print(f"    Epoch {epoch+1}/{NUM_EPOCHS}  batch {batch_idx+1}/{len(train_dl)} "
                  f"({pct:.0f}%)  {elapsed:.0f}s elapsed", flush=True)

    train_loss = running_loss / len(train_ds)
    val_acc    = evaluate(val_dl)
    scheduler_p2.step()
    elapsed = time.time() - t0

    improved = val_acc > best_acc
    if improved:
        best_acc   = val_acc
        best_wts   = copy.deepcopy(model.state_dict())
        no_improve = 0
        torch.save({
            'epoch':            epoch,
            'model_state_dict': best_wts,
            'accuracy':         best_acc,
            'class_names':      CLASS_NAMES,
            'image_size':       IMAGE_SIZE,
        }, SAVE_PATH)
        marker = "  << BEST (saved)"
    else:
        no_improve += 1
        marker = f"  (no improve {no_improve}/{EARLY_STOP_PAT})"

    print(f"  [P2] Epoch {epoch+1:3d}/{NUM_EPOCHS}  loss={train_loss:.4f}  "
          f"val_acc={val_acc:.1%}  best={best_acc:.1%}  ({elapsed:.0f}s){marker}", flush=True)

    history['train_loss'].append(train_loss)
    history['val_acc'].append(val_acc)

    if no_improve >= EARLY_STOP_PAT:
        print(f"\n  Early stopping triggered at epoch {epoch+1}.")
        break

# ─── Step 5: FINAL EVALUATION ─────────────────────────────────────────────────
print("\n" + "=" * 65)
print("[STEP 5]  FINAL EVALUATION")
print("=" * 65)

model.load_state_dict(best_wts)

# Save final model
torch.save({
    'model_state_dict': best_wts,
    'accuracy':         best_acc,
    'class_names':      CLASS_NAMES,
    'image_size':       IMAGE_SIZE,
}, FINAL_PATH)
print(f"\n  Model saved → {FINAL_PATH}")

# Standard test accuracy
test_acc = evaluate(test_dl)
print(f"  Standard test accuracy : {test_acc:.1%}")

# TTA accuracy
print(f"  Running TTA ({TTA_PASSES} passes per image)…")
tta_acc = evaluate_tta(test_ds)
print(f"  TTA test accuracy      : {tta_acc:.1%}")

# Full classification report
model.eval()
all_preds, all_labels = [], []
with torch.no_grad():
    for imgs, labels_b in test_dl:
        preds = model(imgs.to(device)).argmax(1).cpu()
        all_preds.extend(preds.numpy())
        all_labels.extend(labels_b.numpy())

print("\n  Classification Report:")
print(classification_report(all_labels, all_preds, target_names=CLASS_NAMES))

# ─── Step 6: SAVE PLOTS ───────────────────────────────────────────────────────
print("[STEP 6]  Saving plots...")

# Confusion matrix
cm = confusion_matrix(all_labels, all_preds)
fig, ax = plt.subplots(figsize=(6, 5))
im = ax.imshow(cm, cmap='Blues')
ax.set_xticks(range(NUM_CLASSES)); ax.set_yticks(range(NUM_CLASSES))
ax.set_xticklabels(CLASS_NAMES, rotation=30, ha='right')
ax.set_yticklabels(CLASS_NAMES)
for i in range(NUM_CLASSES):
    for j in range(NUM_CLASSES):
        ax.text(j, i, cm[i, j], ha='center', va='center',
                color='white' if cm[i, j] > cm.max() / 2 else 'black',
                fontsize=14, fontweight='bold')
ax.set_xlabel('Predicted'); ax.set_ylabel('True')
ax.set_title(f'Confusion Matrix  (test={test_acc:.1%}  TTA={tta_acc:.1%})')
plt.colorbar(im); plt.tight_layout()
cm_path = r'C:\Users\Admin\Desktop\CAPS\confusion_matrix.png'
plt.savefig(cm_path, dpi=150)
plt.close()
print(f"  Confusion matrix saved → confusion_matrix.png")

# Training curve
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
ax1.plot(history['train_loss'], color='tab:blue')
ax1.set_title('Training Loss'); ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
ax1.grid(True, alpha=0.3)

ax2.plot(history['val_acc'], color='tab:orange')
ax2.axhline(0.85, color='green',  linestyle='--', alpha=0.7, label='85% target')
ax2.axhline(0.90, color='darkgreen', linestyle='--', alpha=0.7, label='90% target')
ax2.set_title('Validation Accuracy'); ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy')
ax2.set_ylim(0, 1); ax2.legend(); ax2.grid(True, alpha=0.3)
plt.suptitle(f'Training Curves  (best val={best_acc:.1%}  test={test_acc:.1%}  TTA={tta_acc:.1%})')
plt.tight_layout()
curve_path = r'C:\Users\Admin\Desktop\CAPS\training_curve.png'
plt.savefig(curve_path, dpi=150)
plt.close()
print(f"  Training curve saved  → training_curve.png")

# ─── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  TRAINING COMPLETE")
print("=" * 65)
print(f"  Best validation accuracy : {best_acc:.1%}")
print(f"  Test accuracy            : {test_acc:.1%}")
print(f"  Test accuracy (TTA)      : {tta_acc:.1%}")
print(f"  Checkpoint saved to      : {SAVE_PATH}")
print(f"  Final model saved to     : {FINAL_PATH}")
print("=" * 65)
