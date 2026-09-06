import 'package:flutter/material.dart';

import '../models/scan_result.dart';
import '../utils/formatters.dart';
import '../utils/result_style.dart';

class LiveResultPill extends StatelessWidget {
  const LiveResultPill({
    super.key,
    required this.prediction,
  });

  final Prediction prediction;

  @override
  Widget build(BuildContext context) {
    final color = ResultStyle.color(prediction.classification);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.58),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withOpacity(0.18)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(ResultStyle.icon(prediction.classification), color: color, size: 18),
          const SizedBox(width: 8),
          Text(
            prediction.classification.label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            Formatters.percent(prediction.confidence),
            style: const TextStyle(color: Colors.white70),
          ),
        ],
      ),
    );
  }
}
