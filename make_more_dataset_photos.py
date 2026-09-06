from PIL import Image, ImageDraw, ImageFont
import os

root = 'DATASETS_ORGANIZED'
classes = ['not_pollinated', 'pollinated', 'pollinating']
selected = []

for c in classes:
    folder = os.path.join(root, 'train', c)
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    # Keep a larger number for a fuller visual proof
    selected.extend(files[:10])

canvas = Image.new('RGB', (2200, 1500), (255, 255, 255))
draw = ImageDraw.Draw(canvas)

try:
    title_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 36)
    label_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
except Exception:
    title_font = ImageFont.load_default()
    label_font = ImageFont.load_default()

draw.text((520, 30), 'Real Dataset Images Used for Training', fill=(0,0,0), font=title_font)

x, y = 50, 100
count = 0
for img_path in selected:
    img = Image.open(img_path).convert('RGB')
    img = img.resize((280, 210))
    canvas.paste(img, (x, y))
    label = os.path.basename(os.path.dirname(img_path))
    draw.rounded_rectangle((x, y + 210, x + 280, y + 248), radius=8, fill=(240, 240, 240))
    draw.text((x + 12, y + 216), label, fill=(0, 0, 0), font=label_font)
    x += 330
    count += 1
    if count == 6:
        x = 50
        y += 330
        count = 0

canvas.save('real_dataset_more_photos.png')
print('Saved real_dataset_more_photos.png')
