import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../services/artwork.dart';
import '../services/scrobbler_api.dart';
import '../theme/app_theme.dart';

/// Artwork is fetched by album identity, never once per playback tick.
class AlbumArt extends StatefulWidget {
  const AlbumArt({
    super.key,
    required this.api,
    required this.artist,
    required this.album,
    this.url,
    this.size = 220,
    this.radius = AppRadii.small,
  });
  final ScrobblerApi api;
  final String artist, album;
  final String? url;
  final double size, radius;
  @override
  State<AlbumArt> createState() => _AlbumArtState();
}

class _AlbumArtState extends State<AlbumArt> {
  String? _url;
  int _generation = 0;
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(AlbumArt oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.artist != oldWidget.artist ||
        widget.album != oldWidget.album ||
        widget.url != oldWidget.url ||
        widget.api != oldWidget.api) {
      _load();
    }
  }

  Future<void> _load() async {
    final generation = ++_generation;
    _url = widget.url;
    if (_url != null) return;
    try {
      final url = await Artwork.url(widget.api, widget.artist, widget.album);
      if (mounted && generation == _generation) setState(() => _url = url);
    } catch (_) {
      /* Artwork is optional; listening remains usable offline. */
    }
  }

  @override
  Widget build(BuildContext context) {
    final pixels = (widget.size * MediaQuery.devicePixelRatioOf(context))
        .round();
    return ClipRRect(
      borderRadius: BorderRadius.circular(widget.radius),
      child: SizedBox.square(
        dimension: widget.size,
        child: _url == null
            ? const RecordSleeve()
            : Image.network(
                _url!,
                fit: BoxFit.cover,
                cacheWidth: pixels,
                gaplessPlayback: true,
                errorBuilder: (_, error, stack) => const RecordSleeve(),
              ),
      ),
    );
  }
}

/// Builds with an accent colour taken from the album cover, or the theme's
/// primary colour when the cover has none, fading between the two.
class ArtworkTint extends StatelessWidget {
  const ArtworkTint({
    super.key,
    required this.api,
    required this.artist,
    required this.album,
    this.url,
    required this.builder,
  });
  final ScrobblerApi api;
  final String artist, album;
  final String? url;
  final Widget Function(BuildContext context, Color tint) builder;

  @override
  Widget build(BuildContext context) => _CoverColor(
    api: api,
    artist: artist,
    album: album,
    url: url,
    builder: (context, tint) => TweenAnimationBuilder<Color?>(
      tween: ColorTween(end: tint ?? Theme.of(context).colorScheme.primary),
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOut,
      builder: (context, tint, _) => builder(context, tint!),
    ),
  );
}

/// Rebuilds the app theme around the cover colour so every accent in the
/// interface follows the album that is playing.
class ArtworkTheme extends StatelessWidget {
  const ArtworkTheme({
    super.key,
    required this.api,
    required this.artist,
    required this.album,
    this.url,
    required this.child,
  });
  final ScrobblerApi api;
  final String artist, album;
  final String? url;
  final Widget child;

  @override
  Widget build(BuildContext context) => _CoverColor(
    api: api,
    artist: artist,
    album: album,
    url: url,
    builder: (context, tint) => AnimatedTheme(
      data: AppTheme.withAccent(tint),
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeOut,
      child: child,
    ),
  );
}

/// Resolves the cover colour once per album; null while loading or when the
/// cover has no usable colour.
class _CoverColor extends StatefulWidget {
  const _CoverColor({
    required this.api,
    required this.artist,
    required this.album,
    this.url,
    required this.builder,
  });
  final ScrobblerApi api;
  final String artist, album;
  final String? url;
  final Widget Function(BuildContext context, Color? tint) builder;
  @override
  State<_CoverColor> createState() => _CoverColorState();
}

class _CoverColorState extends State<_CoverColor> {
  Color? _tint;
  int _generation = 0;
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(_CoverColor oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.artist != oldWidget.artist ||
        widget.album != oldWidget.album ||
        widget.url != oldWidget.url ||
        widget.api != oldWidget.api) {
      _load();
    }
  }

  Future<void> _load() async {
    final generation = ++_generation;
    try {
      final url =
          widget.url ??
          await Artwork.url(widget.api, widget.artist, widget.album);
      final tint = url == null ? null : await Artwork.tint(url);
      if (mounted && generation == _generation) setState(() => _tint = tint);
    } catch (_) {
      if (mounted && generation == _generation) setState(() => _tint = null);
    }
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _tint);
}

class RecordSleeve extends StatelessWidget {
  const RecordSleeve({super.key});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    return CustomPaint(
      painter: _RecordPainter(
        accent: theme.colorScheme.primary,
        vinyl: theme.scaffoldBackgroundColor,
        grooves: colors.outline,
      ),
    );
  }
}

class _RecordPainter extends CustomPainter {
  _RecordPainter({
    required this.accent,
    required this.vinyl,
    required this.grooves,
  });
  final Color accent, vinyl, grooves;

  @override
  void paint(Canvas canvas, Size size) {
    final bounds = Offset.zero & size;
    canvas.drawRect(
      bounds,
      Paint()
        ..shader = LinearGradient(
          colors: [
            accent,
            Color.lerp(accent, vinyl, .5)!,
            Color.lerp(accent, vinyl, .85)!,
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ).createShader(bounds),
    );
    final center = Offset(size.width * .56, size.height * .54);
    final radius = math.min(size.width, size.height) * .39;
    canvas.drawCircle(center, radius, Paint()..color = vinyl);
    for (var i = 4; i < 15; i++) {
      canvas.drawCircle(
        center,
        radius * i / 15,
        Paint()
          ..color = grooves
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1,
      );
    }
    canvas.drawCircle(center, radius * .29, Paint()..color = accent);
    canvas.drawCircle(center, radius * .06, Paint()..color = vinyl);
  }

  @override
  bool shouldRepaint(covariant _RecordPainter oldDelegate) =>
      accent != oldDelegate.accent ||
      vinyl != oldDelegate.vinyl ||
      grooves != oldDelegate.grooves;
}
