"""
Auto-classify images using AI Vision
Requires: pip install openai Pillow
Also need OpenAI API key
"""

import os
import base64
import json
from pathlib import Path
import shutil
import random

# Configuration
SOURCE_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS"
TARGET_DIR = r"C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED"

# You need to set your OpenAI API key here
# Get it from: https://platform.openai.com/api-keys
OPENAI_API_KEY = "YOUR_API_KEY_HERE"  # ⚠️ REPLACE THIS WITH YOUR ACTUAL API KEY

def encode_image(image_path):
    """Encode image to base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def classify_image_with_vision(image_path):
    """
    Use OpenAI Vision API to classify the image
    Returns: 'pollinating', 'pollinated', or 'not_pollinated'
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Encode image
        base64_image = encode_image(image_path)
        
        # Create prompt
        prompt = """Analyze this image and classify it into ONE of these categories:
        
1. "pollinating" - if you see bees or insects actively pollinating flowers (on the flower, gathering pollen/nectar)
2. "pollinated" - if you see flowers that appear to be already pollinated or have visible pollen
3. "not_pollinated" - if you see flowers that are NOT pollinated yet (clean, fresh flowers without pollinators)

Respond with ONLY ONE WORD: either "pollinating", "pollinated", or "not_pollinated"
"""
        
        # Call Vision API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4-vision-preview"
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10
        )
        
        # Extract classification
        classification = response.choices[0].message.content.strip().lower()
        
        # Validate response
        valid_classes = ['pollinating', 'pollinated', 'not_pollinated']
        if classification in valid_classes:
            return classification
        else:
            print(f"  ⚠️ Unexpected response: {classification}, defaulting to 'not_pollinated'")
            return 'not_pollinated'
            
    except Exception as e:
        print(f"  ❌ Error classifying image: {e}")
        return None

def organize_images():
    """Auto-classify and organize all images"""
    
    if OPENAI_API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ ERROR: You need to set your OpenAI API key!")
        print("   1. Get API key from: https://platform.openai.com/api-keys")
        print("   2. Edit this file and replace YOUR_API_KEY_HERE")
        print("   3. Run again\n")
        return
    
    print("="*70)
    print("🤖 AUTO-CLASSIFICATION WITH AI VISION")
    print("="*70)
    
    # Get all images
    extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    images = [os.path.join(SOURCE_DIR, f) for f in os.listdir(SOURCE_DIR) 
              if f.lower().endswith(extensions)]
    
    print(f"\nFound {len(images)} images to classify")
    print("⚠️  Note: This will use OpenAI API credits (costs money)")
    
    choice = input(f"\nClassify all {len(images)} images? (y/n): ").strip().lower()
    if choice != 'y':
        print("Cancelled.")
        return
    
    classifications = {}
    
    print("\n🔄 Classifying images...\n")
    
    for idx, img_path in enumerate(images, 1):
        filename = os.path.basename(img_path)
        print(f"[{idx}/{len(images)}] {filename}...", end=' ')
        
        category = classify_image_with_vision(img_path)
        
        if category:
            classifications[img_path] = category
            print(f"✓ {category}")
        else:
            print(f"✗ Failed")
        
        # Progress update every 50 images
        if idx % 50 == 0:
            print(f"\n   Progress: {idx}/{len(images)} ({idx/len(images)*100:.1f}%)\n")
    
    # Organize into folders
    print("\n" + "="*70)
    print("📁 ORGANIZING INTO FOLDERS")
    print("="*70)
    
    categories = {}
    for img_path, category in classifications.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(img_path)
    
    print(f"\n📊 Classification Summary:")
    for category, images in categories.items():
        print(f"  {category}: {len(images)} images")
    
    # Split into train/val/test and copy
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
            
            # Clear existing
            for f in os.listdir(target_folder):
                os.remove(os.path.join(target_folder, f))
            
            # Copy images
            for img_path in img_list:
                filename = os.path.basename(img_path)
                shutil.copy2(img_path, os.path.join(target_folder, filename))
            
            print(f"  ✓ {split}/{category}: {len(img_list)} images")
    
    print("\n✅ COMPLETE! Images organized and ready for training.")
    print(f"📁 Location: {TARGET_DIR}")

if __name__ == "__main__":
    organize_images()
