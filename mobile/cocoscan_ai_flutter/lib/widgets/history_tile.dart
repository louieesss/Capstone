import 'dart:io';

import 'package:flutter/material.dart';

import '../models/scan_result.dart';
import '../utils/formatters.dart';
import '../utils/result_style.dart';

class HistoryTile extends StatelessWidget {
  const HistoryTile({
    super.key,
    required this.result,
    required this.onTap,
    required this.onDelete,
  });

  final ScanResult result;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final color = ResultStyle.color(result.classification);
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFE0E8E0)),
      ),
      child: ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.file(
            File(result.imagePath),
            width: 54,
            height: 54,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) {
              return Container(
                width: 54,
                height: 54,
                color: color.withOpacity(0.12),
                child: Icon(ResultStyle.icon(result.classification), color: color),
              );
            },
          ),
        ),
        title: Text(
          result.classification.label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        subtitle: Text(
          '${Formatters.percent(result.confidence)} - ${Formatters.shortDate(result.createdAt)}',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: IconButton(
          tooltip: 'Delete scan',
          onPressed: onDelete,
          icon: const Icon(Icons.delete_outline_rounded),
        ),
      ),
    );
  }
}
