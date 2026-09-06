import 'dart:io';

import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

class GalleryService {
  GalleryService({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  Future<File?> pickImage() async {
    await Permission.photos.request();
    final picked = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 94,
      maxWidth: 1800,
    );
    if (picked == null) {
      return null;
    }
    return File(picked.path);
  }
}
