import 'dart:math' as math;

import 'package:camera/camera.dart';
import 'package:image/image.dart' as img;

import 'app_constants.dart';

class ImageUtils {
  const ImageUtils._();

  static img.Image cameraImageToImage(CameraImage cameraImage) {
    switch (cameraImage.format.group) {
      case ImageFormatGroup.yuv420:
        return _convertYuv420(cameraImage);
      case ImageFormatGroup.bgra8888:
        return _convertBgra8888(cameraImage);
      case ImageFormatGroup.jpeg:
      case ImageFormatGroup.nv21:
      case ImageFormatGroup.unknown:
        throw UnsupportedError(
          'Unsupported camera format: ${cameraImage.format.group}',
        );
    }
  }

  static img.Image orientImage(img.Image source, int degrees) {
    switch (degrees) {
      case 90:
        return img.copyRotate(source, angle: 90);
      case 180:
        return img.copyRotate(source, angle: 180);
      case 270:
        return img.copyRotate(source, angle: 270);
      default:
        return source;
    }
  }

  static img.Image resizeForModel(
    img.Image source, {
    int size = AppConstants.modelInputSize,
  }) {
    final oriented = img.bakeOrientation(source);
    return img.copyResize(
      oriented,
      width: size,
      height: size,
      interpolation: img.Interpolation.linear,
    );
  }

  static List<List<List<List<double>>>> imageToNormalizedInput(
    img.Image source, {
    int size = AppConstants.modelInputSize,
  }) {
    final resized = resizeForModel(source, size: size);

    return [
      List.generate(size, (y) {
        return List.generate(size, (x) {
          final pixel = resized.getPixel(x, y);
          final red = pixel.r.toDouble() / 255.0;
          final green = pixel.g.toDouble() / 255.0;
          final blue = pixel.b.toDouble() / 255.0;

          return [
            (red - 0.485) / 0.229,
            (green - 0.456) / 0.224,
            (blue - 0.406) / 0.225,
          ];
        });
      }),
    ];
  }

  static img.Image _convertBgra8888(CameraImage cameraImage) {
    final width = cameraImage.width;
    final height = cameraImage.height;
    final plane = cameraImage.planes.first;
    final output = img.Image(width: width, height: height);

    for (var y = 0; y < height; y++) {
      for (var x = 0; x < width; x++) {
        final offset = y * plane.bytesPerRow + x * 4;
        final blue = plane.bytes[offset];
        final green = plane.bytes[offset + 1];
        final red = plane.bytes[offset + 2];
        output.setPixelRgb(x, y, red, green, blue);
      }
    }

    return output;
  }

  static img.Image _convertYuv420(CameraImage cameraImage) {
    final width = cameraImage.width;
    final height = cameraImage.height;
    final yPlane = cameraImage.planes[0];
    final uPlane = cameraImage.planes[1];
    final vPlane = cameraImage.planes[2];
    final output = img.Image(width: width, height: height);
    final uvPixelStride = uPlane.bytesPerPixel ?? 1;

    for (var y = 0; y < height; y++) {
      final yRow = y * yPlane.bytesPerRow;
      final uvRow = (y ~/ 2) * uPlane.bytesPerRow;

      for (var x = 0; x < width; x++) {
        final yValue = yPlane.bytes[yRow + x];
        final uvIndex = uvRow + (x ~/ 2) * uvPixelStride;
        final uValue = uPlane.bytes[uvIndex] - 128;
        final vValue = vPlane.bytes[uvIndex] - 128;

        final red = (yValue + 1.402 * vValue).round();
        final green = (yValue - 0.344136 * uValue - 0.714136 * vValue).round();
        final blue = (yValue + 1.772 * uValue).round();

        output.setPixelRgb(
          x,
          y,
          red.clamp(0, 255).toInt(),
          green.clamp(0, 255).toInt(),
          blue.clamp(0, 255).toInt(),
        );
      }
    }

    return output;
  }

  static double sigmoid(double value) {
    return 1 / (1 + math.exp(-value));
  }
}
