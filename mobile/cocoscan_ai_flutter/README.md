# CocoScan AI

CocoScan AI is a Flutter mobile app for coconut flower pollination detection. It supports live camera scanning, gallery image scanning, local SQLite scan history, a local profile, TensorFlow Lite inference, and an on-device fallback classifier.

## Folder Structure

```text
cocoscan_ai_flutter/
  pubspec.yaml
  analysis_options.yaml
  android/
    app/
      build.gradle
      proguard-rules.pro
      src/main/
        AndroidManifest.xml
        kotlin/com/cocoscan/ai/MainActivity.kt
        res/drawable/launch_background.xml
        res/values/styles.xml
        res/values-night/styles.xml
    build.gradle
    gradle.properties
    settings.gradle
  assets/
    models/
      cocoscan_model.tflite
      labels.txt
  lib/
    main.dart
    app.dart
    models/
      dashboard_stats.dart
      scan_result.dart
      user_profile.dart
    screens/
      camera_scan_screen.dart
      gallery_scan_screen.dart
      history_screen.dart
      home_dashboard_screen.dart
      profile_screen.dart
      result_screen.dart
      splash_screen.dart
    services/
      ai_service.dart
      camera_service.dart
      database_service.dart
      gallery_service.dart
      profile_service.dart
    utils/
      app_constants.dart
      app_theme.dart
      formatters.dart
      image_utils.dart
      result_style.dart
    widgets/
      action_card.dart
      confidence_bar.dart
      empty_state.dart
      history_tile.dart
      live_result_pill.dart
      scan_result_card.dart
      stat_card.dart
```

## Run

```bash
cd mobile/cocoscan_ai_flutter
flutter pub get
flutter run
```

## Model

The bundled `assets/models/cocoscan_model.tflite` is a minimal TensorFlow Lite starter graph that keeps the interpreter path active. For production accuracy, export the trained coconut pollination model to TensorFlow Lite with the same label order in `assets/models/labels.txt`:

```text
not_pollinated
pollinated
pollinating
```

The app preprocesses images as 224x224 RGB float tensors using ImageNet normalization.

## Firebase

Firebase is not included in this runnable build because Android and iOS Firebase config files are project-specific. Add `firebase_core`, `firebase_auth`, `cloud_firestore`, and generated Firebase options only after creating a Firebase project.
