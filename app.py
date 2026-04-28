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
from picamera2 import Picamera2

# ─── CONFIG (editable via /control) ─────────────────────────────────────────
CONFIG = {
    'model_path':           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'best_model_checkpoint.pth'),
    'snapshot_dir':         os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots'),
    'camera_id':            0,
    'infer_every':          3,
    'stable_frames':        5,
    'max_history':          200,
    'jpeg_quality':         80,
    'confidence_threshold': 0.35,
}

CLASS_NAMES  = ['not_pollinated', 'pollinated', 'pollinating']
CLASS_LABELS = {'not_pollinated': 'Not Pollinated',
                'pollinated':     'Pollinated',
                'pollinating':    'Pollinating'}
CLASS_HEX    = {'not_pollinated': '#f87171',
                'pollinated':     '#60a5fa',
                'pollinating':    '#34d399'}
CLASS_BGR    = {'not_pollinated': (60,60,220),
                'pollinated':     (200,130,40),
                'pollinating':    (60,180,60)}

# ─── APP ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
os.makedirs(CONFIG['snapshot_dir'], exist_ok=True)

# ─── SHARED STATE ────────────────────────────────────────────────────────────
lock          = threading.Lock()
current_frame = None
cam_running   = False

state = {'label':'initializing','confidence':0.0,
         'probs':{c:0.0 for c in CLASS_NAMES},'timestamp':''}
history       = []
snapshot_list = []
stable_count  = 0
last_stable   = None
session_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
total_snaps   = 0

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
    global current_frame, state, history, stable_count, last_stable, cam_running
    try:
        picam2 = Picamera2(CONFIG['camera_id'])
        cfg = picam2.create_preview_configuration(
            main={'format': 'RGB888', 'size': (640, 480)})
        picam2.configure(cfg)
        picam2.start()
        time.sleep(0.5)  # let camera warm up
    except Exception as e:
        print(f'ERROR: Cannot open Pi camera {CONFIG["camera_id"]}: {e}')
        cam_running = False
        return
    cam_running = True
    idx=0; label=CLASS_NAMES[0]; conf=0.0; probs={c:0.0 for c in CLASS_NAMES}
    try:
        while cam_running:
            rgb = picam2.capture_array()          # H×W×3 RGB numpy array
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)  # convert to BGR for cv2
            idx += 1
            if idx % CONFIG['infer_every'] == 0:
                l,c,p = predict(frame)
                if c >= CONFIG['confidence_threshold']:
                    label,conf,probs = l,c,p
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with lock:
                    state = {'label':label,'confidence':conf,'probs':probs,'timestamp':ts}
                if label == last_stable: stable_count += 1
                else: stable_count=1; last_stable=label
                if stable_count == CONFIG['stable_frames']:
                    fn = save_snapshot(frame.copy(), label, conf)
                    rec = {'label':label,'confidence':f'{conf*100:.1f}%',
                           'confidence_raw':round(conf*100,1),'timestamp':ts,'snapshot':fn}
                    with lock:
                        history.insert(0, rec)
                        if len(history) > CONFIG['max_history']: history.pop()
            h,w = frame.shape[:2]; color=CLASS_BGR.get(label,(180,180,180))
            disp = frame.copy()
            cv2.rectangle(disp,(0,0),(w,55),(10,15,25),-1)
            cv2.rectangle(disp,(0,0),(w,55),color,2)
            cv2.putText(disp,f'{CLASS_LABELS.get(label,label)}  {conf*100:.1f}%',
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
    finally:
        picam2.stop()
        picam2.close()
        cam_running = False

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
                        'sensors':sensor_state})

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
    for k in ('infer_every','stable_frames','jpeg_quality','camera_id'):
        if k in d: CONFIG[k] = int(d[k])
    if 'confidence_threshold' in d:
        CONFIG['confidence_threshold'] = float(d['confidence_threshold'])
    return jsonify({'status':'ok','config':CONFIG})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    with lock: history.clear(); snapshot_list.clear()
    return jsonify({'status':'cleared'})

# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('='*55)
    print('  POLLINATION MONITORING SYSTEM')
    print('  Dashboard : http://localhost:5000')
    print('  Report    : http://localhost:5000/report')
    print('  Control   : http://localhost:5000/control')
    print('='*55)
    # Auto-start camera on launch
    threading.Thread(target=camera_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
