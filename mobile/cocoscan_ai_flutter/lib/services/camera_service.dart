import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';

class CameraService {
  List<CameraDescription>? _cameras;

  Future<bool> ensureCameraPermission() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  Future<List<CameraDescription>> getCameras() async {
    final existing = _cameras;
    if (existing != null && existing.isNotEmpty) {
      return existing;
    }
    _cameras = await availableCameras();
    return _cameras!;
  }

  Future<CameraController> createController({
    ResolutionPreset resolutionPreset = ResolutionPreset.high,
  }) async {
    final hasPermission = await ensureCameraPermission();
    if (!hasPermission) {
      throw CameraException(
        'camera_permission_denied',
        'Camera permission was denied.',
      );
    }

    final cameras = await getCameras();
    if (cameras.isEmpty) {
      throw CameraException('camera_unavailable', 'No camera was found.');
    }

    final selected = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.back,
      orElse: () => cameras.first,
    );

    final controller = CameraController(
      selected,
      resolutionPreset,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.yuv420,
    );
    await controller.initialize();
    return controller;
  }
}
