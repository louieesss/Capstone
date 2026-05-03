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

import os, cv2, time, threading, socket
from datetime import datetime

import smbus2

from dht11_gpiod import read_dht11

import torch, torch.nn as nn, numpy as np
from torchvision import models, transforms
from PIL import Image
from flask import (Flask, Response, render_template, jsonify,
                   send_from_directory, request)
from picamera2 import Picamera2
from werkzeug.serving import make_server

import db

# ─── CONFIG (editable via /control) ─────────────────────────────────────────
CONFIG = {
    'model_path':           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'best_model_checkpoint.pth'),
    'snapshot_dir':         os.path.join(os.path.dirname(os.path.abspath(__file__)), 'snapshots'),
    'camera_id':            0,
    'camera_source':        'camera_module',  # 'camera_module' or 'mobile'
    'infer_every':          3,
    'stable_frames':        5,
    'max_history':          200,
    'jpeg_quality':         80,
    'confidence_threshold': 0.35,
    'show_hitboxes':        True,
    'hitbox_min_area':      150,
    'hitbox_max_area':      12000,
    'hitbox_max_count':     20,
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
mobile_frame  = None  # For mobile camera input
cam_running   = False
mobile_cam_active = False
mobile_last_frame_ts = 0.0
MOBILE_SOURCE_LOCK_SECONDS = int(os.getenv('MOBILE_SOURCE_LOCK_SECONDS', '20'))

state = {'label':'initializing','confidence':0.0,
         'probs':{c:0.0 for c in CLASS_NAMES},'timestamp':'',
         'button_count':0}
history       = []
snapshot_list = []
stable_count  = 0
last_stable   = None
session_start = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
total_snaps   = 0

# ─── SENSOR STATE ────────────────────────────────────────────────────────────
BH1750_ADDR_CANDIDATES = (0x23, 0x5C)  # ADDR LOW -> 0x23, ADDR HIGH -> 0x5C
BH1750_CONT_HRES       = 0x10           # Continuous H-Resolution Mode (~1 lux, 120 ms)
DHT11_GPIO_PIN         = 4              # BCM GPIO4 (Pin 7)

sensor_state = {
    'temperature': None,   # °C  (None until first successful read)
    'humidity':    None,   # %RH
    'light':       None,   # lux
    'updated':     '',
    'error':       '',
}

_i2c_bus = None
_bh1750_addr = None


def _init_bh1750():
    """Initialise BH1750 on bus 1, trying 0x23 then 0x5C."""
    global _i2c_bus, _bh1750_addr
    last_error = None
    bus = None

    try:
        bus = smbus2.SMBus(1)
    except Exception as e:
        _i2c_bus = None
        _bh1750_addr = None
        print(f'  [sensor] BH1750 bus open failed: {e}')
        return

    for addr in BH1750_ADDR_CANDIDATES:
        try:
            bus.write_byte(addr, BH1750_CONT_HRES)
            time.sleep(0.18)
            bus.read_i2c_block_data(addr, BH1750_CONT_HRES, 2)
            _i2c_bus = bus
            _bh1750_addr = addr
            print(f'  [sensor] BH1750 initialised at I2C 0x{addr:02X}')
            return
        except Exception as e:
            last_error = e

    try:
        bus.close()
    except Exception:
        pass
    _i2c_bus = None
    _bh1750_addr = None
    print(f'  [sensor] BH1750 init failed on 0x23/0x5C: {last_error}')


_init_bh1750()


def _read_bh1750():
    """Return lux (float) or raise on failure."""
    if _i2c_bus is None or _bh1750_addr is None:
        raise RuntimeError('BH1750 not initialised')
    data = _i2c_bus.read_i2c_block_data(_bh1750_addr, BH1750_CONT_HRES, 2)
    lux  = (data[0] << 8 | data[1]) / 1.2
    return round(lux, 1)


