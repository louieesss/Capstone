import 'dart:io';

import 'package:flutter/material.dart';

import '../models/scan_result.dart';
import '../utils/formatters.dart';
import '../utils/result_style.dart';
import 'confidence_bar.dart';

class ScanResultCard extends StatelessWidget {
  const ScanResultCard({
    super.key,
    required this.result,
    this.onTap,
  });

  final ScanResult result;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = ResultStyle.color(result.classification);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: const Color(0xFFE0E8E0)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.file(
                    File(result.imagePath),
                    width: 64,
                    height: 64,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) {
                      return Container(
                        width: 64,
                        height: 64,
                        color: color.withOpacity(0.1),
                        child: Icon(Icons.image_not_supported, color: color),
                      );
                    },
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            ResultStyle.icon(result.classification),
                            color: color,
                            size: 18,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              result.classification.label,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w900),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${result.source.label} - ${Formatters.timestamp(result.createdAt)}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.black54,
                            ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            ConfidenceBar(
              label: 'Confidence',
              value: result.confidence,
              color: color,
            ),
          ],
        ),
      ),
    );
  }
}
