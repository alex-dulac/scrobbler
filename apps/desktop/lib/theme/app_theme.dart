import 'package:flutter/material.dart';

abstract final class AppPalette {
  static const ink = Color(0xFF0D0C0B);
  static const surface = Color(0xFF161412);
  static const surfaceRaised = Color(0xFF1D1A17);
  static const surfaceHighest = Color(0xFF28231F);
  static const outline = Color(0xFF3A342E);

  static const paper = Color(0xFFF3EEE6);
  static const paperMuted = Color(0xFFA9A198);
  static const paperFaint = Color(0xFF716A63);

  static const lastFmRed = Color(0xFFD51007);
  static const lastFmRedDark = Color(0xFF480E12);
  static const seaGlass = Color(0xFF65D6CC);
  static const violet = Color(0xFF9585FF);
  static const amber = Color(0xFFF2B761);
  static const success = Color(0xFF72D39A);
  static const error = Color(0xFFFF6B6F);
}

@immutable
class ScrobblerColors extends ThemeExtension<ScrobblerColors> {
  const ScrobblerColors({
    required this.surfaceRaised,
    required this.surfaceHighest,
    required this.outline,
    required this.textMuted,
    required this.textFaint,
    required this.nowPlaying,
    required this.dataPrimary,
    required this.dataSecondary,
    required this.warning,
    required this.success,
  });

  final Color surfaceRaised;
  final Color surfaceHighest;
  final Color outline;
  final Color textMuted;
  final Color textFaint;
  final Color nowPlaying;
  final Color dataPrimary;
  final Color dataSecondary;
  final Color warning;
  final Color success;

  static ScrobblerColors of(BuildContext context) {
    return Theme.of(context).extension<ScrobblerColors>()!;
  }

  @override
  ScrobblerColors copyWith({
    Color? surfaceRaised,
    Color? surfaceHighest,
    Color? outline,
    Color? textMuted,
    Color? textFaint,
    Color? nowPlaying,
    Color? dataPrimary,
    Color? dataSecondary,
    Color? warning,
    Color? success,
  }) {
    return ScrobblerColors(
      surfaceRaised: surfaceRaised ?? this.surfaceRaised,
      surfaceHighest: surfaceHighest ?? this.surfaceHighest,
      outline: outline ?? this.outline,
      textMuted: textMuted ?? this.textMuted,
      textFaint: textFaint ?? this.textFaint,
      nowPlaying: nowPlaying ?? this.nowPlaying,
      dataPrimary: dataPrimary ?? this.dataPrimary,
      dataSecondary: dataSecondary ?? this.dataSecondary,
      warning: warning ?? this.warning,
      success: success ?? this.success,
    );
  }

  @override
  ScrobblerColors lerp(
    covariant ThemeExtension<ScrobblerColors>? other,
    double t,
  ) {
    if (other is! ScrobblerColors) {
      return this;
    }
    return ScrobblerColors(
      surfaceRaised: Color.lerp(surfaceRaised, other.surfaceRaised, t)!,
      surfaceHighest: Color.lerp(surfaceHighest, other.surfaceHighest, t)!,
      outline: Color.lerp(outline, other.outline, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      textFaint: Color.lerp(textFaint, other.textFaint, t)!,
      nowPlaying: Color.lerp(nowPlaying, other.nowPlaying, t)!,
      dataPrimary: Color.lerp(dataPrimary, other.dataPrimary, t)!,
      dataSecondary: Color.lerp(dataSecondary, other.dataSecondary, t)!,
      warning: Color.lerp(warning, other.warning, t)!,
      success: Color.lerp(success, other.success, t)!,
    );
  }
}

abstract final class AppTheme {
  static const _colors = ScrobblerColors(
    surfaceRaised: AppPalette.surfaceRaised,
    surfaceHighest: AppPalette.surfaceHighest,
    outline: AppPalette.outline,
    textMuted: AppPalette.paperMuted,
    textFaint: AppPalette.paperFaint,
    nowPlaying: AppPalette.lastFmRed,
    dataPrimary: AppPalette.seaGlass,
    dataSecondary: AppPalette.violet,
    warning: AppPalette.amber,
    success: AppPalette.success,
  );

