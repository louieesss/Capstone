import 'package:flutter/material.dart';

import '../app.dart';
import '../utils/app_constants.dart';
import '../utils/app_theme.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future<void>.delayed(const Duration(milliseconds: 1300), () {
      if (!mounted) {
        return;
      }
      Navigator.of(context).pushReplacementNamed(AppRoutes.home);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 96,
                  height: 96,
                  decoration: BoxDecoration(
                    color: AppTheme.leaf.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(
                    Icons.local_florist_rounded,
                    color: AppTheme.leaf,
                    size: 52,
                  ),
                ),
                const SizedBox(height: 22),
                Text(
                  AppConstants.appName,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  AppConstants.appSubtitle,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.black54,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 28),
                const SizedBox(
                  width: 34,
                  height: 34,
                  child: CircularProgressIndicator(strokeWidth: 3),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
