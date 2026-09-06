import 'dart:io';

import 'package:flutter/material.dart';

import '../app.dart';
import '../models/scan_result.dart';
import '../services/ai_service.dart';
import '../services/database_service.dart';
import '../services/gallery_service.dart';
import '../utils/app_theme.dart';
import '../widgets/empty_state.dart';

class GalleryScanScreen extends StatefulWidget {
  const GalleryScanScreen({super.key});

  @override
  State<GalleryScanScreen> createState() => _GalleryScanScreenState();
}

class _GalleryScanScreenState extends State<GalleryScanScreen> {
  AiService? _aiService;
  DatabaseService? _databaseService;
  GalleryService? _galleryService;
  File? _selectedImage;
  bool _busy = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final scope = AppScope.of(context);
    _aiService = scope.aiService;
    _databaseService = scope.databaseService;
    _galleryService = scope.galleryService;
  }

  Future<void> _pickAndScan() async {
    final aiService = _aiService;
    final databaseService = _databaseService;
    final galleryService = _galleryService;
    if (aiService == null ||
        databaseService == null ||
        galleryService == null ||
        _busy) {
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final image = await galleryService.pickImage();
      if (image == null) {
        if (mounted) {
          setState(() => _busy = false);
        }
        return;
      }

      if (mounted) {
        setState(() => _selectedImage = image);
      }

      final prediction = await aiService.classifyImageFile(image);
      final storedImage = await databaseService.persistImage(
        image,
        scanSource: ScanSource.gallery,
      );
      final result = await databaseService.insertScan(
        prediction.toScanResult(
          imagePath: storedImage,
          source: ScanSource.gallery,
        ),
      );

      if (!mounted) {
        return;
      }
      Navigator.of(context).pushReplacementNamed(
        AppRoutes.result,
        arguments: result,
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.toString();
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Gallery Scan')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: _selectedImage == null
              ? EmptyState(
                  icon: Icons.photo_library_rounded,
                  title: 'Select flower image',
                  message: 'Saved scan results are stored locally.',
                  action: FilledButton.icon(
                    onPressed: _busy ? null : _pickAndScan,
                    icon: const Icon(Icons.add_photo_alternate_rounded),
                    label: const Text('Choose Image'),
                  ),
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.file(
                          _selectedImage!,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) {
                            return Container(
                              color: AppTheme.leaf.withOpacity(0.1),
                              child: const Icon(Icons.broken_image_rounded),
                            );
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (_busy)
                      const LinearProgressIndicator(minHeight: 6)
                    else
                      FilledButton.icon(
                        onPressed: _pickAndScan,
                        icon: const Icon(Icons.add_photo_alternate_rounded),
                        label: const Text('Choose Another'),
                      ),
                    if (_error != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        _error!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
        ),
      ),
    );
  }
}
