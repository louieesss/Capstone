"""
Live Camera Pollination Classifier
====================================
Uses your webcam to classify flowers/bees in real-time.

Controls:
  Q / ESC  — quit
  S        — save a snapshot (snapshot_<n>.jpg)
  SPACE    — pause / resume

Run:
    python camera_classify.py
"""

import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import models, transforms
from PIL import Image
import time
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
MODEL_PATH  = r"C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth"
CAMERA_ID   = 0          # 0 = default webcam, change if you have multiple
DISPLAY_FPS = True
SNAPSHOT_DIR = r"C:\Users\Admin\Desktop\CAPS\snapshots"

# ─── CLASS DISPLAY ───────────────────────────────────────────────────────────
CLASS_LABELS = {
    'not_pollinated': 'NOT POLLINATED',
    'pollinated':     'POLLINATED',
    'pollinating':    'POLLINATING',
}
# BGR colors for OpenCV
CLASS_COLORS_BGR = {
    'not_pollinated': (60,  60,  220),   # red
    'pollinated':     (200, 130,  40),   # blue
    'pollinating':    (60,  180,  60),   # green
}
CLASS_ICONS = {
    'not_pollinated': '[--]',
    'pollinated':     '[**]',
    'pollinating':    '[~~]',
}

# ─── LOAD MODEL ──────────────────────────────────────────────────────────────
def load_model():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    if not isinstance(ckpt, dict):
        raise ValueError("Checkpoint format not recognised.")

    class_names = ckpt.get('class_names', ['not_pollinated', 'pollinated', 'pollinating'])
    image_size  = ckpt.get('image_size', 160)

    # Build EfficientNet-B3 (same architecture as run_training.py)
    model = models.efficientnet_b3(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.4),
        nn.Linear(in_features, 256),
        nn.SiLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, len(class_names)),
    )
    model.load_state_dict(ckpt['model_state_dict'])
    model.to(device).eval()

    tf = transforms.Compose([
        transforms.Resize((image_size + 32, image_size + 32)),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225]),
    ])

    print(f"  Loaded model  — image_size={image_size}  classes={class_names}")
    return model, tf, device, class_names


# ─── INFERENCE ───────────────────────────────────────────────────────────────
@torch.no_grad()
def predict(frame_bgr, model, tf, device, class_names):
    """Run model on a BGR OpenCV frame. Returns (label, confidence, all_probs)."""
    img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
    tensor = tf(img).unsqueeze(0).to(device)
    logits = model(tensor)
    probs  = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
    idx    = int(np.argmax(probs))
    return class_names[idx], float(probs[idx]), probs


# ─── DRAW OVERLAY ────────────────────────────────────────────────────────────
def draw_overlay(frame, label, confidence, all_probs, class_names,
                 fps=None, paused=False):
    h, w = frame.shape[:2]
    color = CLASS_COLORS_BGR.get(label, (200, 200, 200))

    # ── Top banner ──
    cv2.rectangle(frame, (0, 0), (w, 70), (20, 20, 20), -1)
    cv2.rectangle(frame, (0, 0), (w, 70), color, 3)

    display_name = CLASS_LABELS.get(label, label.upper())
    icon         = CLASS_ICONS.get(label, '')
    main_text    = f"{icon}  {display_name}  {confidence*100:.1f}%"
    cv2.putText(frame, main_text, (12, 48),
                cv2.FONT_HERSHEY_DUPLEX, 1.2, color, 2, cv2.LINE_AA)

    # ── Probability bars (bottom-left) ──
    bar_x, bar_y = 10, h - 10 - len(class_names) * 32
    BAR_W = 220
    for i, (cname, prob) in enumerate(zip(class_names, all_probs)):
        y = bar_y + i * 32
        c = CLASS_COLORS_BGR.get(cname, (180, 180, 180))
        cv2.rectangle(frame, (bar_x, y), (bar_x + BAR_W, y + 22), (40, 40, 40), -1)
        fill = int(BAR_W * prob)
        cv2.rectangle(frame, (bar_x, y), (bar_x + fill, y + 22), c, -1)
        cv2.rectangle(frame, (bar_x, y), (bar_x + BAR_W, y + 22), (120,120,120), 1)
        short = CLASS_LABELS.get(cname, cname)[:14]
        cv2.putText(frame, f"{short}: {prob*100:.1f}%",
                    (bar_x + 4, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

    # ── FPS ── source .venv/bin/activate && python app.py
    if fps is not None and DISPLAY_FPS:
        cv2.putText(frame, f"FPS: {fps:.1f}", (w - 110, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 160, 160), 1, cv2.LINE_AA)

    # ── PAUSED banner ──
    if paused:
        cv2.rectangle(frame, (w//2 - 80, h//2 - 25), (w//2 + 80, h//2 + 25),
                      (0, 0, 0), -1)
        cv2.putText(frame, "  PAUSED", (w//2 - 70, h//2 + 10),
                    cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)

    # ── Controls hint ──
    cv2.putText(frame, "Q/ESC=quit  S=snapshot  SPACE=pause",
                (10, h - 10 - len(class_names)*32 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1, cv2.LINE_AA)

    return frame


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  LIVE CAMERA POLLINATION CLASSIFIER")
    print("=" * 55)

    print("\nLoading model...")
    model, tf, device, class_names = load_model()

    print(f"\nOpening camera (id={CAMERA_ID})...")
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print(f"ERROR: Cannot open camera {CAMERA_ID}.")
        print("Try changing CAMERA_ID at the top of this script (0, 1, 2...).")
        return

    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snapshot_count = 0
    paused         = False

    # Warmup
    label, confidence, probs = class_names[0], 0.0, np.ones(len(class_names)) / len(class_names)

    t_prev = time.time()
    fps    = 0.0
    INFER_EVERY = 2   # run model every N frames (keeps display smooth on CPU)
    frame_count = 0

    print("\nCamera is live. Press Q or ESC to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed — retrying...")
            time.sleep(0.1)
            continue

        frame_count += 1

        if not paused and frame_count % INFER_EVERY == 0:
            label, confidence, probs = predict(frame, model, tf, device, class_names)

        # FPS calculation
        now  = time.time()
        fps  = 0.9 * fps + 0.1 * (1.0 / max(now - t_prev, 1e-6))
        t_prev = now

        display = draw_overlay(frame.copy(), label, confidence, probs,
                               class_names, fps=fps, paused=paused)

        cv2.imshow("Pollination Classifier  —  Live Camera", display)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):   # Q or ESC
            break
        elif key == ord(' '):
            paused = not paused
        elif key in (ord('s'), ord('S')):
            path = os.path.join(SNAPSHOT_DIR, f"snapshot_{snapshot_count:04d}.jpg")
            cv2.imwrite(path, display)
            snapshot_count += 1
            print(f"  Snapshot saved: {path}")

    cap.release()
    cv2.destroyAllWindows()
    print("\nCamera closed. Goodbye!")


if __name__ == "__main__":
    main()
