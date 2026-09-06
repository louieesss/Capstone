import 'package:flutter/material.dart';

import 'app.dart';
import 'services/ai_service.dart';
import 'services/camera_service.dart';
import 'services/database_service.dart';
import 'services/gallery_service.dart';
import 'services/profile_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final databaseService = DatabaseService();
  await databaseService.init();

  final aiService = AiService();
  await aiService.load();

  final profileService = ProfileService();
  await profileService.load();

  runApp(
    CocoScanApp(
      aiService: aiService,
      cameraService: CameraService(),
      databaseService: databaseService,
      galleryService: GalleryService(),
      profileService: profileService,
    ),
  );
}
