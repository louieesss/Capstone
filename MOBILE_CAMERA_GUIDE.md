# 📱 Mobile Camera Integration Guide

Your pollination monitoring system now supports both **Camera Module** and **Mobile Camera** sources!

## Features

✅ Switch between camera module and mobile phone camera  
✅ Real-time classification from either source  
✅ Automatic snapshot capture  
✅ Full sensor integration (temp, humidity, light)  
✅ Database logging for all detections  

---

## How to Use Mobile Camera

### Step 1: Access the Dashboard
- For iPhone live camera, start server in HTTPS mode and open `https://192.168.1.36:5000` (replace with your Pi IP)
- You'll see the **Live Feed** section with camera controls

Start command (on Raspberry Pi):
```bash
USE_HTTPS=1 /home/root1/Documents/Capstone/.venv/bin/python app.py
```

### Step 2: Select Camera Source

**Option A: Via Dashboard (Recommended)**
1. Look at the **Live Feed** area
2. You'll see two radio buttons:
   - 📷 **Module** - Uses the Pi camera module (default)
   - 📱 **Mobile** - Uses your phone's camera
3. Click on **📱 Mobile**
4. Click **▶ Start** button that appears
5. Your phone will ask for camera permission - **Allow it**
6. The live feed will now show your phone's camera
7. If iPhone blocks live camera on HTTP, use **Capture Photo** button as fallback

**Option B: Via Control Panel**
1. Go to `http://192.168.1.36:5000/control`
2. In **Camera Control** section, select camera source
3. The camera ID field will hide when mobile is selected
4. Click **📷 Start** button

### Step 3: Monitor Live Classification

Once mobile camera is active:
- Real-time classification appears below the feed
- Confidence score and probability bars update live
- Snapshots auto-save when class is stable
- Detection history updates on the right panel

### Step 4: Switch Back to Camera Module

1. Click the **📷 Module** radio button in the live feed
2. Mobile camera stops automatically
3. Camera module feed resumes

---

## Technical Details

### What Happens When You Use Mobile Camera?

```
Your Phone (Browser)
    ↓
    Captures video frames via getUserMedia API
    ↓
    Converts to JPEG every 100ms
    ↓
Sends frames to /api/camera/mobile_frame
    ↓
Server (Flask Backend)
    ↓
    Decodes frame
    ↓
    Runs AI model inference
    ↓
    Updates real-time display
    ↓
    Detects stable classifications
    ↓
    Saves snapshots & logs to database
```

### Frame Sending Details

- **Frequency**: ~10 frames per second (100ms interval)
- **Format**: JPEG at 85% quality
- **Size**: Automatically scales to phone's video resolution
- **Network**: Uses your local/LAN connection

---

## Browser Compatibility

| Browser | Support | Platform |
|---------|---------|----------|
| Chrome/Chromium | ✅ Full | Android, iOS |
| Firefox | ✅ Full | Android, iOS |
| Safari | ⚠️ Limited | iOS 14.5+ |
| Edge | ✅ Full | Android, Windows |

**Note**: iOS 14.5+: Safari requires HTTPS for live camera access on non-localhost

---

## Requirements

- Modern smartphone with camera
- Same WiFi network as your Raspberry Pi
- HTTPS if accessing remotely on iOS
- Compatible browser with getUserMedia support

---

## Troubleshooting

### Camera Permission Denied
**Problem**: Phone shows "Permission Denied" when selecting mobile camera
**Solution**:
1. Check browser settings → Camera permissions
2. Allow camera for your site
3. Reload the page
4. Try again

### No Frames Being Sent
**Problem**: Mobile camera selected but no image appears
**Solution**:
1. Check browser console (F12) for errors
2. Ensure phone is on same network as Pi
3. Try refreshing the page
4. Close and reopen the mobile camera

### Poor Video Quality
**Problem**: Blurry or laggy video feed
**Solution**:
- Check network connection (same WiFi)
- Reduce phone camera resolution if needed
- Decrease JPEG quality in settings (⚙️ Control panel → JPEG Quality slider)
- Move closer to WiFi router

### High CPU Usage on Server
**Problem**: Server CPU spikes when using mobile camera
**Solution**:
1. Increase "Inference Every N Frames" in Control panel
2. Reduce "Stable Frames Before Snapshot" setting
3. Disable real-time polling if not needed

---

## Camera Source Settings

### Control Panel Settings (⚙️ /control)

**Camera Source** (New)
- Select between **Camera Module** and **Mobile**

**Camera ID** (Hidden when Mobile is selected)
- 0 = default camera module
- 1/2 = other connected cameras (RPi only)

**Inference Every N Frames**
- Lower = faster updates, more CPU usage
- Higher = slower updates, less CPU usage

**JPEG Quality**
- Higher = better image quality, more network bandwidth
- Lower = smaller file size, less bandwidth

---

## API Endpoints

### New Endpoints for Mobile Camera

**Set Camera Source**
```
POST /api/camera/set_source
Body: {"source": "mobile" | "camera_module"}
```

**Receive Mobile Frame**
```
POST /api/camera/mobile_frame
Form Data: image=<JPEG file>
Returns: {"status": "ok", "label": "...", "confidence": "..."}
```

---

## Performance Tips

1. **For Mobile Camera**:
   - Position phone for optimal flower visibility
   - Ensure good lighting
   - Keep phone steady (tripod recommended)
   - Use WiFi 5GHz if available

2. **For Camera Module**:
   - Use when you need consistent, unattended monitoring
   - Better for long-term observations
   - No phone battery drain

3. **Hybrid Usage**:
   - Use mobile camera for field inspection
   - Switch to module for baseline monitoring
   - Both sources log to same database

---

## Database Integration

**Both camera sources**:
- Log all classifications to Supabase
- Include sensor data (temperature, humidity, light)
- Store snapshot references
- Maintain consistent history

Log format:
```
{
  label: "pollinating" | "pollinated" | "not_pollinated",
  confidence: 0.95,
  probabilities: {...},
  timestamp: "2026-04-01 14:30:45",
  snapshot: "pollinating_95pct_20260401_143045.jpg",
  camera_source: "mobile" | "camera_module"
}
```

---

## Example Workflows

### Scenario 1: Daytime Field Inspection
1. Take phone to flower bed
2. Switch to mobile camera in dashboard
3. Point at different flowers
4. Real-time classification shows pollination status
5. Snapshots auto-save for later analysis

### Scenario 2: Continuous Monitoring
1. Camera module stays on 24/7
2. Automatic snapshots every detection
3. Data accumulates in database
4. Use control panel to adjust thresholds

### Scenario 3: Comparison Study
1. Classify same flower with both sources
2. Compare classification consistency
3. Adjust model if needed
4. Export both as snapshots

---

## Notes

- Only one camera source can be active at a time
- Switching sources stops the current one automatically
- All frames are processed identically regardless of source
- Real-time statistics apply to both sources
- Session history persists across source switches

Enjoy your enhanced mobile pollination monitoring! 🐝🌸
