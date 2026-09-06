import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import '../models/dashboard_stats.dart';
import '../models/scan_result.dart';
import '../utils/app_constants.dart';

class DatabaseService {
  Database? _database;

  Future<void> init() async {
    if (_database != null) {
      return;
    }

    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, AppConstants.databaseName);
    _database = await openDatabase(
      path,
      version: 1,
      onCreate: _createSchema,
    );
  }

  Future<void> _createSchema(Database db, int version) async {
    await db.execute('''
      CREATE TABLE scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT NOT NULL,
        result_key TEXT NOT NULL,
        result_label TEXT NOT NULL,
        confidence REAL NOT NULL,
        probabilities_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        source TEXT NOT NULL,
        used_tflite INTEGER NOT NULL DEFAULT 0
      )
    ''');

    await db.execute(
      'CREATE INDEX idx_scan_history_created_at ON scan_history(created_at)',
    );
    await db.execute(
      'CREATE INDEX idx_scan_history_result_key ON scan_history(result_key)',
    );
  }

  Database get _db {
    final db = _database;
    if (db == null) {
      throw StateError('DatabaseService.init must be called before use.');
    }
    return db;
  }

  Future<String> persistImage(
    File source, {
    required ScanSource scanSource,
  }) async {
    final docs = await getApplicationDocumentsDirectory();
    final folder = Directory(p.join(docs.path, AppConstants.scanImageFolder));
    if (!await folder.exists()) {
      await folder.create(recursive: true);
    }

    final extension = p.extension(source.path).isEmpty
        ? '.jpg'
        : p.extension(source.path).toLowerCase();
    final fileName =
        '${DateTime.now().millisecondsSinceEpoch}_${scanSource.key}$extension';
    final targetPath = p.join(folder.path, fileName);
    final copied = await source.copy(targetPath);
    return copied.path;
  }

  Future<ScanResult> insertScan(ScanResult result) async {
    final data = result.toMap()..remove('id');
    final id = await _db.insert(
      'scan_history',
      data,
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    return result.copyWith(id: id);
  }

  Future<List<ScanResult>> getScans({int limit = 100}) async {
    final rows = await _db.query(
      'scan_history',
      orderBy: 'created_at DESC',
      limit: limit,
    );
    return rows.map(ScanResult.fromMap).toList();
  }

  Future<ScanResult?> getScanById(int id) async {
    final rows = await _db.query(
      'scan_history',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (rows.isEmpty) {
      return null;
    }
    return ScanResult.fromMap(rows.first);
  }

  Future<DashboardStats> getDashboardStats() async {
    final totalRows = await _db.rawQuery('SELECT COUNT(*) FROM scan_history');
    final total = Sqflite.firstIntValue(totalRows) ?? 0;

    final countRows = await _db.rawQuery('''
      SELECT result_key, COUNT(*) AS count
      FROM scan_history
      GROUP BY result_key
    ''');
    final counts = {
      for (final row in countRows) row['result_key'] as String: row['count'] as int,
    };

    final avgRows = await _db.rawQuery(
      'SELECT AVG(confidence) AS average_confidence FROM scan_history',
    );
    final averageConfidence =
        (avgRows.first['average_confidence'] as num?)?.toDouble() ?? 0;

    final latestRows = await _db.query(
      'scan_history',
      orderBy: 'created_at DESC',
      limit: 1,
    );

    return DashboardStats(
      totalScans: total,
      pollinatedCount: counts[PollinationClass.pollinated.key] ?? 0,
      pollinatingCount: counts[PollinationClass.pollinating.key] ?? 0,
      notPollinatedCount: counts[PollinationClass.notPollinated.key] ?? 0,
      averageConfidence: averageConfidence,
      latestScan:
          latestRows.isEmpty ? null : ScanResult.fromMap(latestRows.first),
    );
  }

  Future<void> deleteScan(int id) async {
    final scan = await getScanById(id);
    await _db.delete('scan_history', where: 'id = ?', whereArgs: [id]);
    if (scan != null) {
      final image = File(scan.imagePath);
      if (await image.exists()) {
        await image.delete();
      }
    }
  }

  Future<void> clearHistory() async {
    final scans = await getScans(limit: 100000);
    await _db.delete('scan_history');
    for (final scan in scans) {
      final image = File(scan.imagePath);
      if (await image.exists()) {
        await image.delete();
      }
    }
  }

  Future<void> close() async {
    await _database?.close();
    _database = null;
  }
}