def sensor_loop():
    """Continuously read DHT11 (temp/humidity) and BH1750 (lux)."""
    global sensor_state
    temp = hum = light = None
    while True:
        errors = []

        # ── DHT11 (direct lgpio, no RPi.GPIO/blinka conflicts) ────────────────
        dht_error = None
        for _ in range(3):
            try:
                temp, hum = read_dht11(pin=DHT11_GPIO_PIN)
                dht_error = None
                break
            except RuntimeError as e:
                dht_error = str(e)
                time.sleep(0.2)
            except Exception as e:
                dht_error = str(e)
                break
        if dht_error:
            errors.append(f'DHT11(GPIO{DHT11_GPIO_PIN}): {dht_error}')

        # ── BH1750 ────────────────────────────────────────────────────────────
        if _i2c_bus is not None:
            try:
                light = _read_bh1750()
            except Exception as e:
                errors.append(f'BH1750: {e}')
                _init_bh1750()
                if _i2c_bus is not None:
                    try:
                        light = _read_bh1750()
                    except Exception as e2:
                        errors.append(f'BH1750 retry: {e2}')
        else:
            errors.append('BH1750 not initialised')
            _init_bh1750()

        sensor_state = {
            'temperature': temp,
            'humidity':    hum,
            'light':       light,
            'updated':     datetime.now().strftime('%H:%M:%S'),
            'error':       '; '.join(errors) if errors else '',
        }
        if errors:
            print(f'  [sensor] {"; ".join(errors)}')

        # Log each cycle to DB, including sensor error details when present
        db.log_sensor(temp, hum, light, sensor_state['error'] or None)

        # DHT11 minimum sample interval is ~2 s
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


def get_local_ip():
    """Best-effort LAN IP for opening the app from another device."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def get_default_lan_origin(app_port: int) -> str:
    """Return an override LAN origin if DEFAULT_LAN_HOST is set."""
    host = os.getenv('DEFAULT_LAN_HOST', '').strip()
    if not host:
        return ''
    if '://' in host:
        return host.rstrip('/')
    if ':' in host:
        return f'http://{host}'
    return f'http://{host}:{app_port}'


def _is_mobile_recently_active() -> bool:
    return (time.time() - mobile_last_frame_ts) < MOBILE_SOURCE_LOCK_SECONDS

@torch.no_grad()
def predict(bgr):
    img   = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    t     = TF(img).unsqueeze(0).to(DEVICE)
    probs = torch.softmax(MODEL(t),1).squeeze().cpu().numpy()
    idx   = int(np.argmax(probs))
    return CLASS_NAMES[idx], float(probs[idx]), {n:float(p) for n,p in zip(CLASS_NAMES,probs)}


def detect_button_hitboxes(bgr):
    """Return candidate dwarf-coconut button bounding boxes as (x, y, w, h)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    color_mask = cv2.inRange(
        hsv,
        np.array([10, 35, 70], dtype=np.uint8),
        np.array([48, 255, 255], dtype=np.uint8),
    )

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bright_mask = cv2.threshold(blur, 170, 255, cv2.THRESH_BINARY)

    mask = cv2.bitwise_or(color_mask, bright_mask)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    min_area = int(CONFIG['hitbox_min_area'])
    max_area = int(CONFIG['hitbox_max_area'])
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if w <= 0 or h <= 0:
            continue
        aspect_ratio = w / float(h)
        if aspect_ratio < 0.45 or aspect_ratio > 2.2:
            continue
        extent = area / float((w * h) + 1e-6)
        if extent < 0.35:
            continue
        boxes.append((x, y, w, h, area))

    boxes.sort(key=lambda item: item[4], reverse=True)
    max_count = int(CONFIG['hitbox_max_count'])
    return [(x, y, w, h) for (x, y, w, h, _) in boxes[:max_count]]


