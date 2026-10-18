// Render the real widgets with synthetic data, without a backend.
// Run on macOS: flutter test tool/render_preview.dart
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/features/library/artist_detail_page.dart';
import 'package:py_scrobbler_desktop/screens/dashboard_screen.dart';
import 'package:py_scrobbler_desktop/services/artwork.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';
import 'package:py_scrobbler_desktop/theme/app_theme.dart';

/// Abstract sample covers, so artwork-driven colour shows without the network.
const _covers = {
  'A little after midnight': [Color(0xFF0E3B43), Color(0xFFE39B4B)],
  'Open windows': [Color(0xFF2D1B4E), Color(0xFFE2557A)],
  'Everything in between': [Color(0xFF16302B), Color(0xFF8FD694)],
};

Future<Uint8List> _cover(List<Color> colors) async {
  const size = 300.0;
  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder);
  canvas.drawRect(
    const Rect.fromLTWH(0, 0, size, size),
    Paint()..color = colors.first,
  );
  canvas.drawCircle(
    const Offset(size * .62, size * .42),
    size * .3,
    Paint()..color = colors.last,
  );
  canvas.drawRect(
    const Rect.fromLTWH(0, size * .72, size, size * .06),
    Paint()..color = colors.last.withValues(alpha: .6),
  );
  final image = await recorder.endRecording().toImage(
    size.toInt(),
    size.toInt(),
  );
  final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  return bytes!.buffer.asUint8List();
}

/// Image loads never finish inside the fake-async test zone, so resolve them
/// on real IO first; widgets then find them in the image cache.
Future<void> _warm(ImageProvider provider) {
  final done = Completer<void>();
  final stream = provider.resolve(ImageConfiguration.empty);
  late final ImageStreamListener listener;
  listener = ImageStreamListener(
    (_, _) {
      stream.removeListener(listener);
      done.complete();
    },
    onError: (error, stack) {
      stream.removeListener(listener);
      done.completeError(error, stack!);
    },
  );
  stream.addListener(listener);
  return done.future;
}

TextStyle? _previewSans(TextStyle? style) =>
    style?.fontFamily == AppFonts.display || style?.fontFamily == AppFonts.mono
    ? style
    : style?.copyWith(fontFamily: 'Preview Sans');

