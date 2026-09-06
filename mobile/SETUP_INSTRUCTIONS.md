# Setup Instructions for React Native Mobile App

## Before You Start

Your **Flutter app has been permanently deleted**. This React Native Expo app is in its place.

## Quick Start

### 1. Install Node.js
Download from https://nodejs.org/ (LTS version recommended)

### 2. Install Dependencies
```bash
cd mobile/react_native_app
npm install
```

### 3. Configure Python Backend Connection
Edit `src/services/api.js` and update:
```javascript
const API_BASE_URL = 'http://YOUR_IP:5000';  // Your Python Flask server
```

### 4. Start the Development Server
```bash
npm start
```

You'll see terminal options:
- Press `a` for Android emulator
- Press `i` for iOS simulator  
- Press `w` for web browser
- Scan QR code with Expo Go app on physical device

## Project Features

### Dashboard Screen
- Live camera feed from Python backend
- Real-time classification results
- Confidence bars for all three classes
- Session detection counters
- Recent detections list

### Report Screen
- Detection statistics summary
- Full detection history table
- Snapshot gallery
- Tab-based navigation

### Control Screen
- Camera on/off toggle
- Configuration settings adjustment
- Take snapshot action
- System information display

## API Endpoints Required

Your Python Flask app must expose:
```
GET  /video_feed           → MJPEG stream
GET  /api/state            → Current classification
GET  /api/history?limit=50 → Detection history
GET  /api/snapshots        → Snapshot list
GET  /api/config           → Current config
POST /api/config           → Update config
POST /api/camera           → Toggle camera
POST /api/snapshot         → Capture snapshot
```

## Design System

The app uses the **exact same design** as your web app:
- Dark theme (#070C14 background)
- Cyan primary color (#00C2FF)
- Status colors: Green, Blue, Red
- Same typography and spacing

All theme values are in `src/styles/theme.js`

## Testing Without Python Backend

The app includes mock data in `src/utils/constants.js` for testing UI without a running Python server.

## Building for Distribution

### Android APK:
```bash
eas build --platform android
```

### iOS App:
```bash
eas build --platform ios
```

### Web:
```bash
expo export --platform web
```

## Troubleshooting

**App won't connect to Python server:**
- Ensure Python Flask app is running on correct IP/port
- Check firewall settings
- Update API_BASE_URL in `src/services/api.js`

**npm install fails:**
- Delete `node_modules` folder: `rm -r node_modules`
- Delete `package-lock.json`
- Run `npm install` again

**Dependencies missing:**
- Run `npm install` again
- Clear npm cache: `npm cache clean --force`

## File Structure

```
react_native_app/
├── App.js                    # Main app component with navigation
├── package.json              # Dependencies
├── app.json                  # Expo configuration
├── README.md                 # Full documentation
├── src/
│   ├── screens/             # Three main screens
│   │   ├── DashboardScreen.js
│   │   ├── ReportScreen.js
│   │   └── ControlScreen.js
│   ├── components/          # Reusable UI components
│   │   ├── ClassificationCard.js
│   │   ├── SessionCounters.js
│   │   └── ConfidenceBar.js
│   ├── services/
│   │   └── api.js           # API integration
│   ├── styles/
│   │   └── theme.js         # Color & spacing constants
│   └── utils/
│       └── constants.js      # Mock data for testing
└── assets/                   # Images & icons
```

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure Python Flask backend IP
3. ✅ Start Expo dev server (`npm start`)
4. ✅ Open on device/emulator
5. ✅ Test dashboard, report, and control screens
6. ✅ Build for production when ready

---

**Note**: This is a "legacy" approach using Expo for rapid mobile development. The app communicates with your Python backend for inference and data.
