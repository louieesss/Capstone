import 'package:flutter/material.dart';

import '../models/scan_result.dart';
import 'app_theme.dart';

class ResultStyle {
  const ResultStyle._();

  static Color color(PollinationClass classification) {
    switch (classification) {
      case PollinationClass.pollinated:
        return const Color(0xFF34D399); // Green
      case PollinationClass.pollinating:
        return const Color(0xFFFBBF24); // Amber/Yellow
      case PollinationClass.notPollinated:
        return const Color(0xFFF87171); // Red
    }
  }

  static IconData icon(PollinationClass classification) {
    switch (classification) {
      case PollinationClass.pollinated:
        return Icons.verified_rounded;
      case PollinationClass.pollinating:
        return Icons.change_circle_rounded;
      case PollinationClass.notPollinated:
        return Icons.cancel_rounded;
    }
  }

  static String fieldNote(PollinationClass classification) {
    switch (classification) {
      case PollinationClass.pollinated:
        return 'White powder is visible around the coconut button, indicating successful pollination.';
      case PollinationClass.pollinating:
        return 'Lighter coconut button ends suggest the coconut is currently in the pollination stage.';
      case PollinationClass.notPollinated:
        return 'Darker coconut button ends with no signs of white powder or pollination activity.';
    }
  }
}
