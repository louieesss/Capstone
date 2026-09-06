"""
Pollination Monitoring System — Flask Backend
==============================================
Pages:
  /          → Dashboard  (live camera + real-time classification)
  /report    → Report     (history table, charts, snapshot gallery)
  /control   → Control    (camera settings, model config)

Run:
    python app.py
Open: http://localhost:5000
"""

import os, cv2, time, threading, random, math
from datetime import datetime

import torch, torch.nn as nn, numpy as np
from torchvision import models, transforms
from PIL import Image
from flask import (Flask, Response, render_template, jsonify,
                   send_from_directory, request)
import io

try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

try:
    from supabase import create_client
except Exception:
    create_client = None

# ─── CONFIG (editable via /control) ─────────────────────────────────────────
CONFIG = {
    'model_path':           r'C:\Users\Admin\Desktop\CAPS\best_model_checkpoint.pth',
    'snapshot_dir':         r'C:\Users\Admin\Desktop\CAPS\snapshots',
    'camera_id':            0,
    'infer_every':          3,
    'stable_frames':        5,
    'max_history':          200,
    'jpeg_quality':         80,
    'confidence_threshold': 0.35,
    'block_humans':         True,
    'min_subject_texture':  35.0,
    'min_subject_edge':     0.015,
    'zoom_factor':          1.0,
    'snapshot_interval_sec': 10800,
    # Coconut detection settings
    'coconut_reject_confidence':  0.15,   # MobileNetV2 reject threshold
    'coconut_model_min_conf':     0.30,   # Min pollination-model confidence
    'coconut_max_entropy':        1.098,  # Max entropy (log(3)=1.099 = perfectly uniform)
}

CLASS_NAMES  = ['not_pollinated', 'pollinated', 'pollinating']
BLOCKED_LABEL = 'blocked'
CLASS_LABELS = {'not_pollinated': 'Not Pollinating',
                'pollinated':     'Pollinated',
                'pollinating':    'Pollinating',
                BLOCKED_LABEL:    'No Valid Subject'}
CLASS_HEX    = {'not_pollinated': '#f87171',
                'pollinated':     '#34d399',
                'pollinating':    '#fbbf24',
                BLOCKED_LABEL:    '#94a3b8'}
CLASS_BGR    = {'not_pollinated': (60,60,220),
                'pollinated':     (60,180,60),
                'pollinating':    (36,191,251),
                BLOCKED_LABEL:    (150,150,150)}

# ─── APP ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
if HAS_CORS:
    CORS(app, origins='*', supports_credentials=True)
os.makedirs(CONFIG['snapshot_dir'], exist_ok=True)


# ─── SHARED STATE ────────────────────────────────────────────────────────────
lock          = threading.Lock()
current_frame = None
cam_running   = False

state = {'label':'initializing','confidence':0.0,
         'probs':{c:0.0 for c in CLASS_NAMES},'timestamp':'',
         'subject_status':'initializing'}
history       = []
snapshot_list = []
# Populate snapshot_list from existing files (useful for testing)
try:
    for fn in sorted(os.listdir(CONFIG['snapshot_dir']), reverse=True):
        if fn.lower().endswith(('.jpg', '.jpeg', '.png')):
            snapshot_list.append(fn)
    snapshot_list = snapshot_list[:500]
except Exception:
    pass
stable_count  = 0
last_stable   = None
session_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
total_snaps   = 0
last_snapshot_ts = 0.0

# ─── OPTIONAL SUPABASE ───────────────────────────────────────────────────────
SUPABASE_URL = os.getenv('SUPABASE_URL', '').strip()
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '').strip()
supabase_client = None
if create_client and SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print('  Supabase connected')
    except Exception as e:
        print(f'  Supabase disabled: {e}')


def supabase_log_detection(record):
    if not supabase_client:
        return
    try:
        payload = {
            'label': record['label'],
            'pollination_status': record['label'],
            'confidence': float(record['confidence_raw']),
            'timestamp': record['timestamp'],
            'snapshot': record.get('snapshot') or None,
        }
        supabase_client.table('detections').insert(payload).execute()
    except Exception as e:
        print(f'  Supabase insert failed: {e}')


def apply_zoom(frame, zoom_factor):
    if zoom_factor <= 1.0:
        return frame
    h, w = frame.shape[:2]
    new_w = max(2, int(w / zoom_factor))
    new_h = max(2, int(h / zoom_factor))
    x1 = (w - new_w) // 2
    y1 = (h - new_h) // 2
    cropped = frame[y1:y1+new_h, x1:x1+new_w]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

# ─── SENSOR STATE ────────────────────────────────────────────────────────────
# Real Raspberry Pi: replace simulation with GPIO/I2C reads (DHT22, SHT30, BH1750)
sensor_state = {
    'temperature': 27.0,   # °C
    'humidity':    62.0,   # %RH
    'light':       520.0,  # lux
    'updated':     '',
}
_sensor_t0 = time.time()  # phase reference for smooth simulation

