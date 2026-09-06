import 'dart:async';
import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../app.dart';
import '../models/scan_result.dart';
import '../services/ai_service.dart';
import '../services/camera_service.dart';
import '../services/database_service.dart';
import '../widgets/empty_state.dart';
import '../widgets/live_result_pill.dart';

class CameraScanScreen extends StatefulWidget {
  const CameraScanScreen({super.key});

  @override
  State<CameraScanScreen> createState() => _CameraScanScreenState();
}

class _CameraScanScreenState extends State<CameraScanScreen>
    with WidgetsBindingObserver {
  AiService? _aiService;
  CameraService? _cameraService;
  DatabaseService? _databaseService;
  CameraController? _controller;
  Prediction? _livePrediction;
  DateTime _lastFrameAt = DateTime.fromMillisecondsSinceEpoch(0);
  bool _started = false;
  bool _initializing = true;
  bool _processingFrame = false;
  bool _capturing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) {
      return;
    }
    final scope = AppScope.of(context);
    _aiService = scope.aiService;
    _cameraService = scope.cameraService;
    _databaseService = scope.databaseService;
    _started = true;
    unawaited(_initializeCamera());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return;
    }

    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused) {
      unawaited(controller.dispose());
    } else if (state == AppLifecycleState.resumed) {
      unawaited(_initializeCamera());
    }
  }

  Future<void> _initializeCamera() async {
    setState(() {
      _initializing = true;
      _error = null;
    });

    try {
      await _controller?.dispose();
      final controller = await _cameraService!.createController();
      if (!mounted) {
        await controller.dispose();
        return;
      }
      _controller = controller;
      setState(() {
        _initializing = false;
      });
      await _startLiveStream();
    } on CameraException catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.description ?? error.code;
        _initializing = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = error.toString();
        _initializing = false;
      });
    }
  }

  Future<void> _startLiveStream() async {
    final controller = _controller;
    if (controller == null ||
        !controller.value.isInitialized ||
        controller.value.isStreamingImages) {
      return;
    }

    await controller.startImageStream((image) {
      unawaited(_processFrame(image));
    });
  }

  Future<void> _processFrame(CameraImage image) async {
    final aiService = _aiService;
    final controller = _controller;
    if (aiService == null ||
        controller == null ||
        _processingFrame ||
        _capturing ||
        !mounted) {
      return;
    }

    final now = DateTime.now();
    if (now.difference(_lastFrameAt).inMilliseconds < 900) {
      return;
    }

    _lastFrameAt = now;
    _processingFrame = true;
    try {
      final prediction = await aiService.classifyCameraImage(
        image,
        sensorOrientation: controller.description.sensorOrientation,
      );
      if (mounted) {
        setState(() => _livePrediction = prediction);
      }
    } catch (_) {
      // Live frames are noisy and device-dependent; capture flow remains active.
    } finally {
      _processingFrame = false;
    }
  }

  Future<void> _captureAndClassify() async {
    final controller = _controller;
    final aiService = _aiService;
    final databaseService = _databaseService;
    if (controller == null ||
        aiService == null ||
        databaseService == null ||
        _capturing ||
        !controller.value.isInitialized) {
      return;
    }

    setState(() => _capturing = true);

    try {
      if (controller.value.isStreamingImages) {
        await controller.stopImageStream();
      }

      final picture = await controller.takePicture();
      final imageFile = File(picture.path);
      final prediction = await aiService.classifyImageFile(imageFile);
      final storedImage = await databaseService.persistImage(
        imageFile,
        scanSource: ScanSource.camera,
      );
      final result = await databaseService.insertScan(
        prediction.toScanResult(
          imagePath: storedImage,
          source: ScanSource.camera,
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
        _capturing = false;
      });
      await _startLiveStream();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text('Camera Scan'),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'History',
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.history),
            icon: const Icon(Icons.history_rounded),
          ),
        ],
      ),
      body: _initializing
          ? const Center(child: CircularProgressIndicator())
          : _error != null && controller == null
              ? EmptyState(
                  icon: Icons.no_photography_rounded,
                  title: 'Camera unavailable',
                  message: _error!,
                  action: FilledButton.icon(
                    onPressed: _initializeCamera,
                    icon: const Icon(Icons.refresh_rounded),
                    label: const Text('Retry'),
                  ),
                )
              : _CameraPreviewBody(
                  controller: controller,
                  livePrediction: _livePrediction,
                  error: _error,
                  capturing: _capturing,
                  onCapture: _captureAndClassify,
                ),
    );
  }
}

class _CameraPreviewBody extends StatelessWidget {
  const _CameraPreviewBody({
    required this.controller,
    required this.livePrediction,
    required this.error,
    required this.capturing,
    required this.onCapture,
  });

  final CameraController? controller;
  final Prediction? livePrediction;
  final String? error;
  final bool capturing;
  final VoidCallback onCapture;

  @override
  Widget build(BuildContext context) {
    final camera = controller;
    if (camera == null || !camera.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        Center(
          child: AspectRatio(
            aspectRatio: camera.value.aspectRatio,
            child: CameraPreview(camera),
          ),
        ),
        Positioned(
          top: 16,
          left: 16,
          right: 16,
          child: Row(
            children: [
              if (livePrediction != null) LiveResultPill(prediction: livePrediction!),
              const Spacer(),
            ],
          ),
        ),
        if (error != null)
          Positioned(
            left: 16,
            right: 16,
            bottom: 108,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.62),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                error!,
                style: const TextStyle(color: Colors.white),
              ),
            ),
          ),
        Positioned(
          left: 0,
          right: 0,
          bottom: 24,
          child: Center(
            child: SizedBox(
              width: 84,
              height: 84,
              child: FloatingActionButton(
                onPressed: capturing ? null : onCapture,
                backgroundColor: Colors.white,
                foregroundColor: Colors.black,
                child: capturing
                    ? const SizedBox(
                        width: 30,
                        height: 30,
                        child: CircularProgressIndicator(strokeWidth: 3),
                      )
                    : const Icon(Icons.camera_rounded, size: 34),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
