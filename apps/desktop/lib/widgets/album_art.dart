import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../services/scrobbler_api.dart';

/// Artwork is fetched by album identity, never once per playback tick.
class AlbumArt extends StatefulWidget {
  const AlbumArt({
    super.key,
    required this.api,
    required this.artist,
    required this.album,
    this.url,
    this.size = 220,
  });
  final ScrobblerApi api;
  final String artist, album;
  final String? url;
  final double size;
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
    if (_url != null || widget.album.isEmpty || widget.artist.isEmpty) return;
    try {
      final query = Uri(
        queryParameters: {'artist': widget.artist, 'album': widget.album},
      ).query;
      final response = await widget.api.request('GET', '/artwork/?$query');
      if (mounted && generation == _generation) {
        setState(() => _url = response['url'] as String?);
      }
    } catch (_) {
      /* Artwork is optional; listening remains usable offline. */
    }
  }

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(8),
    child: SizedBox.square(
      dimension: widget.size,
      child: _url == null
          ? const RecordSleeve()
          : Image.network(
              _url!,
              fit: BoxFit.cover,
              errorBuilder: (_, error, stack) => const RecordSleeve(),
            ),
    ),
  );
}

class RecordSleeve extends StatelessWidget {
  const RecordSleeve({super.key});
  @override
  Widget build(BuildContext context) => CustomPaint(painter: _RecordPainter());
}

class _RecordPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final bounds = Offset.zero & size;
    canvas.drawRect(
      bounds,
      Paint()
        ..shader = const LinearGradient(
          colors: [Color(0xFFC4A7FF), Color(0xFF7D63C3), Color(0xFF39304F)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ).createShader(bounds),
    );
    final center = Offset(size.width * .56, size.height * .54);
    final radius = math.min(size.width, size.height) * .39;
    canvas.drawCircle(center, radius, Paint()..color = const Color(0xFF191925));
    for (var i = 4; i < 15; i++) {
      canvas.drawCircle(
        center,
        radius * i / 15,
        Paint()
          ..color = const Color(0xFF39394B)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1,
      );
    }
    canvas.drawCircle(
      center,
      radius * .29,
      Paint()..color = const Color(0xFFD4ED83),
    );
    canvas.drawCircle(
      center,
      radius * .06,
      Paint()..color = const Color(0xFF171722),
    );
  }

  @override
  bool shouldRepaint(covariant _RecordPainter oldDelegate) => false;
}
