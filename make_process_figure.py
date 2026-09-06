from PIL import Image, ImageDraw, ImageFont

canvas = Image.new('RGB', (1800, 900), 'white')
draw = ImageDraw.Draw(canvas)

# Colors
blue = (58, 120, 220)
green = (45, 160, 80)
orange = (230, 140, 40)
purple = (120, 90, 180)
gray = (80, 80, 80)
light = (242, 246, 250)
outline = (210, 220, 230)

# Title
try:
    title_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 34)
    box_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 20)
    small_font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
except Exception:
    title_font = ImageFont.load_default()
    box_font = ImageFont.load_default()
    small_font = ImageFont.load_default()

draw.text((420, 30), 'Research Workflow for Pollination Image Classification', fill=(20,20,20), font=title_font)

# Boxes
boxes = [
    {'xy': (70, 140, 350, 260), 'color': blue, 'title': 'Step 3', 'text': 'Data cleaning and\npreprocessing', 'sub': 'Remove unusable images\nand standardize inputs'},
    {'xy': (430, 140, 710, 260), 'color': green, 'title': 'Step 4', 'text': 'Dataset splitting', 'sub': 'Train / validation / test'},
    {'xy': (790, 140, 1070, 260), 'color': orange, 'title': 'Step 5', 'text': 'Model training', 'sub': 'Run the training program\nfor multiple epochs'},
    {'xy': (1150, 140, 1430, 260), 'color': purple, 'title': 'Step 6', 'text': 'Evaluation', 'sub': 'Measure accuracy, loss,\nand confusion matrix'},
    {'xy': (1510, 140, 1710, 260), 'color': (90, 120, 150), 'title': 'Step 7', 'text': 'Model use', 'sub': 'Deploy for live\nclassification'}
]

for b in boxes:
    x1, y1, x2, y2 = b['xy']
    draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=light, outline=b['color'], width=3)
    draw.rounded_rectangle((x1+12, y1+12, x2-12, y2-12), radius=18, fill=(255,255,255), outline=b['color'], width=1)
    draw.text((x1+25, y1+20), b['title'], fill=b['color'], font=box_font)
    draw.text((x1+25, y1+60), b['text'], fill=(20,20,20), font=box_font)
    draw.text((x1+25, y1+110), b['sub'], fill=gray, font=small_font)

# Arrows between boxes
for i in range(len(boxes)-1):
    x1, y1, x2, y2 = boxes[i]['xy']
    x3, y3, x4, y4 = boxes[i+1]['xy']
    arrow_x1 = x2 - 10
    arrow_x2 = x3 + 10
    ymid = (y1 + y2) / 2
    draw.line((arrow_x1, ymid, arrow_x2, ymid), fill=(120,120,120), width=3)
    draw.polygon([(arrow_x2-18, ymid-12), (arrow_x2, ymid), (arrow_x2-18, ymid+12)], fill=(120,120,120))

# Additional explanation panel
panel = (120, 360, 1680, 760)
draw.rounded_rectangle(panel, radius=25, fill=(245,247,250), outline=outline, width=2)

draw.text((170, 395), 'Workflow description', fill=(20,20,20), font=box_font)

lines = [
    '• Data cleaning and preprocessing remove unusable images and correct labeling issues before training.',
    '• Dataset splitting separates the data into training, validation, and testing subsets.',
    '• Training uses multiple epochs so the model can learn, update parameters, and generate checkpoints.',
    '• Validation monitors generalization and helps compare model performance across experiments.',
    '• Testing provides the final unbiased evaluation of the trained model.',
]

for idx, line in enumerate(lines):
    draw.text((170, 445 + idx*62), line, fill=gray, font=small_font)

# Footer note
foot = 'This workflow follows the project methodology for image preparation, model learning, and evaluation.'
draw.text((170, 780), foot, fill=(60,60,60), font=small_font)

canvas.save('workflow_figure.png')
print('Saved workflow_figure.png')
