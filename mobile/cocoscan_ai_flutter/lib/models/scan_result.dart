import 'dart:convert';

enum PollinationClass {
  notPollinated,
  pollinated,
  pollinating,
}

extension PollinationClassX on PollinationClass {
  String get key {
    switch (this) {
      case PollinationClass.notPollinated:
        return 'not_pollinated';
      case PollinationClass.pollinated:
        return 'pollinated';
      case PollinationClass.pollinating:
        return 'pollinating';
    }
  }

  String get label {
    switch (this) {
      case PollinationClass.notPollinated:
        return 'Not Pollinating';
      case PollinationClass.pollinated:
        return 'Pollinated';
      case PollinationClass.pollinating:
        return 'Pollinating';
    }
  }

  String get displayLabel {
    switch (this) {
      case PollinationClass.notPollinated:
        return 'NOT POLLINATING';
      case PollinationClass.pollinated:
        return 'POLLINATED';
      case PollinationClass.pollinating:
        return 'POLLINATING';
    }
  }

  String get emoji {
    switch (this) {
      case PollinationClass.notPollinated:
        return '🔴';
      case PollinationClass.pollinated:
        return '🟢';
      case PollinationClass.pollinating:
        return '🟡';
    }
  }

  List<String> get visualSigns {
    switch (this) {
      case PollinationClass.pollinated:
        return [
          'White powder around the coconut button',
          'Visible powder-like coating or residue',
          'Characteristic pollination powder present',
        ];
      case PollinationClass.pollinating:
        return [
          'Lighter coconut button ends',
          'Appearance indicates active pollination stage',
          'No characteristic white powder yet visible',
        ];
      case PollinationClass.notPollinated:
        return [
          'Darker coconut button ends',
          'No visible white powder around the button',
          'No signs associated with pollination process',
        ];
    }
  }

  static PollinationClass fromKey(String key) {
    return PollinationClass.values.firstWhere(
      (value) => value.key == key,
      orElse: () => PollinationClass.notPollinated,
    );
  }
}

enum ScanSource {
  camera,
  gallery,
  liveCamera,
}

extension ScanSourceX on ScanSource {
  String get key {
    switch (this) {
      case ScanSource.camera:
        return 'camera';
      case ScanSource.gallery:
        return 'gallery';
      case ScanSource.liveCamera:
        return 'live_camera';
    }
  }

  String get label {
    switch (this) {
      case ScanSource.camera:
        return 'Camera';
      case ScanSource.gallery:
        return 'Gallery';
      case ScanSource.liveCamera:
        return 'Live Camera';
    }
  }

  static ScanSource fromKey(String key) {
    return ScanSource.values.firstWhere(
      (value) => value.key == key,
      orElse: () => ScanSource.camera,
    );
  }
}

class Prediction {
  const Prediction({
    required this.classification,
    required this.confidence,
    required this.probabilities,
    required this.usedTflite,
  });

  final PollinationClass classification;
  final double confidence;
  final Map<PollinationClass, double> probabilities;
  final bool usedTflite;

  ScanResult toScanResult({
    required String imagePath,
    required ScanSource source,
    DateTime? createdAt,
  }) {
    return ScanResult(
      imagePath: imagePath,
      classification: classification,
      confidence: confidence,
      probabilities: probabilities,
      createdAt: createdAt ?? DateTime.now(),
      source: source,
      usedTflite: usedTflite,
    );
  }
}

class ScanResult {
  const ScanResult({
    this.id,
    required this.imagePath,
    required this.classification,
    required this.confidence,
    required this.probabilities,
    required this.createdAt,
    required this.source,
    required this.usedTflite,
  });

  final int? id;
  final String imagePath;
  final PollinationClass classification;
  final double confidence;
  final Map<PollinationClass, double> probabilities;
  final DateTime createdAt;
  final ScanSource source;
  final bool usedTflite;

  ScanResult copyWith({
    int? id,
    String? imagePath,
    PollinationClass? classification,
    double? confidence,
    Map<PollinationClass, double>? probabilities,
    DateTime? createdAt,
    ScanSource? source,
    bool? usedTflite,
  }) {
    return ScanResult(
      id: id ?? this.id,
      imagePath: imagePath ?? this.imagePath,
      classification: classification ?? this.classification,
      confidence: confidence ?? this.confidence,
      probabilities: probabilities ?? this.probabilities,
      createdAt: createdAt ?? this.createdAt,
      source: source ?? this.source,
      usedTflite: usedTflite ?? this.usedTflite,
    );
  }

  Map<String, Object?> toMap() {
    return {
      'id': id,
      'image_path': imagePath,
      'result_key': classification.key,
      'result_label': classification.label,
      'confidence': confidence,
      'probabilities_json': jsonEncode(
        probabilities.map((key, value) => MapEntry(key.key, value)),
      ),
      'created_at': createdAt.toIso8601String(),
      'source': source.key,
      'used_tflite': usedTflite ? 1 : 0,
    };
  }

  factory ScanResult.fromMap(Map<String, Object?> map) {
    final probabilityMap = jsonDecode(
      map['probabilities_json'] as String,
    ) as Map<String, dynamic>;

    return ScanResult(
      id: map['id'] as int?,
      imagePath: map['image_path'] as String,
      classification: PollinationClassX.fromKey(map['result_key'] as String),
      confidence: (map['confidence'] as num).toDouble(),
      probabilities: {
        for (final cls in PollinationClass.values)
          cls: (probabilityMap[cls.key] as num?)?.toDouble() ?? 0,
      },
      createdAt: DateTime.parse(map['created_at'] as String),
      source: ScanSourceX.fromKey(map['source'] as String),
      usedTflite: ((map['used_tflite'] as int?) ?? 0) == 1,
    );
  }
}
