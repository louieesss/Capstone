from PIL import Image, ImageDraw, ImageFont

curve = Image.open('training_curve.png').convert('RGB')
cm = Image.open('confusion_matrix.png').convert('RGB')

curve = curve.resize((1200, 700))
cm = cm.resize((620, 620))

canvas = Image.new('RGB', (1900, 1000), 'white')
draw = ImageDraw.Draw(canvas)

# Background panels
panel_color = (245, 247, 250)
for x, y, w, h in [
    (30, 120, 1280, 770),
    (1320, 120, 540, 770),
]:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=25, fill=panel_color)

# Title
try:
    title_font = ImageFont.truetype('arial.ttf', 42)
    subtitle_font = ImageFont.truetype('arial.ttf', 24)
except Exception:
    title_font = ImageFont.load_default()
    subtitle_font = ImageFont.load_default()

draw.text((60, 40), 'Pollination Classification Model Performance', fill='black', font=title_font)
draw.text((60, 90), 'Training curve and confusion matrix for the final model', fill=(80, 80, 80), font=subtitle_font)

# Place actual graph images
canvas.paste(curve, (60, 150))
canvas.paste(cm, (1360, 180))

# Add small labels
label_font = ImageFont.truetype('arial.ttf', 20)
draw.text((60, 150), 'A. Training curve', fill='black', font=label_font)
draw.text((1360, 180), 'B. Confusion matrix', fill='black', font=label_font)

# Add simple summary box
summary_box = (60, 860, 760, 960)
draw.rounded_rectangle(summary_box, radius=18, fill=(230, 240, 255))
draw.text((90, 885), 'Model summary', fill='black', font=title_font)
draw.text((90, 930), 'Input: bee pollination images', fill=(30, 30, 30), font=subtitle_font)
draw.text((90, 960), 'Output: 3 classes (not pollinated, pollinated, pollinating)', fill=(30, 30, 30), font=subtitle_font)

canvas.save('paper_ready_figure.png')
print('Saved paper_ready_figure.png')
