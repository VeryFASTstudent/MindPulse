import 'package:flutter/material.dart';

/// Central theme definition.
///
/// Per the project brief: modern, clean, student-friendly -- NOT a
/// clinical/hospital look. That means: a soft, warm accent color instead
/// of sterile white/blue-only, rounded corners everywhere, and generous
/// whitespace rather than dense clinical-form styling.
class AppTheme {
  // A calm indigo/teal blend reads as "wellness app" without looking
  // medical -- avoids stark red/white hospital signaling entirely.
  static const Color primaryColor = Color(0xFF5B6EE8);
  static const Color secondaryColor = Color(0xFF35C4B3);
  static const Color backgroundColor = Color(0xFFF7F8FC);
  static const Color surfaceColor = Colors.white;
  static const Color textPrimary = Color(0xFF1E1F26);
  static const Color textSecondary = Color(0xFF6B6D7A);

  // Risk-level colors, used from Phase 8 onward on the status card --
  // defined here now so every screen references the same palette.
  static const Color riskLow = Color(0xFF2FBF71);
  static const Color riskMedium = Color(0xFFF5A623);
  static const Color riskHigh = Color(0xFFE85D5D);

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryColor,
        primary: primaryColor,
        secondary: secondaryColor,
        surface: surfaceColor,
      ),
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundColor,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: true,
      ),
      textTheme: const TextTheme(
        headlineMedium: TextStyle(
          fontWeight: FontWeight.bold,
          color: textPrimary,
          fontSize: 24,
        ),
        titleMedium: TextStyle(
          fontWeight: FontWeight.w600,
          color: textPrimary,
          fontSize: 16,
        ),
        bodyMedium: TextStyle(color: textSecondary, fontSize: 14),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(50),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          elevation: 0,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceColor,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        margin: EdgeInsets.zero,
      ),
    );
  }
}
