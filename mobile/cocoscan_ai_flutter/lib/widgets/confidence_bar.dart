import 'package:flutter/material.dart';

import '../utils/formatters.dart';

class ConfidenceBar extends StatelessWidget {
  const ConfidenceBar({
    super.key,
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final clamped = value.clamp(0.0, 1.0).toDouble();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ),
            const SizedBox(width: 10),
            Text(
              Formatters.percent(clamped),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.black54,
                    fontWeight: FontWeight.w700,
                  ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: clamped,
            minHeight: 9,
            color: color,
            backgroundColor: color.withOpacity(0.14),
          ),
        ),
      ],
    );
  }
}