def sensor_loop():
    """Simulates sensor readings. Replace body with real sensor reads on Pi."""
    global sensor_state
    while True:
        t = time.time() - _sensor_t0
        temp  = 26.5 + 1.5*math.sin(t/120) + random.gauss(0, 0.08)
        hum   = 60.0 + 5.0*math.sin(t/90 + 1) + random.gauss(0, 0.3)
        light = max(0, 500 + 200*math.sin(t/60 + 2) + random.gauss(0, 8))
        sensor_state = {
            'temperature': round(temp, 1),
            'humidity':    round(hum, 1),
            'light':       round(light, 1),
            'updated':     datetime.now().strftime('%H:%M:%S'),
        }
        time.sleep(3)

# Start sensor thread immediately
threading.Thread(target=sensor_loop, daemon=True).start()

# ─── MODEL ───────────────────────────────────────────────────────────────────
def load_model():
    dev  = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    ckpt = torch.load(CONFIG['model_path'], map_location=dev, weights_only=False)
    sz   = ckpt.get('image_size', 160)
    m    = models.efficientnet_b3(weights=None)
    inf  = m.classifier[1].in_features
    m.classifier = nn.Sequential(
        nn.Dropout(0.4), nn.Linear(inf,256), nn.SiLU(),
        nn.Dropout(0.2), nn.Linear(256, len(CLASS_NAMES)))
    m.load_state_dict(ckpt['model_state_dict'])
    m.to(dev).eval()
    tf = transforms.Compose([
        transforms.Resize((sz+32,sz+32)), transforms.CenterCrop(sz),
        transforms.ToTensor(),
        transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])])
    print(f'  Model loaded — device={dev}  size={sz}')
    return m, tf, dev

MODEL, TF, DEVICE = load_model()

# ─── COCONUT DETECTOR (MobileNetV2 + entropy analysis) ───────────────────────
def load_coconut_detector():
    """Load MobileNetV2 (ImageNet) for non-coconut object rejection."""
    try:
        from torchvision.models import mobilenet_v2, MobileNet_V2_Weights
        weights = MobileNet_V2_Weights.IMAGENET1K_V1
        detector = mobilenet_v2(weights=weights).to(DEVICE).eval()
        det_tf = weights.transforms()
        categories = weights.meta['categories']
        print(f'  Coconut detector loaded (MobileNetV2, {len(categories)} ImageNet classes)')
        return detector, det_tf, categories
    except Exception as e:
        print(f'  WARNING: Coconut detector failed to load: {e}')
        return None, None, None

COCONUT_DETECTOR, COCONUT_DET_TF, IMAGENET_CATEGORIES = load_coconut_detector()

# Non-coconut ImageNet class indices to reject
# Dogs (151-268), cats (281-285), people/clothing, vehicles, electronics, etc.
REJECT_CLASS_INDICES = set()

# Dog breeds: 151-268
REJECT_CLASS_INDICES.update(range(151, 269))
# Cat breeds: 281-285
REJECT_CLASS_INDICES.update(range(281, 286))

# Add by keyword matching
if IMAGENET_CATEGORIES:
    _REJECT_KEYWORDS = [
        # People / clothing
        'wig', 'mask', 'bib', 'maillot', 'bikini', 'miniskirt', 'jean',
        'suit', 'jersey', 'gown', 'cloak', 'diaper', 'pajama',
        # Vehicles
        'car', 'cab', 'jeep', 'van', 'ambulance', 'truck', 'trailer',
        'bus', 'minibus', 'trolleybus', 'motorcycle', 'moped', 'bicycle',
        'scooter', 'tank', 'tractor', 'aircraft', 'airliner', 'warplane',
        'speedboat', 'gondola', 'canoe', 'catamaran', 'sailboat',
        'locomotive', 'freight',
        # Electronics
        'laptop', 'notebook', 'desktop', 'monitor', 'screen', 'television',
        'phone', 'cellular', 'iPod', 'mouse', 'keyboard', 'remote',
        'printer', 'modem', 'speaker', 'microphone', 'joystick',
        # Documents / office
        'envelope', 'book', 'newspaper', 'comic', 'binder', 'paper towel',
        # Furniture / indoor
        'desk', 'chair', 'throne', 'bench', 'couch', 'cradle', 'crib',
        'wardrobe', 'filing cabinet', 'medicine chest',
        # Buildings / structures
        'church', 'castle', 'palace', 'mosque', 'monastery', 'dome',
        'beacon', 'bridge', 'dam', 'fountain', 'barn', 'greenhouse',
        # Animals (misc)
        'goldfish', 'shark', 'whale', 'penguin', 'ostrich', 'flamingo',
        'pelican', 'scorpion', 'tarantula', 'centipede', 'gecko', 'iguana',
        'chameleon', 'snake', 'cobra', 'turtle', 'crocodile', 'alligator',
        'frog', 'toad', 'rabbit', 'hamster', 'squirrel', 'fox', 'wolf',
        'bear', 'monkey', 'gorilla', 'chimpanzee', 'baboon', 'lion',
        'tiger', 'leopard', 'elephant', 'zebra', 'hippopotamus', 'rhinoceros',
    ]
    for i, cat in enumerate(IMAGENET_CATEGORIES):
        cl = cat.lower()
        for kw in _REJECT_KEYWORDS:
            if kw.lower() in cl:
                REJECT_CLASS_INDICES.add(i)
                break

