import 'scan_result.dart';

class DashboardStats {
  const DashboardStats({
    required this.totalScans,
    required this.pollinatedCount,
    required this.pollinatingCount,
    required this.notPollinatedCount,
    required this.averageConfidence,
    this.latestScan,
  });

  final int totalScans;
  final int pollinatedCount;
  final int pollinatingCount;
  final int notPollinatedCount;
  final double averageConfidence;
  final ScanResult? latestScan;

  int countFor(PollinationClass classification) {
    switch (classification) {
      case PollinationClass.pollinated:
        return pollinatedCount;
      case PollinationClass.pollinating:
        return pollinatingCount;
      case PollinationClass.notPollinated:
        return notPollinatedCount;
    }
  }
}
