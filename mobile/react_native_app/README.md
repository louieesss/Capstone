# React Native Pollination Monitoring Mobile App

A React Native (Expo) mobile application that converts your Python Flask web app into a mobile-friendly experience. Built with the same design system as your web application.

## Features

- **Dashboard**: Real-time camera feed and live classification with confidence scores
- **Report**: Detection history table and snapshot gallery
- **Control**: System configuration, camera settings, and model controls
- **Dark Theme**: Matches your web app's dark UI with cyan/green/blue/red colors

## Project Structure

```
react_native_app/
├── src/
│   ├── screens/          # Tab screens (Dashboard, Report, Control)
│   ├── components/       # Reusable UI components
│   ├── services/         # API service for backend communication
│   ├── styles/           # Theme and styling constants
│   └── utils/            # Helper functions
├── assets/               # Images and static files
├── App.js                # Main app entry point
├── app.json              # Expo configuration
└── package.json          # Dependencies
```

## Installation & Setup

### Prerequisites
- Node.js 16+ and npm
- Expo CLI: `npm install -g expo-cli`

### Steps

1. **Navigate to project**:
   ```bash
   cd mobile/react_native_app
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Configure API endpoint** in `src/services/api.js`:
   ```javascript
   const API_BASE_URL = 'http://YOUR_PYTHON_SERVER:5000';
   ```

4. **Start development server**:
   ```bash
   npm start
   ```

5. **Run on device/emulator**:
   - Android: Press `a` or use `npm run android`
   - iOS: Press `i` or use `npm run ios`
   - Web: Press `w` or use `npm run web`

## API Integration

The app communicates with your Python Flask backend at:
- `/api/state` - Current classification state
- `/api/history` - Detection history
- `/api/snapshots` - Snapshot list
- `/api/config` - Get/update configuration
- `/video_feed` - Stream video

**Ensure your Flask app exposes these endpoints.**

## Design System

Uses consistent theming across the app:
- **Primary**: Cyan (#00C2FF)
- **Status**: Green (Pollinating), Blue (Pollinated), Red (Not Pollinated)
- **Background**: Dark (#070C14)

All defined in `src/styles/theme.js`

## Building for Production

### Android:
```bash
eas build --platform android
```

### iOS:
```bash
eas build --platform ios
```

### Web (Static):
```bash
expo export --platform web
```

## Notes

- This is a **legacy React Native approach** using Expo
- For production, consider ejecting to bare React Native
- Chart.js support is included via `react-native-chart-kit` for future enhancements
- The app currently streams from Python backend without local model integration

## Future Enhancements

- [ ] Add TensorFlow Lite model support for on-device inference
- [ ] Implement data charts and analytics
- [ ] Add offline mode with local database
- [ ] Camera upload and cloud backup
- [ ] Push notifications for critical detections
