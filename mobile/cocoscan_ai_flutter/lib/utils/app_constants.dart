class AppConstants {
  const AppConstants._();

  static const appName = 'CocoScan AI';
  static const appSubtitle = 'Coconut Flower Pollination Detection';
  static const modelAssetPath = 'assets/models/cocoscan_model.tflite';
  static const labelsAssetPath = 'assets/models/labels.txt';
  static const modelInputSize = 224;
  static const databaseName = 'cocoscan_ai.db';
  static const scanImageFolder = 'cocoscan_scans';
}
