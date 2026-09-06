import 'dart:io';

import 'package:flutter/material.dart';

import '../app.dart';
import '../models/scan_result.dart';
import '../utils/formatters.dart';
import '../utils/result_style.dart';
import '../widgets/confidence_bar.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({
    super.key,
    required this.result,
  });

  final ScanResult result;

  bool get _isAmbiguous => result.confidence < 0.50;

  @override
  Widget build(BuildContext context) {
    final color = ResultStyle.color(result.classification);
    final probabilities = PollinationClass.values
        .map((cls) => MapEntry(cls, result.probabilities[cls] ?? 0))
        .toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    // Determine how many visual signs to show based on confidence
    final allSigns = result.classification.visualSigns;
    final confPercent = result.confidence * 100;
    final visibleSigns = confPercent > 80
        ? allSigns
        : confPercent > 60
            ? allSigns.take(2).toList()
            : allSigns.take(1).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Coconut Analysis')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
        children: [
          // ── Coconut Image ──
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: AspectRatio(
              aspectRatio: 4 / 3,
              child: Image.file(
                File(result.imagePath),
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) {
                  return Container(
                    color: color.withOpacity(0.1),
                    child: Icon(
                      Icons.image_not_supported_rounded,
                      color: color,
                      size: 42,
                    ),
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 20),

          // ── Pollination Status Card ──
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: color.withOpacity(0.3), width: 2),
              boxShadow: [
                BoxShadow(
                  color: color.withOpacity(0.08),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Text(
                  'Pollination Status',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: Colors.black54,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                ),
                const SizedBox(height: 12),
                if (_isAmbiguous) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '⚪ UNABLE TO DETERMINE',
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(
                            fontWeight: FontWeight.w900,
                            color: Colors.grey.shade600,
                          ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Unable to determine pollination status.\nPlease capture another clearer image.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.black54,
                        ),
                  ),
                ] else ...[
                  // Emoji + Status display
                  Text(
                    result.classification.emoji,
                    style: const TextStyle(fontSize: 36),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    result.classification.displayLabel,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w900,
                          color: color,
                          letterSpacing: 1.5,
                        ),
                  ),
                  const SizedBox(height: 8),
                  // Confidence
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'Confidence: ${Formatters.percent(result.confidence)}',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: color,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ── Visual Signs Detected ──
          if (!_isAmbiguous)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE0E8E0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.visibility_rounded,
                          color: color, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Visual Signs Detected',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w900,
                                ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  for (final sign in visibleSigns) ...[
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            margin: const EdgeInsets.only(top: 6),
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: color,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              sign,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(color: Colors.black87),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 4),
                  Text(
                    ResultStyle.fieldNote(result.classification),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.black45,
                          fontStyle: FontStyle.italic,
                        ),
                  ),
                ],
              ),
            ),
          const SizedBox(height: 16),

          // ── Class Probabilities ──
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE0E8E0)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Class Probabilities',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 16),
                for (final entry in probabilities) ...[
                  ConfidenceBar(
                    label: '${entry.key.emoji} ${entry.key.label}',
                    value: entry.value,
                    color: ResultStyle.color(entry.key),
                  ),
                  if (entry != probabilities.last) const SizedBox(height: 14),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),

          // ── Meta Info ──
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE0E8E0)),
            ),
            child: Column(
              children: [
                _MetaRow(
                  icon: Icons.schedule_rounded,
                  label: 'Timestamp',
                  value: Formatters.timestamp(result.createdAt),
                ),
                const Divider(height: 24),
                _MetaRow(
                  icon: Icons.source_rounded,
                  label: 'Source',
                  value: result.source.label,
                ),
                const Divider(height: 24),
                _MetaRow(
                  icon: Icons.memory_rounded,
                  label: 'Inference',
                  value: result.usedTflite ? 'TensorFlow Lite' : 'On-device',
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // ── Action Buttons ──
          FilledButton.icon(
            onPressed: () => Navigator.of(context).pushNamedAndRemoveUntil(
              AppRoutes.camera,
              (route) => route.settings.name == AppRoutes.home,
            ),
            icon: const Icon(Icons.photo_camera_rounded),
            label: const Text('Scan Another'),
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.history),
            icon: const Icon(Icons.history_rounded),
            label: const Text('Open History'),
          ),
        ],
      ),
    );
  }
}

class _MetaRow extends StatelessWidget {
  const _MetaRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: Colors.black45),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            label,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.black54,
                  fontWeight: FontWeight.w700,
                ),
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
        ),
      ],
    );
  }
}
