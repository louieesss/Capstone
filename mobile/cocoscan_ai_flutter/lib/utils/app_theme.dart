import 'package:flutter/material.dart';

class AppTheme {
  const AppTheme._();

  static const Color leaf = Color(0xFF1D7A57);
  static const Color lagoon = Color(0xFF0B6E8C);
  static const Color sunlight = Color(0xFFE6A93E);
  static const Color bark = Color(0xFF6B4E3D);
  static const Color soil = Color(0xFF202A25);

  static ThemeData get light {
    final generatedScheme = ColorScheme.fromSeed(
      seedColor: leaf,
      brightness: Brightness.light,
    );
    final scheme = generatedScheme.copyWith(
      primary: leaf,
      secondary: lagoon,
      tertiary: sunlight,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: const Color(0xFFF7FAF6),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: soil,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: Colors.white,
        indicatorColor: leaf.withOpacity(0.14),
        labelTextStyle: MaterialStateProperty.resolveWith(
          (states) => TextStyle(
            fontSize: 12,
            fontWeight:
                states.contains(MaterialState.selected) ? FontWeight.w700 : null,
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: leaf,
          foregroundColor: Colors.white,
          minimumSize: const Size(56, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(56, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFDDE6DD)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFDDE6DD)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: leaf, width: 1.6),
        ),
      ),
    );
  }
}
