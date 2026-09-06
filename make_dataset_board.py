from PIL import Image, ImageDraw, ImageFont
import os

root = 'DATASETS_ORGANIZED'
classes = ['not_pollinated', 'pollinated', 'pollinating']
selected = []

for c in classes:
    folder = os.path.join(root, 'train', c)
    files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))][:6]
    selected.extend(files)

canvas = Image.new('RGB', (2000, 1100), (255, 255, 255))
draw = ImageDraw.Draw(canvas)

try:
    title_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 38)
    sub_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
except Exception:
    title_font = ImageFont.load_default()
    sub_font = ImageFont.load_default()

draw.text((50, 30), 'Sample Dataset Images for Pollination Classification', fill=(0, 0, 0), font=title_font)

y = 100
x = 50
count = 0

for img_path in selected:
    img = Image.open(img_path).convert('RGB')
    img = img.resize((300, 220))
    canvas.paste(img, (x, y))
    label = os.path.basename(os.path.dirname(img_path))
    draw.rounded_rectangle((x, y + 220, x + 300, y + 255), radius=8, fill=(240, 240, 240))
    draw.text((x + 10, y + 225), label, fill=(0, 0, 0), font=sub_font)
    x += 340
    count += 1
    if count == 4:
        x = 50
        y += 320
        count = 0

canvas.save('dataset_photo_board.png')
print('Saved dataset_photo_board.png')
