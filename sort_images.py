"""
Interactive Image Sorting Tool for Capstone Project
Displays images one by one and categorizes them with keyboard shortcuts
Automatically splits into train/val/test and duplicates for class balance
"""

import os
import shutil
from pathlib import Path
from PIL import Image
import tkinter as tk
from tkinter import messagebox
import random
from collections import Counter

# Configuration
SOURCE_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS"
TARGET_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED"
MIN_SAMPLES_PER_CLASS = 100  # Will duplicate to reach this minimum

# Categories
CATEGORIES = {
    '1': 'pollinating',
    '2': 'pollinated', 
    '3': 'not_pollinated'
}

class ImageSorter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🐝 Capstone Image Sorter - Press 1/2/3 to Classify")
        self.root.geometry("1200x900")
        self.root.configure(bg='#2b2b2b')
        
        # State
        self.image_files = []
        self.current_index = 0
        self.classifications = {}
        self.skipped = []
        
        # Setup UI
        self.setup_ui()
        
        # Load images
        self.load_images()
        
        # Start
        if self.image_files:
            self.show_current_image()
        else:
            messagebox.showerror("Error", "No images found in DATASETS folder!")
            self.root.destroy()
    
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#1e1e1e', height=80)
        header.pack(fill=tk.X, padx=10, pady=10)
        
        title = tk.Label(header, text="🎓 Capstone Image Classifier", 
                        font=('Arial', 24, 'bold'), bg='#1e1e1e', fg='#00ff00')
        title.pack(pady=10)
        
        # Progress info
        self.progress_label = tk.Label(header, text="", 
                                      font=('Arial', 12), bg='#1e1e1e', fg='#ffffff')
        self.progress_label.pack()
        
        # Image display
        image_frame = tk.Frame(self.root, bg='#2b2b2b')
        image_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.image_label = tk.Label(image_frame, bg='#2b2b2b')
        self.image_label.pack(expand=True)
        
        # Instructions
        instructions_frame = tk.Frame(self.root, bg='#1e1e1e', height=150)
        instructions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        instructions = tk.Label(instructions_frame, 
                               text="Press Key to Classify:\n" +
                                    "1️⃣  = POLLINATING (bee actively pollinating)\n" +
                                    "2️⃣  = POLLINATED (already pollinated flower)\n" +
                                    "3️⃣  = NOT POLLINATED (flower not pollinated)\n" +
                                    "SPACE = Skip this image\n" +
                                    "ESC = Finish and organize",
                               font=('Arial', 14, 'bold'),
                               bg='#1e1e1e', fg='#ffffff', justify=tk.LEFT)
        instructions.pack(pady=15)
        
        # Stats
        self.stats_label = tk.Label(instructions_frame, text="",
                                   font=('Arial', 11), bg='#1e1e1e', fg='#ffaa00')
        self.stats_label.pack()
        
        # Bind keys
        self.root.bind('1', lambda e: self.classify('pollinating'))
        self.root.bind('2', lambda e: self.classify('pollinated'))
        self.root.bind('3', lambda e: self.classify('not_pollinated'))
        self.root.bind('<space>', lambda e: self.skip_image())
        self.root.bind('<Escape>', lambda e: self.finish_sorting())
        
    def load_images(self):
        """Load all images from source directory"""
        print(f"Loading images from {SOURCE_DIR}...")
        
        extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
        for root, dirs, files in os.walk(SOURCE_DIR):
            for file in files:
                if file.lower().endswith(extensions):
                    self.image_files.append(os.path.join(root, file))
        
        random.shuffle(self.image_files)
        print(f"Found {len(self.image_files)} images")
    
    def show_current_image(self):
        """Display current image"""
        if self.current_index >= len(self.image_files):
            self.finish_sorting()
            return
        
        img_path = self.image_files[self.current_index]
        
        try:
            # Load and resize image
            img = Image.open(img_path)
            img.thumbnail((1000, 650), Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(img)
            
            # Display
            self.image_label.configure(image=photo)
            self.image_label.image = photo
            
            # Update progress
            progress = f"Image {self.current_index + 1} / {len(self.image_files)}"
            filename = os.path.basename(img_path)
            self.progress_label.configure(text=f"{progress} - {filename}")
            
            # Update stats
            counts = Counter(self.classifications.values())
            stats = f"Classified: {len(self.classifications)} | " + \
                   f"Pollinating: {counts.get('pollinating', 0)} | " + \
                   f"Pollinated: {counts.get('pollinated', 0)} | " + \
                   f"Not Pollinated: {counts.get('not_pollinated', 0)} | " + \
                   f"Skipped: {len(self.skipped)}"
            self.stats_label.configure(text=stats)
            
        except Exception as e:
            print(f"Error loading image {img_path}: {e}")
            self.current_index += 1
            self.show_current_image()
    
    def classify(self, category):
        """Classify current image"""
        img_path = self.image_files[self.current_index]
        self.classifications[img_path] = category
        print(f"✓ {os.path.basename(img_path)} -> {category}")
        
        self.current_index += 1
        self.show_current_image()
    
    def skip_image(self):
        """Skip current image"""
        img_path = self.image_files[self.current_index]
        self.skipped.append(img_path)
        print(f"⊘ Skipped: {os.path.basename(img_path)}")
        
        self.current_index += 1
        self.show_current_image()
    
    def finish_sorting(self):
        """Organize classified images into folders"""
        if len(self.classifications) < 30:
            if not messagebox.askyesno("Low Count", 
                f"Only {len(self.classifications)} images classified. Continue anyway?"):
                return
        
        self.root.destroy()
        print("\n" + "="*60)
        print("🎯 ORGANIZING IMAGES...")
        print("="*60)
        
        # Organize images
        organize_images(self.classifications)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def organize_images(classifications):
    """Organize classified images into train/val/test splits with duplication"""
    
    # Group by category
    categories = {}
    for img_path, category in classifications.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(img_path)
    
    print("\n📊 Classification Summary:")
    for category, images in categories.items():
        print(f"  {category}: {len(images)} images")
    
    # Check if we need duplication
    min_count = min(len(images) for images in categories.values())
    max_count = max(len(images) for images in categories.values())
    
    if min_count < MIN_SAMPLES_PER_CLASS:
        print(f"\n⚠️  Minimum class has only {min_count} samples")
        print(f"🔄 Will duplicate images to reach {MIN_SAMPLES_PER_CLASS} per class")
    
    # Duplicate minority classes
    for category, images in categories.items():
        if len(images) < MIN_SAMPLES_PER_CLASS:
            needed = MIN_SAMPLES_PER_CLASS - len(images)
            duplicates = random.choices(images, k=needed)
            categories[category].extend(duplicates)
            print(f"  ✓ Duplicated {needed} images for {category}")
    
    # Split into train/val/test
    splits = {'train': 0.70, 'val': 0.15, 'test': 0.15}
    
    organized_count = 0
    
    for category, images in categories.items():
        random.shuffle(images)
        
        train_end = int(len(images) * splits['train'])
        val_end = train_end + int(len(images) * splits['val'])
        
        split_images = {
            'train': images[:train_end],
            'val': images[train_end:val_end],
            'test': images[val_end:]
        }
        
        # Copy images to organized structure
        for split, img_list in split_images.items():
            target_folder = os.path.join(TARGET_DIR, split, category)
            os.makedirs(target_folder, exist_ok=True)
            
            for i, img_path in enumerate(img_list):
                filename = os.path.basename(img_path)
                
                # Handle duplicates by adding suffix
                base, ext = os.path.splitext(filename)
                target_path = os.path.join(target_folder, filename)
                
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(target_folder, f"{base}_dup{counter}{ext}")
                    counter += 1
                
                shutil.copy2(img_path, target_path)
                organized_count += 1
            
            print(f"  ✓ {split}/{category}: {len(img_list)} images")
    
    print(f"\n✅ Successfully organized {organized_count} images!")
    print(f"📁 Location: {TARGET_DIR}")
    
    # Final summary
    print("\n" + "="*60)
    print("📈 FINAL DATASET STRUCTURE:")
    print("="*60)
    
    for split in ['train', 'val', 'test']:
        print(f"\n{split.upper()}:")
        for category in categories.keys():
            folder = os.path.join(TARGET_DIR, split, category)
            count = len([f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))])
            print(f"  {category}: {count} images")
    
    print("\n🎓 Ready for training! Run the notebook now.")


if __name__ == "__main__":
    print("="*60)
    print("🐝 CAPSTONE IMAGE SORTER")
    print("="*60)
    print("\nStarting interactive image sorter...")
    print("Use keyboard shortcuts to classify images quickly!\n")
    
    sorter = ImageSorter()
    sorter.run()
