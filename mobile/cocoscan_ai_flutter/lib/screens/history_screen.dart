import 'package:flutter/material.dart';

import '../app.dart';
import '../models/scan_result.dart';
import '../services/database_service.dart';
import '../widgets/empty_state.dart';
import '../widgets/history_tile.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  DatabaseService? _databaseService;
  Future<List<ScanResult>>? _scansFuture;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final service = AppScope.of(context).databaseService;
    if (_databaseService != service) {
      _databaseService = service;
      _scansFuture = service.getScans();
    }
  }

  Future<void> _reload() async {
    final service = _databaseService;
    if (service == null) {
      return;
    }
    setState(() => _scansFuture = service.getScans());
    await _scansFuture;
  }

  Future<void> _deleteScan(ScanResult result) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Delete scan'),
          content: const Text('This scan record and image will be removed.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || result.id == null) {
      return;
    }
    await _databaseService?.deleteScan(result.id!);
    await _reload();
  }

  Future<void> _clearHistory() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Clear history'),
          content: const Text('All saved scan records and images will be removed.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Clear'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }
    await _databaseService?.clearHistory();
    await _reload();
  }

  void _openResult(ScanResult result) {
    Navigator.of(context).pushNamed(AppRoutes.result, arguments: result);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan History'),
        actions: [
          IconButton(
            tooltip: 'Clear history',
            onPressed: _clearHistory,
            icon: const Icon(Icons.delete_sweep_rounded),
          ),
        ],
      ),
      body: FutureBuilder<List<ScanResult>>(
        future: _scansFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final scans = snapshot.data ?? const <ScanResult>[];
          if (scans.isEmpty) {
            return EmptyState(
              icon: Icons.history_rounded,
              title: 'No history',
              message: 'Saved scans will be listed by date.',
              action: FilledButton.icon(
                onPressed: () => Navigator.of(context).pushNamed(AppRoutes.camera),
                icon: const Icon(Icons.photo_camera_rounded),
                label: const Text('Camera Scan'),
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
              itemCount: scans.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final scan = scans[index];
                return HistoryTile(
                  result: scan,
                  onTap: () => _openResult(scan),
                  onDelete: () => _deleteScan(scan),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