void main() {
  testWidgets('render listening, History, and Wrapped with sample data', (
    tester,
  ) async {
    // Covers come from a loopback server rather than the test HTTP stub.
    HttpOverrides.global = null;
    tester.view.physicalSize = const Size(1280, 1180);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.runAsync(() async {
      final font = FontLoader('Preview Sans')
        ..addFont(
          File(
            '/System/Library/Fonts/SFNS.ttf',
          ).readAsBytes().then((b) => ByteData.sublistView(b)),
        );
      await font.load();
      final icons = FontLoader('MaterialIcons')
        ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
      await icons.load();
      final display = FontLoader(AppFonts.display)
        ..addFont(rootBundle.load('assets/fonts/SpaceGrotesk-Medium.ttf'))
        ..addFont(rootBundle.load('assets/fonts/SpaceGrotesk-Bold.ttf'));
      await display.load();
      final mono = FontLoader(AppFonts.mono)
        ..addFont(rootBundle.load('assets/fonts/JetBrainsMono-Regular.ttf'))
        ..addFont(rootBundle.load('assets/fonts/JetBrainsMono-Medium.ttf'))
        ..addFont(rootBundle.load('assets/fonts/JetBrainsMono-Bold.ttf'));
      await mono.load();
    });
    final covers = <String, Uint8List>{};
    final server = (await tester.runAsync(() async {
      for (final entry in _covers.entries) {
        covers[entry.key] = await _cover(entry.value);
      }
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((request) {
        final bytes = covers[request.uri.pathSegments.last];
        request.response
          ..statusCode = bytes == null ? 404 : 200
          ..headers.contentType = ContentType('image', 'png');
        if (bytes != null) request.response.add(bytes);
        request.response.close();
      });
      for (final album in covers.keys) {
        final url =
            'http://127.0.0.1:${server.port}/cover/${Uri.encodeComponent(album)}';
        await Artwork.tint(url);
        for (final size in [36, 40, 44, 120, 156, 220]) {
          await _warm(ResizeImage(NetworkImage(url), width: size));
        }
      }
      return server;
    }))!;
    addTearDown(() => server.close(force: true));
    final artists = ['Night Swimming', 'The Satellites', 'Soft Landing'];
    final random = math.Random(7);
    final state = {
      'active_integration_id': 'apple_music',
      'scrobble_enabled': true,
      'runtime_state': 'running',
      'database_available': true,
      'user': {
        'name': 'nightlistener',
        'playcount': '48213',
        'artist_count': '2140',
        'album_count': '3982',
      },
      'current_song': {
        'name': 'Somewhere between songs',
        'artist': artists.first,
        'album': 'A little after midnight',
        'playing': true,
        'duration': 240,
        'year': 2024,
        'genre': 'Alternative',
        'track_number': 3,
        'time_played': 84,
        'scrobble_threshold': 120,
      },
      'session': {
        'pending': [
          {
            'name': 'Evening signal',
            'artist': artists[1],
            'album': 'Open windows',
          },
        ],
        'scrobbles': List.generate(
          12,
          (i) => {
            'name': [
              'Streetlights',
              'Late train',
              'Static',
              'Open windows',
            ][i % 4],
            'artist': artists[i % 3],
            'album': _covers.keys.elementAt(i % 3),
            'scrobbled_at': DateTime(2026, 10, 17, 18, i * 4).toIso8601String(),
          },
        ),
      },
    };
    final controller = ScrobblerController(
      api: ScrobblerApi(
        baseUrl: Uri.parse('http://preview.invalid'),
        token: 'sample-only',
        client: MockClient((request) async {
          Object response = {};
          if (request.url.path == '/state/') response = state;
          if (request.url.path == '/artwork/') {
            final album = request.url.queryParameters['album'] ?? '';
            response = {
              'url': _covers.containsKey(album)
                  ? 'http://127.0.0.1:${server.port}/cover/${Uri.encodeComponent(album)}'
                  : null,
            };
          }
          if (request.url.path == '/library/history/') {
            final albums = _covers.keys.toList();
            response = {
              'page': 1,
              'page_size': 40,
              'total': 8420,
              'items': List.generate(
                9,
                (i) => {
                  'track': ['Streetlights', 'Late train', 'Static'][i % 3],
                  'artist': artists[i % 3],
                  'album': albums[i ~/ 3],
                  'scrobbled_at': DateTime(
                    2026,
                    10,
                    17,
                    21,
                    40 - i * 4,
                  ).toIso8601String(),
                },
              ),
            };
          }
          if (request.url.path == '/library/context/') {
            response = {
              'track': {
                'name': 'Somewhere between songs',
                'artist': artists.first,
                'total_scrobbles': 24,
                'first_scrobbled_at': '2024-05-18T19:34:00',
                'last_scrobbled_at': '2026-09-27T20:12:00',
                'years': [
                  {'year': 2024, 'count': 7},
                  {'year': 2025, 'count': 11},
                  {'year': 2026, 'count': 6},
                ],
                'recent_scrobbles': [
                  '2026-09-27T20:12:00',
                  '2026-09-14T09:32:00',
                  '2026-08-23T18:05:00',
                  '2026-07-18T21:40:00',
                  '2026-06-06T14:18:00',
                ],
              },
              'album': {
                'name': 'A little after midnight',
                'artist': artists.first,
                'total_scrobbles': 208,
                'unique_tracks': 11,
                'years': [
                  {'year': 2024, 'count': 96},
                  {'year': 2025, 'count': 72},
                  {'year': 2026, 'count': 40},
                ],
                'first_scrobbled_at': '2024-05-18T19:26:00',
                'last_scrobbled_at': '2026-09-27T20:12:00',
                'top_tracks': [
                  {'name': 'Streetlights', 'count': 38},
                  {'name': 'Late train', 'count': 31},
                  {'name': 'Somewhere between songs', 'count': 24},
                  {'name': 'Evening signal', 'count': 22},
                  {'name': 'Static', 'count': 20},
                ],
              },
              'artist': {
                'artist': artists.first,
                'total_scrobbles': 840,
                'years': [
                  {'year': 2022, 'count': 72},
                  {'year': 2023, 'count': 146},
                  {'year': 2024, 'count': 280},
                  {'year': 2025, 'count': 214},
                  {'year': 2026, 'count': 128},
                ],
                'top_albums': [
                  {'name': 'A little after midnight', 'count': 208},
                  {'name': 'Open windows', 'count': 182},
                  {'name': 'Everything in between', 'count': 156},
                ],
                'top_tracks': [],
              },
            };
          }

          if (request.url.path == '/library/artists/') {
            final albums = _covers.keys.toList();
            final tracks = [
              'Somewhere between songs',
              'Porch light',
              'Static on the radio',
              'Late bus home',
              'Paper moons',
              'Sleeping in the car',
              'All the small hours',
              'Northbound',
              'Glass harbour',
              'Room tone',
            ];
            response = {
              'artist': request.url.queryParameters['artist'],
              'total_scrobbles': 1184,
              'rank': 3,
              'first_scrobbled_at': '2013-03-04T20:12:00',
              'last_scrobbled_at': '2026-10-15T22:40:00',
              'first_track': {
                'name': 'Late bus home',
                'album': albums[2],
                'scrobbled_at': '2013-03-04T20:12:00',
              },
              'years': [
                for (final (i, count) in [
                  41,
                  212,
                  168,
                  96,
                  30,
                  0,
                  12,
                  58,
                  141,
                  122,
                  87,
                  74,
                  66,
                  77,
                ].indexed)
                  {'year': 2013 + i, 'count': count},
              ],
              'top_albums': [
                for (final (i, count) in [512, 388, 201].indexed)
                  {'name': albums[i], 'count': count},
              ],
              'top_tracks': [
                for (final (i, name) in tracks.indexed)
                  {'name': name, 'album': albums[i % 3], 'count': 96 - i * 7},
              ],
            };
          }
          if (request.url.path == '/library/years/') {
            response = {
              'years': [2026, 2025],
            };
          }
          if (request.url.path == '/library/wrapped/2026/') {
            response = {
              'year': 2026,
              'total_scrobbles': 8420,
              'unique_artists': 326,
              'unique_albums': 612,
              'unique_tracks': 1480,
              'monthly': List.generate(
                12,
                (i) => {
                  'month': i + 1,
                  'count': [
                    430,
                    670,
                    510,
                    720,
                    810,
                    580,
                    940,
                    1050,
                    700,
                    410,
                    0,
                    0,
                  ][i],
                },
              ),
              'previous_total_scrobbles': 9120,
              'daily': [
                for (
                  var day = DateTime(2026);
                  !day.isAfter(DateTime(2026, 10, 17));
                  day = DateTime(day.year, day.month, day.day + 1)
                )
                  if (random.nextDouble() > .18)
                    {
                      'date': day.toIso8601String().substring(0, 10),
                      'count':
                          4 +
                          random.nextInt(day.weekday >= 6 ? 70 : 38) +
                          (day.month >= 7 && day.month <= 8 ? 20 : 0),
                    },
              ],
              'top_artists': [
                for (final (i, previous) in [2, 1, null].indexed)
                  {
                    'name': artists[i],
                    'count': 340 - i * 70,
                    'previous_rank': previous,
                  },
              ],
              'top_albums': [
                for (final (i, album) in _covers.keys.indexed)
                  {
                    'name': album,
                    'artist': artists[i],
                    'count': 208 - i * 26,
                    'previous_rank': [1, 4, 2][i],
                  },
              ],
              'top_tracks': [
                for (final (i, track) in [
                  'Streetlights',
                  'Late train',
                  'Static',
                ].indexed)
                  {
                    'name': track,
                    'artist': artists[0],
                    'album': _covers.keys.first,
                    'count': 38 - i * 7,
                    'previous_rank': [null, 1, 3][i],
                  },
              ],
            };
          }
          if (request.url.path == '/library/on-this-day/') {
            final albums = _covers.keys.toList();
            response = {
              'date': request.url.queryParameters['date'],
              'years': [
                for (final (i, year) in [2025, 2024, 2022].indexed)
                  {
                    'year': year,
                    'total_scrobbles': [42, 17, 9][i],
                    'top_tracks': [
                      for (var t = 0; t < 3 - i; t++)
                        {
                          'name': ['Open windows', 'Late train', 'Static'][t],
                          'artist': artists[(i + t) % 3],
                          'album': albums[(i + t) % 3],
                          'count': 6 - t * 2,
                        },
                    ],
                  },
              ],
            };
          }
          return http.Response(jsonEncode(response), 200);
        }),
      ),
    );
    await controller.refresh();
    final key = GlobalKey();
    final theme = AppTheme.dark;
    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: MaterialApp(
          debugShowCheckedModeBanner: false,
          theme: theme.copyWith(
            textTheme: theme.textTheme.copyWith(
              displayLarge: _previewSans(theme.textTheme.displayLarge),
              displayMedium: _previewSans(theme.textTheme.displayMedium),
              displaySmall: _previewSans(theme.textTheme.displaySmall),
              headlineLarge: _previewSans(theme.textTheme.headlineLarge),
              headlineMedium: _previewSans(theme.textTheme.headlineMedium),
              headlineSmall: _previewSans(theme.textTheme.headlineSmall),
              titleLarge: _previewSans(theme.textTheme.titleLarge),
              titleMedium: _previewSans(theme.textTheme.titleMedium),
              titleSmall: _previewSans(theme.textTheme.titleSmall),
              bodyLarge: _previewSans(theme.textTheme.bodyLarge),
              bodyMedium: _previewSans(theme.textTheme.bodyMedium),
              bodySmall: _previewSans(theme.textTheme.bodySmall),
              labelLarge: _previewSans(theme.textTheme.labelLarge),
              labelMedium: _previewSans(theme.textTheme.labelMedium),
              labelSmall: _previewSans(theme.textTheme.labelSmall),
            ),
          ),
          home: DashboardScreen(controller: controller),
        ),
      ),
    );
    await tester.pumpAndSettle();
    // Artwork lookups finish on the real event loop; let them land first.
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pumpAndSettle();
    Future<void> capture(String name) async {
      final boundary =
          key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 1);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await Directory('build/previews').create(recursive: true);
        await File(
          'build/previews/$name.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }

    await capture('listening');
    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();
    await capture('history');
    // The library pages run long; show them whole.
    tester.view.physicalSize = const Size(1280, 2100);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Wrapped'));
    await tester.pumpAndSettle();
    await capture('wrapped');
    await tester.tap(find.text('Overview'));
    await tester.pumpAndSettle();
    await capture('overview');
    Navigator.of(tester.element(find.byType(DashboardScreen))).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            ArtistDetailPage(api: controller.api, artist: artists.first),
      ),
    );
    await tester.pumpAndSettle();
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pumpAndSettle();
    await capture('artist');
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
}
