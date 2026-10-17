// Render the real widgets with synthetic data, without a backend.
// Run on macOS: flutter test tool/render_preview.dart
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/screens/dashboard_screen.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';
import 'package:py_scrobbler_desktop/theme/app_theme.dart';

void main() {
  testWidgets('render listening and Wrapped with sample data', (tester) async {
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
    });
    final artists = ['Night Swimming', 'The Satellites', 'Soft Landing'];
    final state = {
      'active_integration_id': 'apple_music',
      'scrobble_enabled': true,
      'runtime_state': 'running',
      'database_available': true,
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
        'pending': [],
        'scrobbles': List.generate(
          12,
          (i) => {
            'name': 'Sample listen ${i + 1}',
            'artist': artists[i % 3],
            'album': 'Sample album',
            'scrobbled_at': '2026-09-28T20:00:00',
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
                    580,
                    770,
                    660,
                  ][i],
                },
              ),
              'top_artists': List.generate(
                3,
                (i) => {'name': artists[i], 'count': 340 - i * 70},
              ),
              'top_albums': [],
              'top_tracks': [],
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
            textTheme: theme.textTheme.apply(fontFamily: 'Preview Sans'),
          ),
          home: DashboardScreen(controller: controller),
        ),
      ),
    );
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
    await tester.tap(find.text('Wrapped'));
    await tester.pumpAndSettle();
    await capture('wrapped');
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
}
