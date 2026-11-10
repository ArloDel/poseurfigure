import 'package:flutter/material.dart';

import 'app_colors.dart';

abstract final class AppTheme {
  static const display = 'BowlbyOne';
  static const body = 'Archivo';

  static OutlineInputBorder _inputBorder(Color color) => OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: color, width: 2.5),
      );

  static ThemeData dark() {
    const scheme = ColorScheme.dark(
      primary: AppColors.yellow,
      onPrimary: AppColors.line,
      secondary: AppColors.blue,
      tertiary: AppColors.violet,
      error: AppColors.red,
      surface: AppColors.ink,
      onSurface: AppColors.chalk,
      outline: AppColors.line,
    );

    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: AppColors.ink,
      fontFamily: body,
    );

    return base.copyWith(
      textTheme: base.textTheme
          .copyWith(
            displaySmall: const TextStyle(fontFamily: display, fontSize: 34, height: 1.0),
            headlineMedium: const TextStyle(fontFamily: display, fontSize: 30, height: 1.02),
            titleLarge: const TextStyle(fontFamily: display, fontSize: 19, height: 1.1),
            titleMedium: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            bodyLarge: const TextStyle(fontSize: 15, height: 1.45),
            bodyMedium: const TextStyle(fontSize: 14, height: 1.4),
            bodySmall: const TextStyle(fontSize: 13, color: AppColors.mute),
            labelLarge: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
          )
          .apply(bodyColor: AppColors.chalk, displayColor: AppColors.chalk),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: .12),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        labelStyle: const TextStyle(color: AppColors.mute),
        floatingLabelStyle: const TextStyle(color: AppColors.yellow, fontWeight: FontWeight.w700),
        hintStyle: const TextStyle(color: AppColors.mute),
        errorStyle: const TextStyle(color: AppColors.red, fontWeight: FontWeight.w600),
        border: _inputBorder(AppColors.line),
        enabledBorder: _inputBorder(AppColors.line),
        focusedBorder: _inputBorder(AppColors.yellow),
        errorBorder: _inputBorder(AppColors.red),
        focusedErrorBorder: _inputBorder(AppColors.red),
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: Colors.white,
        contentTextStyle: TextStyle(color: AppColors.line, fontWeight: FontWeight.w800, fontFamily: body),
      ),
    );
  }
}
