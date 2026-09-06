import 'package:flutter/material.dart';

import '../app.dart';
import '../models/dashboard_stats.dart';
import '../models/scan_result.dart';
import '../services/database_service.dart';
import '../utils/app_theme.dart';
import '../utils/formatters.dart';
import '../utils/result_style.dart';
import '../widgets/action_card.dart';
import '../widgets/empty_state.dart';
import '../widgets/scan_result_card.dart';
import '../widgets/stat_card.dart';

class HomeDashboardScreen extends StatefulWidget {
  const HomeDashboardScreen({super.key});

  @override
  State<HomeDashboardScreen> createState() => _HomeDashboardScreenState();
}

class _HomeDashboardScreenState extends State<HomeDashboardScreen> {
  DatabaseService? _databaseService;
  Future<DashboardStats>? _statsFuture;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final scope = AppScope.of(context);
    if (_databaseService != scope.databaseService) {
      _databaseService = scope.databaseService;
      _statsFuture = scope.databaseService.getDashboardStats();
    }
  }

  Future<void> _reload() async {
    final service = _databaseService;
    if (service == null) {
      return;
    }
    setState(() {
      _statsFuture = service.getDashboardStats();
    });
    await _statsFuture;
  }

  void _openResult(ScanResult result) {
    Navigator.of(context).pushNamed(AppRoutes.result, arguments: result);
  }

  @override
  Widget build(BuildContext context) {
    final modelLoaded = AppScope.of(context).aiService.isModelLoaded;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Profile',
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.profile),
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: FutureBuilder<DashboardStats>(
        future: _statsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final stats = snapshot.data ??
              const DashboardStats(
                totalScans: 0,
                pollinatedCount: 0,
                pollinatingCount: 0,
                notPollinatedCount: 0,
                averageConfidence: 0,
              );

          return RefreshIndicator(
            onRefresh: _reload,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
              children: [
                _Header(modelLoaded: modelLoaded),
                const SizedBox(height: 18),
                _StatsGrid(stats: stats),
                const SizedBox(height: 18),
                ActionCard(
                  title: 'Camera Scan',
                  subtitle: 'Live flower detection',
                  icon: Icons.photo_camera_rounded,
                  color: AppTheme.leaf,
                  onTap: () =>
                      Navigator.of(context).pushNamed(AppRoutes.camera).then((_) {
                    _reload();
                  }),
                ),
                const SizedBox(height: 12),
                ActionCard(
                  title: 'Gallery Scan',
                  subtitle: 'Analyze saved images',
                  icon: Icons.photo_library_rounded,
                  color: AppTheme.lagoon,
                  onTap: () =>
                      Navigator.of(context).pushNamed(AppRoutes.gallery).then((_) {
                    _reload();
                  }),
                ),
                const SizedBox(height: 12),
                ActionCard(
                  title: 'Scan History',
                  subtitle: 'Review local records',
                  icon: Icons.history_rounded,
                  color: AppTheme.bark,
                  onTap: () =>
                      Navigator.of(context).pushNamed(AppRoutes.history).then((_) {
                    _reload();
                  }),
                ),
                const SizedBox(height: 22),
                Text(
                  'Latest Scan',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 10),
                if (stats.latestScan == null)
                  EmptyState(
                    icon: Icons.eco_rounded,
                    title: 'No scans yet',
                    message: 'Camera and gallery scans will appear here.',
                    action: FilledButton.icon(
                      onPressed: () =>
                          Navigator.of(context).pushNamed(AppRoutes.camera),
                      icon: const Icon(Icons.photo_camera_rounded),
                      label: const Text('Start Scan'),
                    ),
                  )
                else
                  ScanResultCard(
                    result: stats.latestScan!,
                    onTap: () => _openResult(stats.latestScan!),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.modelLoaded});

  final bool modelLoaded;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.soil,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.local_florist_rounded, color: Colors.white),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'CocoScan AI',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Colors.white,
                        fontWeight: FontWeight.w900,
                      ),
                ),
              ),
              _ModelBadge(modelLoaded: modelLoaded),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Coconut flower pollination detection for field scans.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.white70,
                ),
          ),
        ],
      ),
    );
  }
}

class _ModelBadge extends StatelessWidget {
  const _ModelBadge({required this.modelLoaded});

  final bool modelLoaded;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: (modelLoaded ? AppTheme.leaf : AppTheme.sunlight).withOpacity(0.18),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        modelLoaded ? 'TFLite' : 'On-device',
        style: TextStyle(
          color: modelLoaded ? const Color(0xFFBFF4D5) : const Color(0xFFFFE7AD),
          fontWeight: FontWeight.w900,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _StatsGrid extends StatelessWidget {
  const _StatsGrid({
    required this.stats,
  });

  final DashboardStats stats;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      childAspectRatio: 1.35,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      children: [
        StatCard(
          label: 'Total scans',
          value: stats.totalScans.toString(),
          icon: Icons.document_scanner_rounded,
          color: AppTheme.leaf,
        ),
        StatCard(
          label: 'Avg confidence',
          value: Formatters.percent(stats.averageConfidence, digits: 0),
          icon: Icons.speed_rounded,
          color: AppTheme.lagoon,
        ),
        StatCard(
          label: PollinationClass.pollinated.label,
          value: stats.countFor(PollinationClass.pollinated).toString(),
          icon: ResultStyle.icon(PollinationClass.pollinated),
          color: ResultStyle.color(PollinationClass.pollinated),
        ),
        StatCard(
          label: PollinationClass.pollinating.label,
          value: stats.countFor(PollinationClass.pollinating).toString(),
          icon: ResultStyle.icon(PollinationClass.pollinating),
          color: ResultStyle.color(PollinationClass.pollinating),
        ),
      ],
    );
  }
}