def get_roi(frame):
    """Crop a central region to reduce background false positives."""
    h, w = frame.shape[:2]
    pad_x = int(w * float(os.getenv('ROI_PAD_X_PCT', '0.15')))
    pad_y = int(h * float(os.getenv('ROI_PAD_Y_PCT', '0.15')))
    pad_x = max(0, min(pad_x, max(0, (w // 2) - 1)))
    pad_y = max(0, min(pad_y, max(0, (h // 2) - 1)))
    if pad_x == 0 and pad_y == 0:
        return frame, 0, 0
    return frame[pad_y:h - pad_y, pad_x:w - pad_x], pad_x, pad_y


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
    idx=0; label=CLASS_NAMES[0]; conf=0.0; probs={c:0.0 for c in CLASS_NAMES}; button_boxes=[]
    try:
        while cam_running:
            rgb = picam2.capture_array()          # H×W×3 RGB numpy array
            frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)  # convert to BGR for cv2
            idx += 1
            if idx % CONFIG['infer_every'] == 0:
                l,c,p = predict(frame)
                if c >= CONFIG['confidence_threshold']:
                    label,conf,probs = l,c,p
                if CONFIG['show_hitboxes'] and conf >= CONFIG['confidence_threshold']:
                    button_boxes = detect_button_hitboxes(frame)
                else:
                    button_boxes = []
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with lock:
                    state = {'label':label,'confidence':conf,'probs':probs,'timestamp':ts,
                             'button_count':len(button_boxes)}
                if label == last_stable: stable_count += 1
                else: stable_count=1; last_stable=label
                if stable_count == CONFIG['stable_frames']:
                    fn = save_snapshot(frame.copy(), label, conf)
                    rec = {'label':label,'confidence':f'{conf*100:.1f}%',
                           'confidence_raw':round(conf*100,1),'timestamp':ts,'snapshot':fn}
                    with lock:
                        history.insert(0, rec)
                        if len(history) > CONFIG['max_history']: history.pop()
                    # ── Push to database ─────────────────────────────────────
                    db.log_classification(label, conf, probs, fn, sensor_state)
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
            for x, y, w_box, h_box in button_boxes:
                cv2.rectangle(disp, (x, y), (x + w_box, y + h_box), (0, 255, 255), 2)
                cv2.putText(disp, 'Button', (x, max(18, y - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(disp,datetime.now().strftime('%H:%M:%S'),(w-75,h-5),
                        cv2.FONT_HERSHEY_SIMPLEX,0.45,(90,90,90),1)
            with lock: current_frame = disp
    finally:
        picam2.stop()
        picam2.close()
        cam_running = False

def gen_frames():
    while True:
        with lock:
            if CONFIG['camera_source'] == 'mobile' and mobile_frame is not None:
                f = mobile_frame
            else:
                f = current_frame
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

@app.route('/mobile')
def mobile():
    use_https = os.getenv('USE_HTTPS', '0') == '1' or os.getenv('USE_HTPPS', '0') == '1'
    https_port = int(os.getenv('HTTPS_PORT', '5443'))
    app_port = int(os.getenv('APP_PORT', '5000'))
    api_base = get_default_lan_origin(app_port)
    return render_template('mobile.html', class_names=CLASS_NAMES,
                           class_labels=CLASS_LABELS, class_hex=CLASS_HEX,
                           use_https=use_https, https_port=https_port,
                           api_base=api_base)

# ─── API ROUTES ──────────────────────────────────────────────────────────────
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    with lock:
        return jsonify({**state,
                        'cam_running':cam_running,
                        'camera_source': CONFIG['camera_source'],
                        'mobile_cam_active': mobile_cam_active,
                        'mobile_recent': _is_mobile_recently_active(),
                        'total_snaps':total_snaps,
                        'sensors':sensor_state})


@app.route('/api/network_info')
def api_network_info():
    app_port = int(os.getenv('APP_PORT', '5000'))
    override_origin = get_default_lan_origin(app_port)
    local_ip = get_local_ip()
    public_base_url = os.getenv('PUBLIC_BASE_URL', '').strip()
    use_https = os.getenv('USE_HTTPS', '0') == '1' or os.getenv('USE_HTPPS', '0') == '1'
    local_origin = override_origin or f'http://{local_ip}:{app_port}'
    return jsonify({
        'local_mobile_url': f'{local_origin}/mobile',
        'public_mobile_url': f'{public_base_url}/mobile' if public_base_url else '',
        'use_https': use_https,
        'hint': 'Use PUBLIC_BASE_URL with an HTTPS tunnel/domain for off-LAN access.',
    })

@app.route('/api/sensors')
def api_sensors():
    return jsonify(sensor_state)

@app.route('/api/db/health')
def api_db_health():
    health = db.get_health()
    status_code = 200 if health.get('ok') else 503
    return jsonify(health), status_code

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

@app.route('/manifest.webmanifest')
def serve_manifest():
    return send_from_directory('static', 'manifest.webmanifest')

@app.route('/sw.js')
def serve_service_worker():
    return send_from_directory('static', 'sw.js')

@app.route('/offline.html')
def serve_offline_page():
    return send_from_directory('static', 'offline.html')

@app.route('/api/camera/start', methods=['POST'])
def cam_start():
    global cam_running
    if not cam_running and CONFIG['camera_source'] == 'camera_module':
        threading.Thread(target=camera_loop, daemon=True).start()
        time.sleep(0.4)
    return jsonify({'cam_running': cam_running, 'camera_source': CONFIG['camera_source']})

@app.route('/api/camera/stop', methods=['POST'])
def cam_stop():
    global cam_running, mobile_cam_active
    cam_running = False
    mobile_cam_active = False
    return jsonify({'cam_running': False, 'mobile_cam_active': False})

@app.route('/api/camera/set_source', methods=['POST'])
def set_camera_source():
    """Switch between 'camera_module' and 'mobile' camera sources."""
    global cam_running, mobile_cam_active
    d = request.get_json(silent=True) or {}
    source = d.get('source', 'camera_module')
    force = bool(d.get('force', False))
    
    if source not in ['camera_module', 'mobile']:
        return jsonify({'status': 'error', 'message': 'Invalid source'}), 400
    
    # Stop current source if running
    if source == 'camera_module':
        if not force and (mobile_cam_active or _is_mobile_recently_active()):
            return jsonify({
                'status': 'locked',
                'message': 'Mobile stream active recently; pass force=true to override.',
                'camera_source': CONFIG['camera_source'],
                'mobile_cam_active': mobile_cam_active,
            }), 409
        mobile_cam_active = False
        with lock:
            # clear stale mobile frame so stream switches cleanly
            global mobile_frame
            mobile_frame = None
        if not cam_running:
            threading.Thread(target=camera_loop, daemon=True).start()
            time.sleep(0.4)
    elif source == 'mobile':
        cam_running = False
        mobile_cam_active = True
    
    CONFIG['camera_source'] = source
    return jsonify({'status': 'ok', 'camera_source': CONFIG['camera_source'], 
                    'cam_running': cam_running, 'mobile_cam_active': mobile_cam_active})

@app.route('/api/camera/mobile_frame', methods=['POST'])
def receive_mobile_frame():
    """Receive and process frame from mobile camera via WebRTC/Canvas."""
    global mobile_frame, state, history, stable_count, last_stable, mobile_cam_active, cam_running, mobile_last_frame_ts

    def _decode_image_bytes(raw: bytes):
        if not raw:
            return None
        img_array = np.frombuffer(raw, dtype=np.uint8)
        frame_local = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame_local is not None:
            return frame_local
        try:
            import io
            from PIL import Image
            pil_image = Image.open(io.BytesIO(raw)).convert('RGB')
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def _decode_base64_image(data_uri: str):
        if not data_uri:
            return None
        import base64
        encoded = data_uri.split(',', 1)[1] if ',' in data_uri else data_uri
        encoded = ''.join(encoded.split())
        missing_padding = len(encoded) % 4
        if missing_padding:
            encoded += '=' * (4 - missing_padding)
        try:
            raw = base64.b64decode(encoded)
        except Exception:
            return None
        return _decode_image_bytes(raw)
    
    # Be resilient: if phone sends frames, auto-switch source to mobile
    if not mobile_cam_active or CONFIG.get('camera_source') != 'mobile':
        mobile_cam_active = True
        cam_running = False
        CONFIG['camera_source'] = 'mobile'
    
    try:
        # Get image data from request (multipart file, form base64, or JSON base64)
        file_obj = None
        if request.files:
            for key in ('image', 'frame', 'photo', 'file'):
                if key in request.files:
                    file_obj = request.files[key]
                    break
            if file_obj is None:
                file_obj = next(iter(request.files.values()), None)

        if file_obj is not None:
            frame = _decode_image_bytes(file_obj.read())
            if frame is None and request.files:
                for candidate in request.files.values():
                    frame = _decode_image_bytes(candidate.read())
                    if frame is not None:
                        break
        elif 'image_data' in request.form:
            frame = _decode_base64_image(request.form.get('image_data'))
        elif request.is_json:
            payload = request.get_json(silent=True) or {}
            img_data = payload.get('image_data') or payload.get('image')
            frame = _decode_base64_image(img_data)
        else:
            frame = None
        
        if frame is None or frame.size == 0:
            return jsonify({'status': 'error', 'message': 'Invalid frame data'}), 400
        
        # Process frame for inference
        label = CLASS_NAMES[0]
        conf = 0.0
        probs = {c: 0.0 for c in CLASS_NAMES}
        
        roi, off_x, off_y = get_roi(frame)
        l, c, p = predict(roi)
        if c >= CONFIG['confidence_threshold']:
            label, conf, probs = l, c, p
        else:
            label = CLASS_NAMES[0]
            conf = 0.0
            probs = {cname: 0.0 for cname in CLASS_NAMES}
        
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if CONFIG['show_hitboxes'] and conf >= CONFIG['confidence_threshold']:
            button_boxes = detect_button_hitboxes(roi)
            if off_x or off_y:
                button_boxes = [(x + off_x, y + off_y, w_box, h_box)
                                for (x, y, w_box, h_box) in button_boxes]
        else:
            button_boxes = []
        mobile_disp = frame.copy()
        for x, y, w_box, h_box in button_boxes:
            cv2.rectangle(mobile_disp, (x, y), (x + w_box, y + h_box), (0, 255, 255), 2)
            cv2.putText(mobile_disp, 'Button', (x, max(18, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        with lock:
            state = {'label': label, 'confidence': conf, 'probs': probs, 'timestamp': ts,
                     'button_count': len(button_boxes)}
            mobile_frame = mobile_disp
        mobile_last_frame_ts = time.time()
        
        # Handle stable frame detection and snapshotting
        if label == last_stable:
            stable_count += 1
        else:
            stable_count = 1
            last_stable = label
        
        if stable_count == CONFIG['stable_frames']:
            fn = save_snapshot(frame.copy(), label, conf)
            rec = {'label': label, 'confidence': f'{conf*100:.1f}%',
                   'confidence_raw': round(conf*100, 1), 'timestamp': ts, 'snapshot': fn}
            with lock:
                history.insert(0, rec)
                if len(history) > CONFIG['max_history']:
                    history.pop()
            # Push to database
            db.log_classification(label, conf, probs, fn, sensor_state)
        
        return jsonify({'status': 'ok', 'label': label, 'confidence': f'{conf*100:.1f}%',
            'button_count': len(button_boxes),
                'camera_source': CONFIG['camera_source']})
    
    except Exception as e:
        print(f'  [mobile] Error processing frame: {e}')
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def update_config():
    d = request.json or {}
    for k in ('infer_every','stable_frames','jpeg_quality','camera_id','camera_source',
              'hitbox_min_area','hitbox_max_area','hitbox_max_count'):
        if k in d:
            if k == 'camera_source':
                if d[k] in ['camera_module', 'mobile']:
                    CONFIG[k] = d[k]
            else:
                CONFIG[k] = int(d[k])
    if 'confidence_threshold' in d:
        CONFIG['confidence_threshold'] = float(d['confidence_threshold'])
    if 'show_hitboxes' in d:
        v = d['show_hitboxes']
        CONFIG['show_hitboxes'] = v if isinstance(v, bool) else str(v).lower() in ('1', 'true', 'yes', 'on')
    return jsonify({'status':'ok','config':CONFIG})

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    with lock: history.clear(); snapshot_list.clear()
    return jsonify({'status':'cleared'})

# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    start_source = os.getenv('START_CAMERA_SOURCE', '').strip().lower()
    if start_source in ('camera_module', 'mobile'):
        CONFIG['camera_source'] = start_source

    use_https = os.getenv('USE_HTTPS', '0') == '1' or os.getenv('USE_HTPPS', '0') == '1'
    app_port = int(os.getenv('APP_PORT', '5000'))
    https_port = int(os.getenv('HTTPS_PORT', '5443'))
    local_ip = get_local_ip()
    mobile_url = f'http://{local_ip}:{app_port}'
    print('='*55)
    print('  POLLINATION MONITORING SYSTEM')
    if use_https:
        print(f'  Dashboard : http://localhost:{app_port}')
        print(f'  Report    : http://localhost:{app_port}/report')
        print(f'  Control   : http://localhost:{app_port}/control')
        print(f'  HTTPS     : https://localhost:{https_port}')
    else:
        print(f'  Dashboard : http://localhost:{app_port}')
        print(f'  Report    : http://localhost:{app_port}/report')
        print(f'  Control   : http://localhost:{app_port}/control')
    print(f'  Mobile URL: {mobile_url}')
    if use_https:
        print(f'  Optional HTTPS LAN URL: https://{local_ip}:{https_port}')
    print('='*55)
    db.init_db()  # connect to MySQL (non-fatal if .env not configured)
    # Auto-start camera only when source is camera_module
    if CONFIG.get('camera_source') == 'camera_module':
        threading.Thread(target=camera_loop, daemon=True).start()
    else:
        print('  [cam] Startup source is mobile (camera_module not auto-started).')
    if use_https:
        try:
            https_server = make_server('0.0.0.0', https_port, app, threaded=True, ssl_context='adhoc')
            threading.Thread(target=https_server.serve_forever, daemon=True).start()
            print(f'  [net] HTTPS enabled on 0.0.0.0:{https_port}')
        except (OSError, SystemExit) as e:
            print(f'  [net] HTTPS disabled (port {https_port} unavailable): {e}')
            print('  [net] Continuing with HTTP only.')
        app.run(host='0.0.0.0', port=app_port, debug=False, threaded=True)
    else:
        app.run(host='0.0.0.0', port=app_port, debug=False, threaded=True)
