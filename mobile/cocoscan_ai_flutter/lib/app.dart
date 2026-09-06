import 'package:flutter/material.dart';

import 'models/scan_result.dart';
import 'screens/camera_scan_screen.dart';
import 'screens/gallery_scan_screen.dart';
import 'screens/history_screen.dart';
import 'screens/home_dashboard_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/result_screen.dart';
import 'screens/splash_screen.dart';
import 'services/ai_service.dart';
import 'services/camera_service.dart';
import 'services/database_service.dart';
import 'services/gallery_service.dart';
import 'services/profile_service.dart';
import 'utils/app_theme.dart';

class AppRoutes {
  const AppRoutes._();

  static const splash = '/';
  static const home = '/home';
  static const camera = '/camera';
  static const gallery = '/gallery';
  static const result = '/result';
  static const history = '/history';
  static const profile = '/profile';
}

class AppScope extends InheritedWidget {
  const AppScope({
    super.key,
    required this.aiService,
    required this.cameraService,
    required this.databaseService,
    required this.galleryService,
    required this.profileService,
    required super.child,
  });

  final AiService aiService;
  final CameraService cameraService;
  final DatabaseService databaseService;
  final GalleryService galleryService;
  final ProfileService profileService;

  static AppScope of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    if (scope == null) {
      throw StateError('AppScope was not found in the widget tree.');
    }
    return scope;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) {
    return false;
  }
}

class CocoScanApp extends StatelessWidget {
  const CocoScanApp({
    super.key,
    required this.aiService,
    required this.cameraService,
    required this.databaseService,
    required this.galleryService,
    required this.profileService,
  });

  final AiService aiService;
  final CameraService cameraService;
  final DatabaseService databaseService;
  final GalleryService galleryService;
  final ProfileService profileService;

  @override
  Widget build(BuildContext context) {
    return AppScope(
      aiService: aiService,
      cameraService: cameraService,
      databaseService: databaseService,
      galleryService: galleryService,
      profileService: profileService,
      child: MaterialApp(
        title: 'CocoScan AI',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        initialRoute: AppRoutes.splash,
        onGenerateRoute: _route,
      ),
    );
  }

  Route<void> _route(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.splash:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const SplashScreen(),
        );
      case AppRoutes.home:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const HomeDashboardScreen(),
        );
      case AppRoutes.camera:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const CameraScanScreen(),
        );
      case AppRoutes.gallery:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const GalleryScanScreen(),
        );
      case AppRoutes.history:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const HistoryScreen(),
        );
      case AppRoutes.profile:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const ProfileScreen(),
        );
      case AppRoutes.result:
        final result = settings.arguments as ScanResult;
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => ResultScreen(result: result),
        );
      default:
        return MaterialPageRoute(
          settings: settings,
          builder: (_) => const HomeDashboardScreen(),
        );
    }
  }
}
