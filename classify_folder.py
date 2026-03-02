"""
Classify Folder by Pollination Status
----------------------------------------
Uses the trained ResNet50 model to automatically sort images from any folder
into three subfolders: pollinating / pollinated / not_pollinated

Usage:
    python classify_folder.py                         # sorts DATASETS/ folder
    python classify_folder.py --source path/to/imgs   # sorts a custom folder
    python classify_folder.py --source path/to/imgs --output path/to/out
    python classify_folder.py --source path/to/imgs --move  # move instead of copy

Options:
    --source  SOURCE   Folder containing images to classify (default: DATASETS)
    --output  OUTPUT   Destination folder (default: <source>_SORTED)
    --model   MODEL    Path to model checkpoint (default: best_model_checkpoint.pth)
    --move             Move files instead of copying them
    --conf    FLOAT    Minimum confidence threshold 0-1 (default: 0.0)
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# ── Class labels (must match training order – alphabetical / ImageFolder order) ──
CLASS_NAMES = ['not_pollinated', 'pollinated', 'pollinating']

# ── Image pre-processing (same as validation transform used in training) ──
TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}


def load_model(model_path: str, device: torch.device) -> nn.Module:
    """Load the trained ResNet50 model from a checkpoint."""
    model = models.resnet50(weights=None)
    # Replicate the custom fc head used during training:
    # fc.1 = Linear(2048→512),  fc.4 = Linear(512→num_classes)
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.5),                        # 0 – no params
        nn.Linear(num_ftrs, 512),               # 1
        nn.ReLU(inplace=True),                  # 2 – no params
        nn.Dropout(0.3),                        # 3 – no params
        nn.Linear(512, len(CLASS_NAMES)),       # 4
    )

    checkpoint = torch.load(model_path, map_location=device, weights_only=False)

    # Handle various checkpoint formats
    if isinstance(checkpoint, dict):
        state_dict = checkpoint.get('model_state_dict',
                     checkpoint.get('state_dict',
                     checkpoint))
    else:
        state_dict = checkpoint

    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


def classify_image(model: nn.Module, image_path: str, device: torch.device):
    """
    Classify a single image.
    Returns (class_name, confidence_float).
    """
    try:
        img = Image.open(image_path).convert('RGB')
    except Exception as e:
        print(f"  [WARN] Could not open {image_path}: {e}")
        return None, 0.0

    tensor = TRANSFORM(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)
        conf, pred_idx = torch.max(probs, dim=1)

    return CLASS_NAMES[pred_idx.item()], conf.item()


def get_unique_dest(dest_path: Path) -> Path:
    """Return a non-colliding destination path by appending a counter."""
    if not dest_path.exists():
        return dest_path
    stem, suffix = dest_path.stem, dest_path.suffix
    counter = 1
    while True:
        candidate = dest_path.parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def classify_folder(source_dir: str,
                    output_dir: str,
                    model_path: str,
                    move_files: bool = False,
                    min_confidence: float = 0.0):

    source_path = Path(source_dir)
    output_path = Path(output_dir)

    if not source_path.exists():
        print(f"[ERROR] Source folder not found: {source_path}")
        sys.exit(1)

    if not Path(model_path).exists():
        print(f"[ERROR] Model checkpoint not found: {model_path}")
        sys.exit(1)

    # Collect image files (non-recursive by default; tweak below if needed)
    image_files = [
        f for f in source_path.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not image_files:
        print(f"[ERROR] No images found in: {source_path}")
        sys.exit(1)

    # Device
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice        : {device}")
    print(f"Model         : {model_path}")
    print(f"Source        : {source_path}  ({len(image_files)} images)")
    print(f"Output        : {output_path}")
    print(f"Action        : {'MOVE' if move_files else 'COPY'}")
    if min_confidence > 0:
        print(f"Min confidence: {min_confidence:.0%}")
    print()

    # Create output subfolders
    for cls in CLASS_NAMES:
        (output_path / cls).mkdir(parents=True, exist_ok=True)
    low_conf_dir = output_path / 'low_confidence'

    # Load model
    print("Loading model …")
    model = load_model(model_path, device)
    print("Model loaded.\n")

    # Classify
    counts = {cls: 0 for cls in CLASS_NAMES}
    counts['low_confidence'] = 0
    skipped = 0

    for i, img_path in enumerate(image_files, 1):
        label, confidence = classify_image(model, str(img_path), device)

        if label is None:
            skipped += 1
            continue

        # Confidence filter
        if confidence < min_confidence:
            low_conf_dir.mkdir(parents=True, exist_ok=True)
            dest = get_unique_dest(low_conf_dir / img_path.name)
            shutil.copy2(img_path, dest) if not move_files else shutil.move(str(img_path), str(dest))
            counts['low_confidence'] += 1
            print(f"  [{i:4d}/{len(image_files)}] {img_path.name:<40s}  "
                  f"→ low_confidence  ({confidence:.1%})")
            continue

        dest = get_unique_dest(output_path / label / img_path.name)
        if move_files:
            shutil.move(str(img_path), str(dest))
        else:
            shutil.copy2(img_path, dest)

        counts[label] += 1
        print(f"  [{i:4d}/{len(image_files)}] {img_path.name:<40s}  "
              f"→ {label:<16s} ({confidence:.1%})")

    # Summary
    total = sum(counts.values())
    print("\n" + "=" * 60)
    print("CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"  Pollinating    : {counts['pollinating']:>5}")
    print(f"  Pollinated     : {counts['pollinated']:>5}")
    print(f"  Not Pollinated : {counts['not_pollinated']:>5}")
    if counts['low_confidence']:
        print(f"  Low Confidence : {counts['low_confidence']:>5}  (below {min_confidence:.0%})")
    if skipped:
        print(f"  Skipped (error): {skipped:>5}")
    print(f"  {'─'*25}")
    print(f"  Total          : {total:>5}")
    print(f"\nOutput saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Sort images into pollination categories using the trained model."
    )
    parser.add_argument(
        '--source', default=r'C:\Users\Admin\Desktop\CAPS\DATASETS',
        help='Folder of images to classify (default: DATASETS)'
    )
    parser.add_argument(
        '--output', default=None,
        help='Destination folder (default: <source>_SORTED)'
    )
    parser.add_argument(
        '--model', default=r'C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth',
        help='Path to model .pth checkpoint'
    )
    parser.add_argument(
        '--move', action='store_true',
        help='Move files instead of copying'
    )
    parser.add_argument(
        '--conf', type=float, default=0.0, metavar='FLOAT',
        help='Minimum confidence (0.0–1.0). Low-conf images go to low_confidence/'
    )

    args = parser.parse_args()

    source = args.source
    output = args.output or (source.rstrip('/\\') + '_SORTED')

    classify_folder(
        source_dir=source,
        output_dir=output,
        model_path=args.model,
        move_files=args.move,
        min_confidence=args.conf,
    )


if __name__ == '__main__':
    main()
