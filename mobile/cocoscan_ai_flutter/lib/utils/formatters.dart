import 'package:intl/intl.dart';

class Formatters {
  const Formatters._();

  static String percent(double value, {int digits = 1}) {
    final clamped = (value * 100).clamp(0, 100);
    return '${clamped.toStringAsFixed(digits)}%';
  }

  static String shortDate(DateTime value) {
    return DateFormat('MMM d, yyyy').format(value);
  }

  static String time(DateTime value) {
    return DateFormat('h:mm a').format(value);
  }

  static String timestamp(DateTime value) {
    return DateFormat('MMM d, yyyy  h:mm a').format(value);
  }
}
