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
  // Neutral greys: the album cover supplies the colour, not the chrome.
  static const ink = Color(0xFF0E0E10);
  static const surface = Color(0xFF151517);
  static const surfaceRaised = Color(0xFF1D1D20);
  static const surfaceHighest = Color(0xFF27272B);
  static const outline = Color(0xFF34343A);

  static const paper = Color(0xFFF3F1EC);
  static const paperMuted = Color(0xFFB4B1AB);
  static const paperFaint = Color(0xFF8D8A85);

  /// The accent when nothing is playing or a cover has no usable colour.
  static const brand = Color(0xFFC4A7FF);

  // Status colours stay fixed so they never depend on the cover.
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
  /// Theme colours for the brand accent; used when no theme is in scope.
  static final colors = _Tones(AppPalette.brand).colors;

  static ThemeData get dark => withAccent(null);

  /// The app theme built around one accent, usually taken from the album
  /// cover. Greys pick up a faint trace of it so the whole window shifts with
  /// the music while text and status colours stay put.
  static ThemeData withAccent(Color? cover) {
    final tones = _Tones(cover ?? AppPalette.brand);
    final accent = tones.accent;

    final colorScheme = ColorScheme.dark(
      primary: accent,
      onPrimary: tones.onAccent,
      primaryContainer: tones.container,
      onPrimaryContainer: AppPalette.paper,
      secondary: tones.soft,
      onSecondary: AppPalette.ink,
      secondaryContainer: tones.container,
      onSecondaryContainer: AppPalette.paper,
      tertiary: tones.soft,
      onTertiary: AppPalette.ink,
      error: AppPalette.error,
      onError: AppPalette.ink,
      surface: tones.surface,
      onSurface: AppPalette.paper,
      onSurfaceVariant: AppPalette.paperMuted,
      surfaceContainerHighest: tones.surfaceHighest,
      outline: tones.outline,
      outlineVariant: tones.outline,
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

    final outline = BorderSide(color: tones.outline);
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: tones.ink,
      canvasColor: tones.ink,
      textTheme: textTheme,
      splashFactory: NoSplash.splashFactory,
      visualDensity: VisualDensity.compact,
      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
      extensions: [tones.colors],
      dividerTheme: DividerThemeData(
        color: tones.outline,
        thickness: 1,
        space: 1,
      ),
      cardTheme: CardThemeData(
        color: tones.surfaceRaised,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: AppRadii.largeAll,
          side: outline,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: tones.surfaceRaised,
        hintStyle: const TextStyle(color: AppPalette.paperFaint),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: outline,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: accent),
        ),
        errorBorder: const OutlineInputBorder(
          borderRadius: AppRadii.smallAll,
          borderSide: BorderSide(color: AppPalette.error),
        ),
      ),
      navigationRailTheme: NavigationRailThemeData(
        backgroundColor: tones.surface,
        indicatorColor: tones.surfaceHighest,
        selectedIconTheme: IconThemeData(color: accent),
        unselectedIconTheme: const IconThemeData(color: AppPalette.paperFaint),
        selectedLabelTextStyle: const TextStyle(
          color: AppPalette.paper,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelTextStyle: const TextStyle(
          color: AppPalette.paperFaint,
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: accent,
          foregroundColor: tones.onAccent,
          disabledBackgroundColor: tones.surfaceHighest,
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
          side: outline,
        ),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          selectedBackgroundColor: accent,
          selectedForegroundColor: tones.onAccent,
          minimumSize: const Size(0, 40),
          shape: const RoundedRectangleBorder(borderRadius: AppRadii.smallAll),
          side: outline,
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
      scrollbarTheme: ScrollbarThemeData(
        thumbColor: WidgetStatePropertyAll(tones.outline),
        thickness: const WidgetStatePropertyAll(6),
        radius: const Radius.circular(999),
      ),
      tooltipTheme: TooltipThemeData(
        decoration: BoxDecoration(
          color: tones.surfaceHighest,
          borderRadius: AppRadii.smallAll,
          border: Border.fromBorderSide(outline),
        ),
        textStyle: const TextStyle(color: AppPalette.paper, fontSize: 12),
      ),
    );
  }
}

/// Every colour the theme derives from one accent.
class _Tones {
  _Tones(this.accent)
    : onAccent =
          ThemeData.estimateBrightnessForColor(accent) == Brightness.light
          ? AppPalette.ink
          : AppPalette.paper,
      soft = _lighter(accent);

  final Color accent, onAccent, soft;

  // Just enough of the accent that the greys read as warm or cool with the
  // cover, without becoming coloured surfaces.
  Color _trace(Color grey, double amount) =>
      Color.alphaBlend(accent.withValues(alpha: amount), grey);

  Color get ink => _trace(AppPalette.ink, .025);
  Color get surface => _trace(AppPalette.surface, .03);
  Color get surfaceRaised => _trace(AppPalette.surfaceRaised, .04);
  Color get surfaceHighest => _trace(AppPalette.surfaceHighest, .05);
  Color get outline => _trace(AppPalette.outline, .08);
  Color get container => _trace(AppPalette.surfaceRaised, .2);

  ScrobblerColors get colors => ScrobblerColors(
    surfaceRaised: surfaceRaised,
    surfaceHighest: surfaceHighest,
    outline: outline,
    textMuted: AppPalette.paperMuted,
    textFaint: AppPalette.paperFaint,
    nowPlaying: accent,
    dataPrimary: accent,
    dataSecondary: soft,
    warning: AppPalette.amber,
    success: AppPalette.success,
  );

  static Color _lighter(Color color) {
    final hsl = HSLColor.fromColor(color);
    return hsl.withLightness((hsl.lightness + .1).clamp(0, .86)).toColor();
  }
}
