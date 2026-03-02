"""
Terminal-based Quick Image Sorter
Shows image info and lets you classify via keyboard
"""

import os
import shutil
import random
from pathlib import Path
from collections import Counter

SOURCE_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS"
TARGET_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED"
MIN_SAMPLES_PER_CLASS = 100

def get_all_images():
    """Get all image files"""
    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    images = []
    for file in os.listdir(SOURCE_DIR):
        if file.lower().endswith(extensions):
            images.append(os.path.join(SOURCE_DIR, file))
    return images

def terminal_sort():
    """Terminal-based classification"""
    print("\n" + "="*70)
    print("🐝 QUICK IMAGE SORTER (Terminal Edition)")
    print("="*70)
    
    images = get_all_images()
    random.shuffle(images)
    
    print(f"\nFound {len(images)} images")
    print("\nFor each image filename shown, type:")
    print("  1 = Pollinating")
    print("  2 = Pollinated")
    print("  3 = Not Pollinated")
    print("  s = Skip")
    print("  q = Quit and organize")
    print("\nNOTE: Images will open in your default viewer automatically")
    print("="*70)
    
    classifications = {}
    
    for i, img_path in enumerate(images):
        filename = os.path.basename(img_path)
        
        # Try to open image in default viewer
        try:
            os.startfile(img_path)
        except:
            pass
        
        print(f"\n[{i+1}/{len(images)}] {filename}")
        
        while True:
            choice = input("Classify (1/2/3/s/q): ").strip().lower()
            
            if choice == 'q':
                print("\n✓ Finishing classification...")
                organize_images(classifications)
                return
            elif choice == 's':
                print("  Skipped")
                break
            elif choice == '1':
                classifications[img_path] = 'pollinating'
                print("  ✓ Pollinating")
                break
            elif choice == '2':
                classifications[img_path] = 'pollinated'
                print("  ✓ Pollinated")
                break
            elif choice == '3':
                classifications[img_path] = 'not_pollinated'
                print("  ✓ Not Pollinated")
                break
            else:
                print("  Invalid input. Use 1, 2, 3, s, or q")
        
        # Show progress every 10 images
        if (i + 1) % 10 == 0:
            counts = Counter(classifications.values())
            print(f"\n  Progress: {len(classifications)} classified")
            print(f"    Pollinating: {counts.get('pollinating', 0)}")
            print(f"    Pollinated: {counts.get('pollinated', 0)}")
            print(f"    Not Pollinated: {counts.get('not_pollinated', 0)}")
    
    organize_images(classifications)

def organize_images(classifications):
    """Organize and duplicate images"""
    if len(classifications) < 30:
        print(f"\n⚠️  Only {len(classifications)} images classified.")
        cont = input("Continue anyway? (y/n): ").strip().lower()
        if cont != 'y':
            print("Cancelled.")
            return
    
    print("\n" + "="*70)
    print("🎯 ORGANIZING IMAGES WITH DUPLICATION")
    print("="*70)
    
    # Group by category
    categories = {}
    for img_path, category in classifications.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(img_path)
    
    print("\n📊 Original Classification:")
    for category, images in categories.items():
        print(f"  {category}: {len(images)} images")
    
    # Duplicate to meet minimum
    print(f"\n🔄 Duplicating to minimum {MIN_SAMPLES_PER_CLASS} per class...")
    for category, images in categories.items():
        if len(images) < MIN_SAMPLES_PER_CLASS:
            needed = MIN_SAMPLES_PER_CLASS - len(images)
            duplicates = random.choices(images, k=needed)
            categories[category].extend(duplicates)
            print(f"  ✓ {category}: added {needed} duplicates ({len(images)} → {len(categories[category])})")
        else:
            print(f"  ✓ {category}: no duplication needed ({len(images)} images)")
    
    # Split and organize
    print("\n📁 Splitting into train/val/test (70/15/15)...")
    
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
            
            for i, img_path in enumerate(img_list):
                filename = os.path.basename(img_path)
                base, ext = os.path.splitext(filename)
                target_path = os.path.join(target_folder, filename)
                
                # Handle duplicates
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(target_folder, f"{base}_dup{counter}{ext}")
                    counter += 1
                
                shutil.copy2(img_path, target_path)
            
            print(f"  ✓ {split}/{category}: {len(img_list)} images")
    
    # Summary
    print("\n" + "="*70)
    print("✅ ORGANIZATION COMPLETE!")
    print("="*70)
    
    print("\n📈 Final Dataset:")
    for split in ['train', 'val', 'test']:
        total = 0
        print(f"\n{split.upper()}:")
        for category in categories.keys():
            folder = os.path.join(TARGET_DIR, split, category)
            if os.path.exists(folder):
                count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
                print(f"  {category}: {count}")
                total += count
        print(f"  TOTAL: {total}")
    
    print("\n🎓 Ready for training!")

if __name__ == "__main__":
    terminal_sort()
