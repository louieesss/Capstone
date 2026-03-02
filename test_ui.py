"""
Pollination Classifier - Test UI
----------------------------------
Visual interface to test the trained ResNet50 model on any image or folder.

Run:
    python test_ui.py
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
import torch
import torch.nn as nn
from torchvision import models, transforms

# ── Model config ─────────────────────────────────────────────────────────────
MODEL_PATH   = r"C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth"
CLASS_NAMES  = ['not_pollinated', 'pollinated', 'pollinating']
CLASS_COLORS = {
    'pollinating':   '#27ae60',   # green
    'pollinated':    '#2980b9',   # blue
    'not_pollinated':'#e74c3c',   # red
}
CLASS_EMOJI = {
    'pollinating':    '🐝  POLLINATING',
    'pollinated':     '🌸  POLLINATED',
    'not_pollinated': '🌿  NOT POLLINATED',
}

TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}


# ── Model loading ─────────────────────────────────────────────────────────────
def load_model():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    ck = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    sd = ck.get('model_state_dict', ck) if isinstance(ck, dict) else ck

    # Auto-detect architecture from saved keys
    if any('features' in k for k in sd.keys()):
        # EfficientNet-B3 (train_high_accuracy.py)
        m = models.efficientnet_b3(weights=None)
        in_features = m.classifier[1].in_features
        m.classifier = nn.Sequential(
            nn.Dropout(p=0.4),
            nn.Linear(in_features, 256),
            nn.SiLU(),
            nn.Dropout(p=0.2),
            nn.Linear(256, len(CLASS_NAMES)),
        )
    else:
        # ResNet50 (pollination_training.ipynb)
        m = models.resnet50(weights=None)
        nf = m.fc.in_features
        m.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(nf, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, len(CLASS_NAMES)),
        )
    m.load_state_dict(sd)
    m.to(device)
    m.eval()
    return m, device


def predict(model, device, image_path):
    img = Image.open(image_path).convert('RGB')
    tensor = TRANSFORM(img).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)[0]
    results = {CLASS_NAMES[i]: float(probs[i]) for i in range(len(CLASS_NAMES))}
    top_class = max(results, key=results.get)
    return top_class, results


# ── Main App ──────────────────────────────────────────────────────────────────
class PollinationTestUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🐝 Pollination Classifier — Test UI")
        self.root.geometry("960x720")
        self.root.configure(bg='#1a1a2e')
        self.root.resizable(True, True)

        self.model = None
        self.device = None
        self.folder_images = []
        self.folder_index = 0

        self._build_ui()
        self._load_model_async()

    # ── UI Layout ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg='#16213e', pady=12)
        top.pack(fill=tk.X)

        tk.Label(top, text="🐝 Pollination Classifier", font=('Segoe UI', 22, 'bold'),
                 bg='#16213e', fg='#e2b96f').pack(side=tk.LEFT, padx=20)

        self.status_lbl = tk.Label(top, text="Loading model…",
                                   font=('Segoe UI', 11), bg='#16213e', fg='#aaaaaa')
        self.status_lbl.pack(side=tk.RIGHT, padx=20)

        # ── Button row ───────────────────────────────────────────────────────
        btn_frame = tk.Frame(self.root, bg='#1a1a2e', pady=8)
        btn_frame.pack(fill=tk.X, padx=20)

        btn_style = dict(font=('Segoe UI', 11, 'bold'), relief=tk.FLAT,
                         cursor='hand2', padx=18, pady=8)

        self.btn_image  = tk.Button(btn_frame, text="📂  Open Image",
                                    bg='#0f3460', fg='white',
                                    command=self.open_image, **btn_style)
        self.btn_image.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_folder = tk.Button(btn_frame, text="📁  Open Folder",
                                    bg='#533483', fg='white',
                                    command=self.open_folder, **btn_style)
        self.btn_folder.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_prev   = tk.Button(btn_frame, text="◀  Prev",
                                    bg='#2c3e50', fg='white',
                                    command=self.prev_image, state=tk.DISABLED, **btn_style)
        self.btn_prev.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_next   = tk.Button(btn_frame, text="Next  ▶",
                                    bg='#2c3e50', fg='white',
                                    command=self.next_image, state=tk.DISABLED, **btn_style)
        self.btn_next.pack(side=tk.LEFT, padx=(0, 8))

        self.folder_lbl = tk.Label(btn_frame, text="", font=('Segoe UI', 10),
                                   bg='#1a1a2e', fg='#aaaaaa')
        self.folder_lbl.pack(side=tk.LEFT, padx=8)

        # ── Main content area ────────────────────────────────────────────────
        content = tk.Frame(self.root, bg='#1a1a2e')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # Left: image panel
        img_panel = tk.Frame(content, bg='#16213e', bd=0)
        img_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 10))

        self.img_label = tk.Label(img_panel, bg='#16213e',
                                  text="No image loaded\n\nClick  📂 Open Image  or\n📁 Open Folder  to start",
                                  font=('Segoe UI', 13), fg='#555577')
        self.img_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.filename_lbl = tk.Label(img_panel, text="", font=('Segoe UI', 9),
                                     bg='#16213e', fg='#666688', wraplength=400)
        self.filename_lbl.pack(pady=(0, 6))

        # Right: results panel
        res_panel = tk.Frame(content, bg='#16213e', bd=0)
        res_panel.grid(row=0, column=1, sticky='nsew')

        tk.Label(res_panel, text="PREDICTION", font=('Segoe UI', 11, 'bold'),
                 bg='#16213e', fg='#888899').pack(pady=(18, 4))

        self.pred_label = tk.Label(res_panel, text="—",
                                   font=('Segoe UI', 20, 'bold'),
                                   bg='#16213e', fg='#ffffff',
                                   wraplength=260, justify=tk.CENTER)
        self.pred_label.pack(pady=(0, 4))

        self.pred_frame_color = tk.Frame(res_panel, height=6, bg='#333355')
        self.pred_frame_color.pack(fill=tk.X, padx=30, pady=(0, 20))

        # Confidence bars
        tk.Label(res_panel, text="CONFIDENCE", font=('Segoe UI', 11, 'bold'),
                 bg='#16213e', fg='#888899').pack(pady=(0, 10))

        self.bar_vars   = {}
        self.bar_labels = {}
        self.bar_pct    = {}

        for cls in ['pollinating', 'pollinated', 'not_pollinated']:
            row = tk.Frame(res_panel, bg='#16213e')
            row.pack(fill=tk.X, padx=20, pady=4)

            lbl = tk.Label(row, text=cls.replace('_', ' ').title(),
                           font=('Segoe UI', 10), bg='#16213e', fg='#ccccdd',
                           width=16, anchor='w')
            lbl.pack(side=tk.LEFT)

            var = tk.DoubleVar(value=0)
            bar = ttk.Progressbar(row, variable=var, maximum=100,
                                  length=120, mode='determinate')
            bar.pack(side=tk.LEFT, padx=6)

            pct = tk.Label(row, text="  0.0%", font=('Segoe UI', 10, 'bold'),
                           bg='#16213e', fg='#aaaacc', width=7)
            pct.pack(side=tk.LEFT)

            self.bar_vars[cls]   = var
            self.bar_pct[cls]    = pct

        # Additional info box
        self.info_box = tk.Label(res_panel, text="", font=('Segoe UI', 10),
                                 bg='#0f1e3d', fg='#99bbdd',
                                 justify=tk.LEFT, wraplength=250,
                                 padx=14, pady=12)
        self.info_box.pack(fill=tk.X, padx=20, pady=(24, 0))

        # Style progressbars
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor='#2a2a4a',
                        background='#e2b96f', thickness=14)

    # ── Model loading ─────────────────────────────────────────────────────────
    def _load_model_async(self):
        try:
            self.model, self.device = load_model()
            dev_str = "GPU (CUDA)" if self.device.type == 'cuda' else "CPU"
            self.status_lbl.config(text=f"✅  Model ready  |  {dev_str}", fg='#27ae60')
        except Exception as e:
            self.status_lbl.config(text=f"❌  Model error: {e}", fg='#e74c3c')
            messagebox.showerror("Model Load Error",
                                 f"Could not load model:\n{e}\n\n"
                                 f"Expected: {MODEL_PATH}")

    # ── File / Folder opening ─────────────────────────────────────────────────
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.webp"),
                       ("All files", "*.*")])
        if path:
            self.folder_images = [path]
            self.folder_index  = 0
            self._update_nav()
            self.classify_and_show(path)

    def open_folder(self):
        folder = filedialog.askdirectory(title="Select image folder",
                                         initialdir=r"C:\Users\Admin\Desktop\CAPS\DATASETS")
        if not folder:
            return
        imgs = sorted([str(p) for p in Path(folder).iterdir()
                       if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
        if not imgs:
            messagebox.showwarning("No Images", f"No image files found in:\n{folder}")
            return
        self.folder_images = imgs
        self.folder_index  = 0
        self._update_nav()
        self.classify_and_show(imgs[0])

    def prev_image(self):
        if self.folder_index > 0:
            self.folder_index -= 1
            self._update_nav()
            self.classify_and_show(self.folder_images[self.folder_index])

    def next_image(self):
        if self.folder_index < len(self.folder_images) - 1:
            self.folder_index += 1
            self._update_nav()
            self.classify_and_show(self.folder_images[self.folder_index])

    def _update_nav(self):
        total = len(self.folder_images)
        idx   = self.folder_index
        self.btn_prev.config(state=tk.NORMAL if idx > 0           else tk.DISABLED)
        self.btn_next.config(state=tk.NORMAL if idx < total - 1   else tk.DISABLED)
        if total > 1:
            self.folder_lbl.config(text=f"Image {idx+1} / {total}")
        else:
            self.folder_lbl.config(text="")

    # ── Classification & display ──────────────────────────────────────────────
    def classify_and_show(self, image_path):
        if self.model is None:
            messagebox.showwarning("Model not ready", "The model has not loaded yet.")
            return

        # Show the image
        self._display_image(image_path)
        self.filename_lbl.config(text=os.path.basename(image_path))

        # Run inference
        try:
            top_class, probs = predict(self.model, self.device, image_path)
        except Exception as e:
            messagebox.showerror("Inference Error", str(e))
            return

        # Update prediction label
        color = CLASS_COLORS[top_class]
        label = CLASS_EMOJI[top_class]
        self.pred_label.config(text=label, fg=color)
        self.pred_frame_color.config(bg=color)

        # Update bars
        for cls in CLASS_NAMES:
            pct_val = probs[cls] * 100
            self.bar_vars[cls].set(pct_val)
            self.bar_pct[cls].config(text=f"{pct_val:5.1f}%",
                                      fg=CLASS_COLORS[cls] if cls == top_class else '#aaaacc')

        # Info box
        conf = probs[top_class] * 100
        desc = {
            'pollinating':    "Bees or insects are actively\ngathering pollen/nectar.",
            'pollinated':     "Flowers show signs of\nsuccessful pollination.",
            'not_pollinated': "Flowers have not yet been\nvisited by pollinators.",
        }
        self.info_box.config(
            text=f"Top confidence:  {conf:.1f}%\n\n{desc[top_class]}"
        )

    def _display_image(self, image_path):
        img = Image.open(image_path).convert('RGB')

        # Fit inside the label area (max ~520×480)
        max_w, max_h = 520, 480
        img.thumbnail((max_w, max_h), Image.LANCZOS)

        photo = ImageTk.PhotoImage(img)
        self.img_label.config(image=photo, text='')
        self.img_label.image = photo   # keep reference


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = PollinationTestUI(root)
    root.mainloop()
