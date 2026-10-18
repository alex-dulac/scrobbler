import 'package:flutter/material.dart';

abstract final class AppFonts {
  static const display = 'Space Grotesk';
  static const mono = 'JetBrains Mono';
  static const tabular = [FontFeature.tabularFigures()];

  /// Counts, durations, and timestamps share a fixed-width face so they align.
  static TextStyle? numeric(TextStyle? base) => base?.copyWith(
    fontFamily: mono,
    fontSize: base.fontSize == null ? null : base.fontSize! - 1,
    fontFeatures: tabular,
  );
}

/// Two radii: [small] for controls, bars, and thumbnails; [large] for panels.
abstract final class AppRadii {
  static const small = 6.0;
  static const large = 14.0;
  static const smallAll = BorderRadius.all(Radius.circular(small));
  static const largeAll = BorderRadius.all(Radius.circular(large));
}

abstract final class AppSpacing {
  static const page = EdgeInsets.fromLTRB(32, 8, 32, 32);
}

abstract final class AppPalette {
  static const ink = Color(0xFF101019);
  static const surface = Color(0xFF171722);
  static const surfaceRaised = Color(0xFF20202E);
  static const surfaceHighest = Color(0xFF2B2B3C);
  static const outline = Color(0xFF39394B);

  static const paper = Color(0xFFF5F3FF);
  static const paperMuted = Color(0xFFB9B6CB);
  static const paperFaint = Color(0xFF918CA8);

  static const lilac = Color(0xFFC4A7FF);
  static const plum = Color(0xFF39304F);
  static const lime = Color(0xFFD4ED83);
  static const peach = Color(0xFFFFAD92);
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
    return Theme.of(context).extension<ScrobblerColors>() ?? AppTheme.colors;
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
  static const colors = ScrobblerColors(
    surfaceRaised: AppPalette.surfaceRaised,
    surfaceHighest: AppPalette.surfaceHighest,
    outline: AppPalette.outline,
    textMuted: AppPalette.paperMuted,
    textFaint: AppPalette.paperFaint,
    nowPlaying: AppPalette.lilac,
    dataPrimary: AppPalette.lime,
    dataSecondary: AppPalette.peach,
    warning: AppPalette.amber,
    success: AppPalette.success,
  );

  static ThemeData get dark {
    const colorScheme = ColorScheme.dark(
      primary: AppPalette.lilac,
      onPrimary: AppPalette.ink,
      primaryContainer: AppPalette.plum,
      onPrimaryContainer: AppPalette.paper,
      secondary: AppPalette.lime,
      onSecondary: AppPalette.ink,
      tertiary: AppPalette.peach,
      onTertiary: AppPalette.ink,
      error: AppPalette.error,
      onError: AppPalette.ink,
      surface: AppPalette.surface,
      onSurface: AppPalette.paper,
      outline: AppPalette.outline,
    );

    const textTheme = TextTheme(
      displayLarge: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 42,
        fontWeight: FontWeight.w700,
        height: 1,
        letterSpacing: -1.6,
      ),
      displaySmall: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 34,
        fontWeight: FontWeight.w700,
        height: 1.05,
        letterSpacing: -1.2,
      ),
      headlineLarge: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 26,
        fontWeight: FontWeight.w700,
        height: 1.1,
        letterSpacing: -0.8,
      ),
      headlineMedium: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 22,
        fontWeight: FontWeight.w600,
        height: 1.15,
        letterSpacing: -0.4,
      ),
      titleLarge: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 18,
        fontWeight: FontWeight.w600,
        height: 1.2,
      ),
      titleMedium: TextStyle(
        fontFamily: AppFonts.display,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.25,
      ),
      bodyLarge: TextStyle(
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 15,
        fontWeight: FontWeight.w400,
        height: 1.5,
      ),
      bodyMedium: TextStyle(
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paperMuted,
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.45,
      ),
      labelLarge: TextStyle(
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paper,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.2,
      ),
      labelSmall: TextStyle(
        fontFamily: AppFonts.mono,
        fontFeatures: AppFonts.tabular,
        color: AppPalette.paperMuted,
        fontSize: 10,
        fontWeight: FontWeight.w500,
        letterSpacing: 1.2,
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
      extensions: const [colors],
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
          borderRadius: AppRadii.largeAll,
          side: BorderSide(color: AppPalette.outline),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: AppPalette.surfaceRaised,
        hintStyle: TextStyle(color: AppPalette.paperFaint),
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppPalette.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppPalette.lime),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppPalette.error),
        ),
      ),
      navigationRailTheme: const NavigationRailThemeData(
        backgroundColor: AppPalette.surface,
        indicatorColor: AppPalette.surfaceHighest,
        selectedIconTheme: IconThemeData(color: AppPalette.lilac),
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
          backgroundColor: AppPalette.lilac,
          foregroundColor: AppPalette.ink,
          disabledBackgroundColor: AppPalette.surfaceHighest,
          disabledForegroundColor: AppPalette.paperFaint,
          minimumSize: const Size(0, 40),
          padding: const EdgeInsets.symmetric(horizontal: 18),
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.smallAll),
          textStyle: textTheme.labelLarge,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(0, 40),
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.smallAll),
          side: const BorderSide(color: AppPalette.outline),
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          minimumSize: const Size(0, 40),
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.smallAll),
          side: const BorderSide(color: AppPalette.outline),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: AppPalette.paper,
          disabledForegroundColor: AppPalette.paperFaint,
          minimumSize: const Size.square(40),
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.smallAll),
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
          borderRadius: AppRadii.smallAll,
          border: Border.fromBorderSide(BorderSide(color: AppPalette.outline)),
        ),
        textStyle: TextStyle(color: AppPalette.paper, fontSize: 12),
      ),
    );
  }
}
