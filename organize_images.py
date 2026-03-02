"""
Image Organization Helper Script
================================
This script helps you organize images from DATASETS folder into train/val/test splits
across the three classes: pollinating, pollinated, and not_pollinated.

Instructions:
1. Run this script and it will guide you through organizing your images
2. You can either manually move files or use the interactive mode
"""

import os
import shutil
from pathlib import Path

# Paths
SOURCE_DIR = 'DATASETS'
DEST_DIR = 'DATASETS_ORGANIZED'

# Classes
CLASSES = ['pollinating', 'pollinated', 'not_pollinated']

# Split ratios
TRAIN_RATIO = 0.7
VAL_RATIO = 0.15
TEST_RATIO = 0.15

def count_organized_images():
    """Count how many images are organized in each split/class."""
    counts = {'train': {}, 'val': {}, 'test': {}}
    
    for split in ['train', 'val', 'test']:
        for class_name in CLASSES:
            class_dir = os.path.join(DEST_DIR, split, class_name)
            if os.path.exists(class_dir):
                counts[split][class_name] = len([f for f in os.listdir(class_dir) 
                                                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            else:
                counts[split][class_name] = 0
    
    return counts

def display_organization_status():
    """Display current organization status."""
    print("\n" + "="*60)
    print("CURRENT ORGANIZATION STATUS")
    print("="*60)
    
    counts = count_organized_images()
    
    for split in ['train', 'val', 'test']:
        print(f"\n{split.upper()}:")
        total = 0
        for class_name in CLASSES:
            count = counts[split][class_name]
            total += count
            print(f"  {class_name:20}: {count:4} images")
        print(f"  {'TOTAL':20}: {total:4} images")
    
    grand_total = sum(sum(counts[split].values()) for split in ['train', 'val', 'test'])
    print(f"\n{'GRAND TOTAL':20}: {grand_total:4} images")
    print("="*60)

def manual_organization_guide():
    """Provide instructions for manual organization."""
    print("\n" + "="*60)
    print("MANUAL ORGANIZATION GUIDE")
    print("="*60)
    
    print("\nTo organize your images manually, follow these steps:")
    print("\n1. Look at each image in the DATASETS folder")
    print("2. Move it to the appropriate folder based on its class:")
    
    for class_name in CLASSES:
        print(f"\n   {class_name.upper()}:")
        print(f"   - Train (70%): DATASETS_ORGANIZED/train/{class_name}/")
        print(f"   - Val   (15%): DATASETS_ORGANIZED/val/{class_name}/")
        print(f"   - Test  (15%): DATASETS_ORGANIZED/test/{class_name}/")
    
    print("\nExample split recommendation:")
    total_images = len([f for f in os.listdir(SOURCE_DIR) 
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    print(f"  Total images in DATASETS: {total_images}")
    print(f"  Suggested per class (if evenly distributed):")
    images_per_class = total_images // 3
    print(f"    Train: {int(images_per_class * TRAIN_RATIO)} images")
    print(f"    Val:   {int(images_per_class * VAL_RATIO)} images")
    print(f"    Test:  {int(images_per_class * TEST_RATIO)} images")
    
    print("\n" + "="*60)

def main():
    print("="*60)
    print("POLLINATION IMAGE ORGANIZATION TOOL")
    print("="*60)
    
    # Check if source directory exists
    if not os.path.exists(SOURCE_DIR):
        print(f"\nError: Source directory '{SOURCE_DIR}' not found!")
        return
    
    # Count images in source
    source_images = [f for f in os.listdir(SOURCE_DIR) 
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"\nFound {len(source_images)} images in '{SOURCE_DIR}'")
    
    # Display current organization status
    display_organization_status()
    
    # Show manual organization guide
    manual_organization_guide()
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Manually organize your images into the folder structure")
    print("2. Run this script again to check your progress: python organize_images.py")
    print("3. Once all images are organized, run the training notebook!")
    print("="*60)

if __name__ == "__main__":
    main()