  static ThemeData get dark {
    const colorScheme = ColorScheme.dark(
      primary: AppPalette.lastFmRed,
      onPrimary: AppPalette.paper,
      primaryContainer: AppPalette.lastFmRedDark,
      onPrimaryContainer: AppPalette.paper,
      secondary: AppPalette.seaGlass,
      onSecondary: AppPalette.ink,
      tertiary: AppPalette.violet,
      onTertiary: AppPalette.ink,
      error: AppPalette.error,
      onError: AppPalette.ink,
      surface: AppPalette.surface,
      onSurface: AppPalette.paper,
      outline: AppPalette.outline,
    );

    const textTheme = TextTheme(
      displayLarge: TextStyle(
        color: AppPalette.paper,
        fontSize: 42,
        fontWeight: FontWeight.w700,
        height: 1,
        letterSpacing: -1.6,
      ),
      displaySmall: TextStyle(
        color: AppPalette.paper,
        fontSize: 34,
        fontWeight: FontWeight.w700,
        height: 1.05,
        letterSpacing: -1.2,
      ),
      headlineLarge: TextStyle(
        color: AppPalette.paper,
        fontSize: 26,
        fontWeight: FontWeight.w700,
        height: 1.1,
        letterSpacing: -0.8,
      ),
      headlineMedium: TextStyle(
        color: AppPalette.paper,
        fontSize: 22,
        fontWeight: FontWeight.w600,
        height: 1.15,
        letterSpacing: -0.4,
      ),
      titleLarge: TextStyle(
        color: AppPalette.paper,
        fontSize: 18,
        fontWeight: FontWeight.w600,
        height: 1.2,
      ),
      titleMedium: TextStyle(
        color: AppPalette.paper,
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.25,
      ),
      bodyLarge: TextStyle(
        color: AppPalette.paper,
        fontSize: 15,
        fontWeight: FontWeight.w400,
        height: 1.5,
      ),
      bodyMedium: TextStyle(
        color: AppPalette.paperMuted,
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.45,
      ),
      labelLarge: TextStyle(
        color: AppPalette.paper,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.2,
      ),
      labelSmall: TextStyle(
        color: AppPalette.paperMuted,
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 1.4,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppPalette.ink,
      canvasColor: AppPalette.ink,
      textTheme: textTheme,
      splashFactory: NoSplash.splashFactory,
      visualDensity: VisualDensity.compact,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      extensions: const [_colors],
      dividerTheme: const DividerThemeData(
        color: AppPalette.outline,
        thickness: 1,
        space: 1,
      ),
      cardTheme: const CardThemeData(
        color: AppPalette.surfaceRaised,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(18)),
          side: BorderSide(color: AppPalette.outline),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: AppPalette.surfaceRaised,
        hintStyle: TextStyle(color: AppPalette.paperFaint),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AppPalette.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AppPalette.seaGlass),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          borderSide: BorderSide(color: AppPalette.error),
        ),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: AppPalette.surface,
        indicatorColor: AppPalette.surfaceHighest,
        selectedIconTheme: IconThemeData(color: AppPalette.lastFmRed),
        unselectedIconTheme: IconThemeData(color: AppPalette.paperFaint),
        selectedLabelTextStyle: TextStyle(
          color: AppPalette.paper,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: TextStyle(
          color: AppPalette.paperFaint,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppPalette.paper,
          foregroundColor: AppPalette.ink,
          disabledBackgroundColor: AppPalette.surfaceHighest,
          disabledForegroundColor: AppPalette.paperFaint,
          minimumSize: const Size(0, 40),
          padding: const EdgeInsets.symmetric(horizontal: 18),
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
          textStyle: textTheme.labelLarge,
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppPalette.paper,
          disabledForegroundColor: AppPalette.paperFaint,
          minimumSize: const Size.square(40),
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
        ),
      ),
      scrollbarTheme: const ScrollbarThemeData(
        thumbColor: WidgetStatePropertyAll(AppPalette.outline),
        thickness: WidgetStatePropertyAll(6),
        radius: Radius.circular(999),
      ),
      tooltipTheme: const TooltipThemeData(
        decoration: BoxDecoration(
          color: AppPalette.surfaceHighest,
          borderRadius: BorderRadius.all(Radius.circular(8)),
          border: Border.fromBorderSide(BorderSide(color: AppPalette.outline)),
        ),
        textStyle: TextStyle(color: AppPalette.paper, fontSize: 12),
      ),
    );
  }
}
