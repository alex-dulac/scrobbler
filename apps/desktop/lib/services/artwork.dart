import 'dart:async';
import 'dart:collection';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/painting.dart';

import 'scrobbler_api.dart';

/// Album artwork lookups and colours, shared by every widget that shows a cover.
///
/// Lists like History show many rows from the same album, so lookups are
/// de-duplicated by album and only a few run at once against the backend.
abstract final class Artwork {
  static const _maxConcurrent = 4;
  static const _maxEntries = 256;
  static final _urls = <String, Future<String?>>{};
  static final _tints = <String, Future<Color?>>{};
  static final _waiting = Queue<Completer<void>>();
  static var _running = 0;

  static Future<String?> url(ScrobblerApi api, String artist, String album) {
    if (artist.isEmpty || album.isEmpty) return Future.value();
    final key =
        '${api.baseUrl}|${artist.trim().toLowerCase()}|${album.trim().toLowerCase()}';
    return _remember(_urls, key, () => _lookup(api, artist, album));
  }

  static Future<String?> _lookup(
    ScrobblerApi api,
    String artist,
    String album,
  ) async {
    if (_running >= _maxConcurrent) {
      final turn = Completer<void>();
      _waiting.add(turn);
      await turn.future;
    }
    _running++;
    try {
      final query = Uri(
        queryParameters: {'artist': artist, 'album': album},
      ).query;
      final response = await api.request('GET', '/artwork/?$query');
      return response['url'] as String?;
    } finally {
      _running--;
      if (_waiting.isNotEmpty) _waiting.removeFirst().complete();
    }
  }

  /// A colour from the cover that reads well as an accent on the dark theme.
  static Future<Color?> tint(String url) =>
      _remember(_tints, url, () => _extract(url));

  static Future<Color?> _extract(String url) async {
    final stream = ResizeImage(
      NetworkImage(url),
      width: 24,
      height: 24,
    ).resolve(ImageConfiguration.empty);
    final loaded = Completer<ui.Image>();
    late final ImageStreamListener listener;
    listener = ImageStreamListener(
      (info, _) {
        stream.removeListener(listener);
        loaded.complete(info.image.clone());
        info.dispose();
      },
      onError: (error, stack) {
        stream.removeListener(listener);
        loaded.completeError(error, stack);
      },
    );
    stream.addListener(listener);
    final image = await loaded.future;
    try {
      final bytes = await image.toByteData();
      return bytes == null ? null : accentFrom(bytes);
    } finally {
      image.dispose();
    }
  }

  /// Picks the most prominent saturated hue from raw RGBA pixels.
  static Color? accentFrom(ByteData rgba) {
    const buckets = 12;
    final weight = List<double>.filled(buckets, 0);
    final red = List<double>.filled(buckets, 0);
    final green = List<double>.filled(buckets, 0);
    final blue = List<double>.filled(buckets, 0);
    var pixels = 0;
    for (var i = 0; i + 3 < rgba.lengthInBytes; i += 4) {
      if (rgba.getUint8(i + 3) < 128) continue;
      pixels++;
      final color = Color.fromARGB(
        255,
        rgba.getUint8(i),
        rgba.getUint8(i + 1),
        rgba.getUint8(i + 2),
      );
      final hsv = HSVColor.fromColor(color);
      // Favour vibrant colour over dark backgrounds, near-white, and greys.
      final score = hsv.saturation * hsv.value;
      if (score <= 0) continue;
      final bucket = (hsv.hue / 360 * buckets).floor() % buckets;
      weight[bucket] += score;
      red[bucket] += color.r * score;
      green[bucket] += color.g * score;
      blue[bucket] += color.b * score;
    }
    var best = 0;
    for (var i = 1; i < buckets; i++) {
      if (weight[i] > weight[best]) best = i;
    }
    // Mostly monochrome covers fall back to the theme accent.
    if (pixels == 0 || weight[best] / pixels < .02) return null;
    final total = weight[best];
    final hsl = HSLColor.fromColor(
      Color.from(
        alpha: 1,
        red: red[best] / total,
        green: green[best] / total,
        blue: blue[best] / total,
      ),
    );
    return hsl
        .withSaturation(hsl.saturation.clamp(.35, .75))
        .withLightness(hsl.lightness.clamp(.62, .74))
        .toColor();
  }

  static Future<T> _remember<T>(
    Map<String, Future<T>> cache,
    String key,
    Future<T> Function() load,
  ) {
    final cached = cache.remove(key);
    if (cached != null) return cache[key] = cached;
    final future = load();
    cache[key] = future;
    // A failed lookup should be retried next time rather than cached.
    future.then<void>(
      (_) {},
      onError: (Object _) {
        if (identical(cache[key], future)) cache.remove(key);
      },
    );
    while (cache.length > _maxEntries) {
      cache.remove(cache.keys.first);
    }
    return future;
  }
}
