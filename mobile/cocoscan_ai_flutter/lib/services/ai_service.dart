import 'dart:io';
import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:tflite_flutter/tflite_flutter.dart';

import '../models/scan_result.dart';
import '../utils/app_constants.dart';
import '../utils/image_utils.dart';

class AiService {
  Interpreter? _interpreter;
  List<String> _labels = PollinationClass.values.map((e) => e.key).toList();

  bool get isModelLoaded => _interpreter != null;

  Future<void> load() async {
    await _loadLabels();
    try {
      final options = InterpreterOptions()..threads = 2;
      _interpreter = await Interpreter.fromAsset(
        AppConstants.modelAssetPath,
        options: options,
      );
      _interpreter?.allocateTensors();
    } catch (_) {
      _interpreter = null;
    }
  }

  Future<void> _loadLabels() async {
    try {
      final raw = await rootBundle.loadString(AppConstants.labelsAssetPath);
      final labels = raw
          .split(RegExp(r'\r?\n'))
          .map((line) => line.trim())
          .where((line) => line.isNotEmpty)
          .toList();
      if (labels.length >= PollinationClass.values.length) {
        _labels = labels.take(PollinationClass.values.length).toList();
      }
    } catch (_) {
      _labels = PollinationClass.values.map((e) => e.key).toList();
    }
  }

  Future<Prediction> classifyImageFile(File file) async {
    final bytes = await file.readAsBytes();
    final decoded = img.decodeImage(bytes);
    if (decoded == null) {
      throw const FormatException('Image could not be decoded.');
    }
    return _classifyDecodedImage(decoded);
  }

  Future<Prediction> classifyCameraImage(
    CameraImage cameraImage, {
    int sensorOrientation = 0,
  }) async {
    final converted = ImageUtils.cameraImageToImage(cameraImage);
    final oriented = ImageUtils.orientImage(converted, sensorOrientation);
    return _classifyDecodedImage(oriented);
  }

  Prediction _classifyDecodedImage(img.Image decoded) {
    final tflitePrediction = _runTflite(decoded);
    return tflitePrediction ?? _runVisualFallback(decoded);
  }

  Prediction? _runTflite(img.Image image) {
    final interpreter = _interpreter;
    if (interpreter == null) {
      return null;
    }

    try {
      final input = ImageUtils.imageToNormalizedInput(image);
      final output = [
        List<double>.filled(PollinationClass.values.length, 0),
      ];
      interpreter.run(input, output);
      return _predictionFromScores(output.first, usedTflite: true);
    } catch (_) {
      return null;
    }
  }

  Prediction _runVisualFallback(img.Image image) {
    final resized = ImageUtils.resizeForModel(image);
    var yellow = 0.0;
    var green = 0.0;
    var brown = 0.0;
    var dark = 0.0;
    var saturation = 0.0;
    var count = 0;

    for (var y = 0; y < resized.height; y += 2) {
      for (var x = 0; x < resized.width; x += 2) {
        final pixel = resized.getPixel(x, y);
        final r = pixel.r.toDouble() / 255.0;
        final g = pixel.g.toDouble() / 255.0;
        final b = pixel.b.toDouble() / 255.0;
        final maxChannel = math.max(r, math.max(g, b));
        final minChannel = math.min(r, math.min(g, b));
        final brightness = (r + g + b) / 3.0;
        final sat = maxChannel <= 0 ? 0 : (maxChannel - minChannel) / maxChannel;

        yellow += math.max(0, ((r + g) / 2.0 - b) * (0.4 + sat));
        green += math.max(0, g - (r + b) / 2.0);
        brown += math.max(0, (0.72 * r + 0.48 * g - 0.55 * b) * (1.08 - brightness));
        dark += 1.0 - brightness;
        saturation += sat;
        count++;
      }
    }

    if (count == 0) {
      return _predictionFromScores(const [1, 1, 1], usedTflite: false);
    }

    yellow /= count;
    green /= count;
    brown /= count;
    dark /= count;
    saturation /= count;

    final notPollinatedLogit = 0.55 + 2.7 * dark + 1.9 * brown - 0.7 * yellow;
    final pollinatedLogit = 0.70 + 3.4 * yellow + 0.8 * brown - 0.8 * green;
    final pollinatingLogit = 0.65 + 2.8 * green + 1.2 * yellow + 0.7 * saturation;

    return _predictionFromScores(
      [notPollinatedLogit, pollinatedLogit, pollinatingLogit],
      usedTflite: false,
    );
  }

  Prediction _predictionFromScores(
    List<double> scores, {
    required bool usedTflite,
  }) {
    final normalized = _normalizeScores(scores);
    final probabilities = <PollinationClass, double>{};

    for (var index = 0; index < PollinationClass.values.length; index++) {
      final label = index < _labels.length ? _labels[index] : '';
      final cls = PollinationClassX.fromKey(label);
      probabilities[cls] = normalized[index];
    }

    for (final cls in PollinationClass.values) {
      probabilities.putIfAbsent(cls, () => 0);
    }

    final sorted = probabilities.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Prediction(
      classification: sorted.first.key,
      confidence: sorted.first.value,
      probabilities: probabilities,
      usedTflite: usedTflite,
    );
  }

  List<double> _normalizeScores(List<double> scores) {
    final cleaned = scores
        .take(PollinationClass.values.length)
        .map((score) => score.isFinite ? score : 0.0)
        .toList();

    while (cleaned.length < PollinationClass.values.length) {
      cleaned.add(0);
    }

    final sum = cleaned.fold<double>(0, (total, value) => total + value);
    final alreadyProbabilities =
        cleaned.every((score) => score >= 0) && sum > 0 && sum <= 1.2;

    if (alreadyProbabilities) {
      return cleaned.map((score) => score / sum).toList();
    }

    final maxScore = cleaned.reduce(math.max);
    final expScores = cleaned.map((score) => math.exp(score - maxScore)).toList();
    final expSum = expScores.fold<double>(0, (total, value) => total + value);
    if (expSum == 0) {
      return List<double>.filled(cleaned.length, 1 / cleaned.length);
    }
    return expScores.map((score) => score / expSum).toList();
  }

  void dispose() {
    _interpreter?.close();
    _interpreter = null;
  }
}