print(f'  Rejection list: {len(REJECT_CLASS_INDICES)} non-coconut ImageNet classes')


@torch.no_grad()
def detect_coconut(pil_img):
    """Coconut detection via MobileNetV2 non-coconut rejection.
       Checks if the image matches a known non-coconut category
       (people, animals, vehicles, electronics, etc.).
       Returns (is_coconut, reason, details_dict).
    """
    details = {'stage': 'passed', 'rejected_as': None, 'confidence': 0.0}

    if COCONUT_DETECTOR is None or COCONUT_DET_TF is None:
        # Detector unavailable — allow through with warning
        print('  [coconut-detect] WARNING: detector not loaded, skipping check')
        return True, None, details

    det_tensor = COCONUT_DET_TF(pil_img).unsqueeze(0).to(DEVICE)
    logits = COCONUT_DETECTOR(det_tensor)
    probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
    top10_idx = np.argsort(probs)[-10:][::-1]
    reject_threshold = float(CONFIG.get('coconut_reject_confidence', 0.15))

    # Check if any top prediction is a known non-coconut object
    for idx in top10_idx:
        prob = float(probs[idx])
        if prob < reject_threshold:
            break  # remaining are even lower
        if int(idx) in REJECT_CLASS_INDICES:
            cat_name = IMAGENET_CATEGORIES[idx] if IMAGENET_CATEGORIES else f'class_{idx}'
            details = {
                'stage': 'mobilenet_rejection',
                'rejected_as': cat_name,
                'confidence': round(prob * 100, 1),
                'top_predictions': [
                    {'class': IMAGENET_CATEGORIES[i], 'confidence': round(float(probs[i]) * 100, 1)}
                    for i in top10_idx[:5]
                ],
            }
            print(f'  [coconut-detect] REJECTED: detected "{cat_name}" ({prob*100:.1f}%)')
            return False, f'Image appears to contain "{cat_name}" (not a coconut)', details

    # No reject-class found in top predictions — accept the image
    top1_name = IMAGENET_CATEGORIES[top10_idx[0]] if IMAGENET_CATEGORIES else 'unknown'
    top1_conf = float(probs[top10_idx[0]]) * 100
    details = {
        'stage': 'accepted',
        'top_prediction': top1_name,
        'confidence': round(top1_conf, 1),
    }
    print(f'  [coconut-detect] ACCEPTED: top1="{top1_name}" ({top1_conf:.1f}%), no reject match')
    return True, None, details

HUMAN_DETECTOR = cv2.HOGDescriptor()
HUMAN_DETECTOR.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())


def detect_human(frame):
    if not CONFIG.get('block_humans', True):
        return False
    h, w = frame.shape[:2]
    if w > 480:
        scale = 480.0 / float(w)
        frame = cv2.resize(frame, (480, max(2, int(h * scale))))
    rects, _ = HUMAN_DETECTOR.detectMultiScale(
        frame,
        winStride=(8, 8),
        padding=(8, 8),
        scale=1.05,
    )
    return len(rects) > 0


