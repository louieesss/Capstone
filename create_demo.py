"""
Auto-Demo Setup for Training Pipeline
Creates a demo dataset with sample images so training can begin immediately
"""

import os
import shutil
import random
from pathlib import Path

SOURCE_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS"
TARGET_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED"
MIN_SAMPLES_PER_CLASS = 100

# Demo configuration
DEMO_IMAGES_PER_CLASS = 120  # Will be split 70/15/15 = ~84 train / 18 val / 18 test

def create_demo_dataset():
    """Create demo organized dataset for immediate training"""
    
    print("="*70)
    print("🚀 CREATING DEMO DATASET FOR IMMEDIATE TRAINING")
    print("="*70)
    print("\n⚠️  NOTE: This uses RANDOM classification for demonstration only!")
    print("   For your actual capstone with real accuracy, you'll need to")
    print("   properly label images based on their content.")
    print("\n   This demo lets you test the full training pipeline now.\n")
    
    # Get all images
    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    all_images = []
    for file in os.listdir(SOURCE_DIR):
        if file.lower().endswith(extensions):
            all_images.append(os.path.join(SOURCE_DIR, file))
    
    demo_per_class = DEMO_IMAGES_PER_CLASS
    total_needed = demo_per_class * 3
    
    if len(all_images) < total_needed:
        print(f"⚠️  Only {len(all_images)} images available, need {total_needed}")
        demo_per_class = len(all_images) // 3
        total_needed = demo_per_class * 3
    
    print(f"📊 Using {total_needed} images ({demo_per_class} per class)")
    
    # Random sample
    random.shuffle(all_images)
    sample_images = all_images[:total_needed]
    
    # Randomly assign to classes (DEMO ONLY)
    categories = {
        'pollinating': sample_images[:demo_per_class],
        'pollinated': sample_images[demo_per_class:demo_per_class*2],
        'not_pollinated': sample_images[demo_per_class*2:demo_per_class*3]
    }
    
    print("\n🔄 Random Classification (DEMO):")
    for category, images in categories.items():
        print(f"  {category}: {len(images)} images")
    
    # Duplicate if needed
    print(f"\n📦 Duplicating to minimum {MIN_SAMPLES_PER_CLASS} per class...")
    for category, images in list(categories.items()):
        if len(images) < MIN_SAMPLES_PER_CLASS:
            needed = MIN_SAMPLES_PER_CLASS - len(images)
            duplicates = random.choices(images, k=needed)
            categories[category] = images + duplicates
            print(f"  ✓ {category}: {len(images)} → {len(categories[category])} (added {needed})")
        else:
            print(f"  ✓ {category}: {len(images)} (no duplication needed)")
    
    # Organize into train/val/test
    print("\n📁 Organizing into train/val/test (70/15/15)...")
    
    stats = {}
    
    for category, images in categories.items():
        random.shuffle(images)
        
        train_end = int(len(images) * 0.70)
        val_end = train_end + int(len(images) * 0.15)
        
        splits = {
            'train': images[:train_end],
            'val': images[train_end:val_end],
            'test': images[val_end:]
        }
        
        for split, img_list in splits.items():
            target_folder = os.path.join(TARGET_DIR, split, category)
            os.makedirs(target_folder, exist_ok=True)
            
            # Clear existing files
            for existing_file in os.listdir(target_folder):
                os.remove(os.path.join(target_folder, existing_file))
            
            # Copy images
            for i, img_path in enumerate(img_list):
                filename = os.path.basename(img_path)
                base, ext = os.path.splitext(filename)
                target_path = os.path.join(target_folder, filename)
                
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(target_folder, f"{base}_dup{counter}{ext}")
                    counter += 1
                
                shutil.copy2(img_path, target_path)
            
            if split not in stats:
                stats[split] = {}
            stats[split][category] = len(img_list)
    
    # Print summary
    print("\n" + "="*70)
    print("✅ DEMO DATASET CREATED!")
    print("="*70)
    
    print("\n📈 Dataset Structure:")
    for split in ['train', 'val', 'test']:
        total = sum(stats[split].values())
        print(f"\n{split.upper()} ({total} images):")
        for category in categories.keys():
            print(f"  {category}: {stats[split][category]}")
    
    grand_total = sum(sum(split_data.values()) for split_data in stats.values())
    print(f"\n📊 Grand Total: {grand_total} images")
    
    print("\n✅ Ready to train!")
    print("   Run the notebook cells to start training.")
    print("\n⚠️  REMEMBER: For your actual capstone submission,")
    print("   you'll need to properly classify images based on their")
    print("   actual content for meaningful accuracy results.")
    
    return True

if __name__ == "__main__":
    create_demo_dataset()
