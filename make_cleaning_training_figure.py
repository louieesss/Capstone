from PIL import Image, ImageDraw, ImageFont

canvas = Image.new('RGB', (1800, 1100), 'white')
draw = ImageDraw.Draw(canvas)

# Colors
blue = (58, 120, 220)
green = (60, 160, 100)
orange = (230, 140, 40)
red = (200, 70, 70)
gray = (80, 80, 80)
light = (245, 247, 250)
outline = (210, 220, 230)

try:
    title_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 34)
    heading_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 24)
    body_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
except Exception:
    title_font = ImageFont.load_default()
    heading_font = ImageFont.load_default()
    body_font = ImageFont.load_default()

draw.text((350, 40), 'Data Cleaning and Training Workflow', fill=(20,20,20), font=title_font)

# Step 3 box
x1, y1, x2, y2 = 90, 170, 520, 420
box_color = red
draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=light, outline=box_color, width=3)
draw.text((160, 205), 'Step 3', fill=box_color, font=heading_font)
draw.text((150, 245), 'Data Cleaning', fill=(20,20,20), font=heading_font)
draw.text((130, 285), '• Remove unusable images', fill=gray, font=body_font)
draw.text((130, 315), '• Correct labeling errors', fill=gray, font=body_font)
draw.text((130, 345), '• Standardize image format', fill=gray, font=body_font)

draw.text((130, 375), 'Only clean, valid data continues to training', fill=(80,80,80), font=body_font)

# Arrow
arrow_y = (y1 + y2) / 2
arrow_start = x2 + 40
arrow_end = 760

draw.line((arrow_start, arrow_y, arrow_end, arrow_y), fill=(100,100,100), width=4)
draw.polygon([(arrow_end-20, arrow_y-14), (arrow_end, arrow_y), (arrow_end-20, arrow_y+14)], fill=(100,100,100))

# Step 4 box
x1, y1, x2, y2 = 780, 170, 1220, 420
box_color = blue
draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=light, outline=box_color, width=3)
draw.text((890, 205), 'Step 4', fill=box_color, font=heading_font)
draw.text((860, 245), 'Dataset Splitting', fill=(20,20,20), font=heading_font)
draw.text((845, 285), '• Train set', fill=gray, font=body_font)
draw.text((845, 315), '• Validation set', fill=gray, font=body_font)
draw.text((845, 345), '• Test set', fill=gray, font=body_font)

draw.text((845, 375), 'Used for learning, monitoring, and final testing', fill=(80,80,80), font=body_font)

# Arrow
arrow_y2 = (y1 + y2) / 2
arrow_start2 = x2 + 40
arrow_end2 = 1460

draw.line((arrow_start2, arrow_y2, arrow_end2, arrow_y2), fill=(100,100,100), width=4)
draw.polygon([(arrow_end2-20, arrow_y2-14), (arrow_end2, arrow_y2), (arrow_end2-20, arrow_y2+14)], fill=(100,100,100))

# Step 5 box
x1, y1, x2, y2 = 1480, 170, 1720, 420
box_color = green
draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=light, outline=box_color, width=3)
draw.text((1550, 205), 'Step 5', fill=box_color, font=heading_font)
draw.text((1525, 245), 'Model Training', fill=(20,20,20), font=heading_font)
draw.text((1520, 285), '• Multi-epoch learning', fill=gray, font=body_font)
draw.text((1520, 315), '• Parameter updates', fill=gray, font=body_font)
draw.text((1520, 345), '• Checkpoints saved', fill=gray, font=body_font)

# Lower panel
panel = (120, 500, 1680, 980)
draw.rounded_rectangle(panel, radius=25, fill=(245,247,250), outline=outline, width=2)

draw.text((170, 545), 'Training process summary', fill=(20,20,20), font=heading_font)
summary = [
    '1. Unusable images are removed to improve the quality of the dataset.',
    '2. Labeling errors are corrected so each image belongs to the correct class.',
    '3. The dataset is divided into train, validation, and test subsets.',
    '4. The model is trained over multiple epochs to reduce error and improve learning.',
    '5. Validation and test results are used to compare the model performance.',
]

for i, line in enumerate(summary):
    draw.text((170, 585 + i*75), line, fill=gray, font=body_font)

# Footer
footer = 'This workflow is used to prepare the flower image dataset and train the pollination classifier.'
draw.text((170, 930), footer, fill=(60,60,60), font=body_font)

canvas.save('data_cleaning_training_workflow.png')
print('Saved data_cleaning_training_workflow.png')