def frame_has_valid_subject(frame):
    if detect_human(frame):
        return False, 'human detected'

    h, w = frame.shape[:2]
    roi = frame[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
    if roi.size == 0:
        return False, 'no valid subject detected'

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edge_ratio = float(cv2.Canny(gray, 80, 160).mean() / 255.0)

    if texture < float(CONFIG.get('min_subject_texture', 35.0)):
        return False, 'no coconut/flower detected'
    if edge_ratio < float(CONFIG.get('min_subject_edge', 0.015)):
        return False, 'no coconut/flower detected'
    return True, 'subject ready'

@torch.no_grad()
def predict(bgr):
    img   = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    t     = TF(img).unsqueeze(0).to(DEVICE)
    probs = torch.softmax(MODEL(t),1).squeeze().cpu().numpy()
    idx   = int(np.argmax(probs))
    return CLASS_NAMES[idx], float(probs[idx]), {n:float(p) for n,p in zip(CLASS_NAMES,probs)}

# ─── SNAPSHOT ────────────────────────────────────────────────────────────────
def save_snapshot(frame, label, conf):
    global total_snaps
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    fn = f'{label}_{int(conf*100)}pct_{ts}.jpg'
    cv2.imwrite(os.path.join(CONFIG['snapshot_dir'], fn), frame)
    total_snaps += 1
    with lock:
        snapshot_list.insert(0, fn)
        if len(snapshot_list) > 500: snapshot_list.pop()
    print(f'  [snap] {fn}')
    return fn

# ─── CAMERA THREAD ───────────────────────────────────────────────────────────
def camera_loop():
    global current_frame, state, history, stable_count, last_stable, cam_running, last_snapshot_ts
    cap = cv2.VideoCapture(CONFIG['camera_id'])
    if not cap.isOpened():
        print(f'ERROR: Cannot open camera {CONFIG["camera_id"]}'); cam_running=False; return
    cam_running = True
    idx=0; label=CLASS_NAMES[0]; conf=0.0; probs={c:0.0 for c in CLASS_NAMES}
    subject_status = 'initializing'
    while cam_running:
        ret, frame = cap.read()
        if not ret: time.sleep(0.05); continue
        zoomed_frame = apply_zoom(frame, float(CONFIG.get('zoom_factor', 1.0)))
        idx += 1
        if idx % CONFIG['infer_every'] == 0:
            valid_subject, subject_status = frame_has_valid_subject(zoomed_frame)
            if valid_subject:
                l,c,p = predict(zoomed_frame)
                if c >= CONFIG['confidence_threshold']:
                    label,conf,probs = l,c,p
                else:
                    subject_status = 'low confidence'
                    label,conf,probs = BLOCKED_LABEL,0.0,{cname:0.0 for cname in CLASS_NAMES}
                    stable_count = 0
                    last_stable = None
            else:
                label,conf,probs = BLOCKED_LABEL,0.0,{cname:0.0 for cname in CLASS_NAMES}
                stable_count = 0
                last_stable = None
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with lock:
                state = {'label':label,'confidence':conf,'probs':probs,'timestamp':ts,
                         'zoom_factor':CONFIG.get('zoom_factor',1.0),
                         'subject_status':subject_status}
            if label != BLOCKED_LABEL:
                if label == last_stable: stable_count += 1
                else: stable_count=1; last_stable=label
                if stable_count == CONFIG['stable_frames']:
                    fn = ''
                    now_ts = time.time()
                    if now_ts - last_snapshot_ts >= float(CONFIG.get('snapshot_interval_sec', 10800)):
                        fn = save_snapshot(zoomed_frame.copy(), label, conf)
                        last_snapshot_ts = now_ts
                    rec = {'label':label,'confidence':f'{conf*100:.1f}%',
                           'confidence_raw':round(conf*100,1),'timestamp':ts,'snapshot':fn}
                    with lock:
                        history.insert(0, rec)
                        if len(history) > CONFIG['max_history']: history.pop()
                    threading.Thread(target=supabase_log_detection, args=(rec,), daemon=True).start()
        h,w = zoomed_frame.shape[:2]; color=CLASS_BGR.get(label,(180,180,180))
        disp = zoomed_frame.copy()
        cv2.rectangle(disp,(0,0),(w,55),(10,15,25),-1)
        cv2.rectangle(disp,(0,0),(w,55),color,2)
        top_text = f'{CLASS_LABELS.get(label,label)}  {conf*100:.1f}%'
        if label == BLOCKED_LABEL:
            top_text = f'{CLASS_LABELS[BLOCKED_LABEL]}  ({subject_status})'
        cv2.putText(disp,top_text,
                    (12,38),cv2.FONT_HERSHEY_DUPLEX,0.95,color,2,cv2.LINE_AA)
        bx=8; by=h-10-len(CLASS_NAMES)*27; BW=195
        for i,cn in enumerate(CLASS_NAMES):
            pb=probs.get(cn,0.0); y=by+i*27; c2=CLASS_BGR.get(cn,(150,150,150))
            cv2.rectangle(disp,(bx,y),(bx+BW,y+18),(25,25,25),-1)
            cv2.rectangle(disp,(bx,y),(bx+int(BW*pb),y+18),c2,-1)
            cv2.putText(disp,f'{CLASS_LABELS[cn][:12]}: {pb*100:.0f}%',
                        (bx+4,y+13),cv2.FONT_HERSHEY_SIMPLEX,0.43,(210,210,210),1,cv2.LINE_AA)
        cv2.putText(disp,datetime.now().strftime('%H:%M:%S'),(w-75,h-5),
                    cv2.FONT_HERSHEY_SIMPLEX,0.45,(90,90,90),1)
        with lock: current_frame = disp
    cap.release(); cam_running=False

def gen_frames():
    while True:
        with lock: f = current_frame
        if f is None: time.sleep(0.05); continue
        ok,buf = cv2.imencode('.jpg',f,[cv2.IMWRITE_JPEG_QUALITY,CONFIG['jpeg_quality']])
        if not ok: continue
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'+buf.tobytes()+b'\r\n'
        time.sleep(0.04)

# ─── PAGE ROUTES ─────────────────────────────────────────────────────────────
@app.route('/')
def dashboard():
    return render_template('dashboard.html', class_names=CLASS_NAMES,
                           class_labels=CLASS_LABELS, class_hex=CLASS_HEX,
                           cam_running=cam_running)

@app.route('/report')
def report():
    with lock:
        hist=list(history); snaps=list(snapshot_list)
    counts={c:sum(1 for r in hist if r['label']==c) for c in CLASS_NAMES}
    return render_template('report.html', class_names=CLASS_NAMES,
                           class_labels=CLASS_LABELS, class_hex=CLASS_HEX,
                           history=hist, snapshot_list=snaps[:48],
                           counts=counts, total=len(hist),
                           session_start=session_start,
                           total_snaps=total_snaps)

@app.route('/control')
def control():
    return render_template('control.html', config=CONFIG,
                           cam_running=cam_running)

# ─── API ROUTES ──────────────────────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    with lock:
        return jsonify({**state,'cam_running':cam_running,'total_snaps':total_snaps,
                        'sensors':sensor_state,
                        'snapshot_interval_sec':CONFIG.get('snapshot_interval_sec',10800)})

@app.route('/api/sensors')
def api_sensors():
    return jsonify(sensor_state)

@app.route('/api/history')
def api_history():
    with lock: return jsonify(history)

@app.route('/api/stats')
def api_stats():
    with lock: hist=list(history)
    counts={c:sum(1 for r in hist if r['label']==c) for c in CLASS_NAMES}
    recent=[{'label':r['label'],'conf':r['confidence_raw'],'time':r['timestamp'][11:]} for r in hist[:20]]
    return jsonify({'counts':counts,'recent':recent,'total':len(hist),'session_start':session_start})

@app.route('/api/snapshots')
def api_snapshots():
    with lock: return jsonify(snapshot_list[:50])

@app.route('/snapshots/<filename>')
def serve_snapshot(filename):
    return send_from_directory(CONFIG['snapshot_dir'], filename)

@app.route('/api/camera/start', methods=['POST'])
def cam_start():
    global cam_running
    if not cam_running:
        threading.Thread(target=camera_loop, daemon=True).start()
        time.sleep(0.4)
    return jsonify({'cam_running': cam_running})

@app.route('/api/camera/stop', methods=['POST'])
def cam_stop():
    global cam_running
    cam_running = False
    return jsonify({'cam_running': False})

@app.route('/api/config', methods=['POST'])
def update_config():
    d = request.json or {}
    for k in ('infer_every','stable_frames','jpeg_quality','camera_id','max_history'):
        if k in d: CONFIG[k] = int(d[k])
    if 'confidence_threshold' in d:
        CONFIG['confidence_threshold'] = float(d['confidence_threshold'])
    if 'zoom_factor' in d:
        CONFIG['zoom_factor'] = max(1.0, min(4.0, float(d['zoom_factor'])))
    if 'snapshot_interval_hours' in d:
        hours = max(1.0, float(d['snapshot_interval_hours']))
        CONFIG['snapshot_interval_sec'] = int(hours * 3600)
    return jsonify({'status':'ok','config':CONFIG})


@app.route('/api/camera/zoom', methods=['POST'])
def camera_zoom():
    d = request.json or {}
    action = d.get('action', '').lower()
    current = float(CONFIG.get('zoom_factor', 1.0))
    step = 0.2

    if action == 'in':
        current = min(4.0, current + step)
    elif action == 'out':
        current = max(1.0, current - step)
    elif action == 'reset':
        current = 1.0

    CONFIG['zoom_factor'] = round(current, 2)
    return jsonify({'status': 'ok', 'zoom_factor': CONFIG['zoom_factor']})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    global last_snapshot_ts
    with lock: history.clear(); snapshot_list.clear()
    last_snapshot_ts = 0.0
    return jsonify({'status':'cleared'})

# ─── CLASSIFIER API (consumed by frontend clients) ─────────────────────────
# The dataset in DATASETS_ORGANIZED uses the actual pollination classes only.
# Keep the backend aligned with those labels instead of the old mature/tender aliases.
POLLINATION_CLASS_MAP = {
    'pollinating':    'pollinating',
    'not_pollinated': 'not_pollinated',
    'pollinated':     'pollinated',
}

POLLINATION_EMOJI = {
    'not_pollinated': '🔴',
    'pollinating':    '🟡',
    'pollinated':     '🟢',
}

POLLINATION_DISPLAY_LABELS = {
    'not_pollinated': 'NOT POLLINATING',
    'pollinating':    'POLLINATING',
    'pollinated':     'POLLINATED',
}


def _get_visual_signs(label, confidence):
    """Return visual signs detected based on the classification result."""
    signs = {
        'pollinated': [
            'White powder around the coconut button',
            'Visible powder-like coating or residue',
            'Characteristic pollination powder present',
        ],
        'pollinating': [
            'Lighter coconut button ends',
            'Appearance indicates active pollination stage',
            'No characteristic white powder yet visible',
        ],
        'not_pollinated': [
            'Darker coconut button ends',
            'No visible white powder around the button',
            'No signs associated with pollination process',
        ],
    }
    result_signs = signs.get(label, [])
    # For lower confidence, reduce the number of signs reported
    if confidence < 60:
        result_signs = result_signs[:1]
    elif confidence < 80:
        result_signs = result_signs[:2]
    return result_signs


def _detect_ambiguity(probs_dict, top_confidence):
    """Detect if the classification is too ambiguous to report reliably.
       Returns (is_ambiguous, reason)."""
    # If top class confidence is below 50%, it's ambiguous
    if top_confidence < 0.50:
        return True, 'Low confidence — no class reached 50% probability'
    # Check entropy: if distribution is nearly uniform, it's ambiguous
    import math as _math
    values = [v for v in probs_dict.values() if v > 0]
    if values:
        entropy = -sum(v * _math.log(v + 1e-9) for v in values)
        max_entropy = _math.log(len(CLASS_NAMES))  # log(3) ≈ 1.099
        if entropy > 0.95 * max_entropy:
            return True, 'Probabilities are nearly uniform across all classes'
    return False, None

@app.route('/api/classifier/health', methods=['GET'])
def classifier_health():
    """Health check for the classifier API."""
    return jsonify({
        'status': 'healthy',
        'model_loaded': MODEL is not None,
        'device': str(DEVICE),
        'models': ['pollination'],
        'python_version': f'{__import__("sys").version_info.major}.{__import__("sys").version_info.minor}.{__import__("sys").version_info.micro}',
        'torch_version': torch.__version__,
        'cors_enabled': HAS_CORS,
    })


@app.route('/api/classifier/predict', methods=['POST'])
def classifier_predict():
    """Accept an image upload, run the pollination classifier, and return the actual dataset labels."""
    try:
        if 'file' not in request.files:
            print('  [classifier] ERROR: No file in request')
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            print('  [classifier] ERROR: Empty filename')
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        model_type = request.form.get('model_type', 'pollination').lower()
        if model_type not in ('pollination',):
            model_type = 'pollination'

        print(f'  [classifier] Predict request: file={file.filename}, model={model_type}, size={request.content_length or "unknown"} bytes')

        img_bytes = file.read()
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

        is_coconut, reject_reason, detect_details = detect_coconut(pil_img)
        if not is_coconut:
            print(f'  [classifier] Coconut detection FAILED for {file.filename}: {reject_reason}')
            return jsonify({
                'success': False,
                'coconut_detected': False,
                'message': 'No coconut detected. Please capture or upload an image containing a coconut.',
                'detection_details': detect_details,
                'filename': file.filename,
            }), 400

        tensor = TF(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = MODEL(tensor)
            probs_tensor = torch.softmax(logits, dim=1).squeeze().cpu().numpy()

        raw_idx = int(np.argmax(probs_tensor))
        raw_class = CLASS_NAMES[raw_idx]
        raw_conf = float(probs_tensor[raw_idx])
        raw_probs = {name: float(p) for name, p in zip(CLASS_NAMES, probs_tensor)}

        mapped_class = POLLINATION_CLASS_MAP.get(raw_class, raw_class)
        mapped_probs = {label: round(raw_probs.get(label, 0.0) * 100, 2)
                        for label in ['pollinating', 'not_pollinated', 'pollinated']}
        mapped_conf = round(raw_conf * 100, 2)
        model_label = 'EfficientNet-B3 (Pollination Classification)'

        # Ambiguity detection
        is_ambiguous, ambiguity_reason = _detect_ambiguity(raw_probs, raw_conf)
        visual_signs = _get_visual_signs(mapped_class, mapped_conf)

        response = {
            'success': True,
            'coconut_detected': True,
            'prediction': {
                'class': mapped_class,
                'confidence': mapped_conf,
                'all_probabilities': mapped_probs,
                'model': model_label,
            },
            'pollination_status': {
                'status': mapped_class,
                'display_label': POLLINATION_DISPLAY_LABELS.get(mapped_class, mapped_class.upper()),
                'emoji': POLLINATION_EMOJI.get(mapped_class, '⚪'),
                'confidence': mapped_conf,
                'visual_signs': visual_signs,
                'is_ambiguous': is_ambiguous,
                'ambiguity_message': 'Unable to determine pollination status. Please capture another clearer image.' if is_ambiguous else None,
            },
            'raw': {
                'class': raw_class,
                'confidence': round(raw_conf * 100, 2),
                'probabilities': {k: round(v * 100, 2) for k, v in raw_probs.items()},
            },
            'filename': file.filename,
        }

        return jsonify(response)

    except Exception as e:
        print(f'  [classifier] Error: {e}')
        return jsonify({
            'success': False,
            'error': f'Classification failed: {str(e)}',
        }), 500


# ─── UNIFIED PREDICT (pollination-only output aligned to DATASETS_ORGANIZED) ──────

UNIFIED_POLLINATION_CLASSES = {
    'pollinated': {
        'quality': 'White powder is visible around the coconut button, indicating successful pollination.',
        'use': 'The coconut has been pollinated. White powder-like coating or residue is the key visual indicator.',
    },
    'pollinating': {
        'quality': 'Lighter coconut button ends suggest the coconut is currently in the pollination stage.',
        'use': 'The coconut is actively pollinating. No characteristic white powder is visible yet.',
    },
    'not_pollinated': {
        'quality': 'Darker coconut button ends with no signs of white powder or pollination activity.',
        'use': 'The coconut is not yet pollinating. No visible signs of the pollination process.',
    },
}


def _build_pollination_analysis(pred):
    label = pred['class']
    conf = pred['confidence']
    probs = pred['all_probabilities']
    info = UNIFIED_POLLINATION_CLASSES.get(label, UNIFIED_POLLINATION_CLASSES['pollinating'])
    visual_signs = _get_visual_signs(label, conf)

    # Ambiguity detection
    raw_probs = {k: v / 100.0 for k, v in probs.items()}
    is_ambiguous, _ = _detect_ambiguity(raw_probs, conf / 100.0)

    if is_ambiguous:
        obs = 'Unable to determine pollination status. Please capture another clearer image.'
    elif conf > 90:
        obs = f'Very high confidence classification as {POLLINATION_DISPLAY_LABELS.get(label, label)} ({conf:.1f}%).'
    elif conf > 70:
        second = next(((k, v) for k, v in sorted(probs.items(), key=lambda x: -x[1]) if k != label), (None, 0))
        obs = f'Moderate confidence as {POLLINATION_DISPLAY_LABELS.get(label, label)} ({conf:.1f}%). Next likely: {POLLINATION_DISPLAY_LABELS.get(second[0], second[0])} at {second[1]:.1f}%.'
    else:
        obs = f'Low confidence as {POLLINATION_DISPLAY_LABELS.get(label, label)} ({conf:.1f}%). Consider re-capturing the image.'
    return {
        'predictedClass': label,
        'displayLabel': POLLINATION_DISPLAY_LABELS.get(label, label.upper()),
        'emoji': POLLINATION_EMOJI.get(label, '⚪'),
        'confidence': conf,
        'probabilities': probs,
        'qualityDescription': info['quality'],
        'recommendedUse': info['use'],
        'observations': obs,
        'visualSigns': visual_signs,
        'isAmbiguous': is_ambiguous,
        'model': pred['model'],
    }


def _determine_overall(pred):
    label = pred['class']
    conf = pred['confidence']
    display = POLLINATION_DISPLAY_LABELS.get(label, label.upper())
    emoji = POLLINATION_EMOJI.get(label, '⚪')

    # Ambiguity check
    raw_probs = {k: v / 100.0 for k, v in pred['all_probabilities'].items()}
    is_ambiguous, _ = _detect_ambiguity(raw_probs, conf / 100.0)

    if is_ambiguous:
        classification = 'Unable to Determine'
        status = 'ambiguous'
        summary = 'Unable to determine pollination status. Please capture another clearer image.'
    else:
        classification = f'{emoji} {display}'
        status = 'success' if conf >= 70 else 'warning'
        visual_signs = _get_visual_signs(label, conf)
        signs_text = '; '.join(visual_signs[:2]) if visual_signs else ''
        summary = f'The coconut is classified as {display} with {conf:.1f}% confidence. Visual signs: {signs_text}.'
    return {
        'classification': classification,
        'pollination_status': label,
        'display_label': display,
        'emoji': emoji,
        'confidence': conf,
        'status': status,
        'summary': summary,
        'is_ambiguous': is_ambiguous,
    }


def _generate_ai_summary(pollination_analysis, overall):
    if overall.get('is_ambiguous'):
        return 'Unable to determine pollination status. The image quality or angle may not provide enough visual cues. Please capture another clearer image.'
    parts = [f'The uploaded coconut is classified as {overall["display_label"]} with {overall["confidence"]:.1f}% confidence.']
    label = pollination_analysis['predictedClass']
    visual_signs = pollination_analysis.get('visualSigns', [])
    if visual_signs:
        parts.append(f'Visual signs detected: {"; ".join(visual_signs)}.')
    info = UNIFIED_POLLINATION_CLASSES.get(label, UNIFIED_POLLINATION_CLASSES['pollinating'])
    if info.get('use'):
        parts.append(info['use'])
    return ' '.join(parts)


@app.route('/api/classifier/predict-unified', methods=['POST'])
def classifier_predict_unified():
    """Unified prediction using the actual DATASETS_ORGANIZED pollination labels."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        print(f'  [unified] Predict request: file={file.filename}')
        img_bytes = file.read()
        pil_img = Image.open(io.BytesIO(img_bytes)).convert('RGB')

        is_coconut, reject_reason, detect_details = detect_coconut(pil_img)
        if not is_coconut:
            print(f'  [unified] No coconut detected: {reject_reason}')
            return jsonify({
                'success': False,
                'coconutDetected': False,
                'message': 'No coconut detected. Please capture or upload an image containing a coconut.',
                'detectionDetails': detect_details,
                'filename': file.filename,
            })

        tensor = TF(pil_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = MODEL(tensor)
            probs_tensor = torch.softmax(logits, dim=1).squeeze().cpu().numpy()
        raw_idx = int(np.argmax(probs_tensor))
        raw_class = CLASS_NAMES[raw_idx]
        raw_conf = float(probs_tensor[raw_idx])
        raw_probs = {name: float(p) for name, p in zip(CLASS_NAMES, probs_tensor)}

        pollination_mapped_class = POLLINATION_CLASS_MAP.get(raw_class, raw_class)
        pollination_probs = {label: round(raw_probs.get(label, 0.0) * 100, 2)
                            for label in ['pollinating', 'not_pollinated', 'pollinated']}
        pollination_pred = {
            'class': pollination_mapped_class,
            'confidence': round(raw_conf * 100, 2),
            'all_probabilities': pollination_probs,
            'model': 'EfficientNet-B3 (Pollination Classification)',
        }

        overall = _determine_overall(pollination_pred)
        visual_signs = _get_visual_signs(pollination_mapped_class, round(raw_conf * 100, 2))

        print(f'  [unified] Result: {overall["classification"]} ({overall["confidence"]:.1f}%)')
        return jsonify({
            'success': True,
            'coconutDetected': True,
            'filename': file.filename,
            'overall': overall,
            'pollinationStatus': {
                'status': pollination_mapped_class,
                'displayLabel': POLLINATION_DISPLAY_LABELS.get(pollination_mapped_class, pollination_mapped_class.upper()),
                'emoji': POLLINATION_EMOJI.get(pollination_mapped_class, '⚪'),
                'confidence': round(raw_conf * 100, 2),
                'visualSigns': visual_signs,
                'isAmbiguous': overall.get('is_ambiguous', False),
                'probabilities': pollination_probs,
            },
        })

    except Exception as e:
        print(f'  [unified] Error: {e}')
        import traceback; traceback.print_exc()
        return jsonify({'success': False, 'error': f'Classification failed: {str(e)}'}), 500


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    print('='*60)
    print('  COCONUT POLLINATION MONITOR — BACKEND')
    print('='*60)
    print(f'  Python    : {sys.version.split()[0]}')
    print(f'  PyTorch   : {torch.__version__}')
    print(f'  Flask     : {__import__("importlib.metadata", fromlist=["version"]).version("flask")}')
    print(f'  OpenCV    : {cv2.__version__}')
    print(f'  CORS      : {"ENABLED" if HAS_CORS else "DISABLED (install flask-cors)"}')
    print(f'  Device    : {DEVICE}')
    print(f'  Model     : {"LOADED" if MODEL is not None else "FAILED"}')
    print(f'  Detector : {"LOADED" if COCONUT_DETECTOR is not None else "FAILED"}')
    print(f'  Rejects  : {len(REJECT_CLASS_INDICES)} non-coconut ImageNet classes')
    print(f'  Model file: {CONFIG["model_path"]}')
    print('-'*60)
    print('  Endpoints:')
    print('    GET  /api/classifier/health    -> Health check')
    print('    POST /api/classifier/predict   -> Image classification')
    print('    GET  /api/status               -> System status')
    print('-'*60)
    print('  URLs:')
    print('    Dashboard  : http://localhost:5001')
    print('    Health     : http://localhost:5001/api/classifier/health')
    print('    Classifier : http://localhost:5001/api/classifier/predict')
    print('='*60)
    # Camera is NOT auto-started — start it from the Control page or /api/camera/start
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
