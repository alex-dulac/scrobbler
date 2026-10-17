import 'dart:async';
import 'package:py_scrobbler_desktop/services/library_cache.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/features/listening/listening_context.dart';
import 'package:py_scrobbler_desktop/models/scrobbler_state.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

Map<String, dynamic> stats(int count) => {
  'track': {
    'total_scrobbles': count,
    'first_scrobbled_at': '2024-03-01T12:00:00Z',
    'last_scrobbled_at': '2026-01-01T12:00:00Z',
    'recent_scrobbles': ['2026-01-01T12:00:00Z'],
  },
  'album': {
    'total_scrobbles': 45,
    'unique_tracks': 8,
    'top_tracks': [
      {'name': 'Album favorite', 'count': 12},
    ],
  },
  'artist': {
    'total_scrobbles': 100,
    'years': [
      {'year': 2026, 'count': 50},
    ],
    'top_albums': [
      {'name': 'Older record', 'count': 30},
    ],
  },
};
http.Response response(int count) =>
    http.Response(jsonEncode(stats(count)), 200);
ScrobblerApi apiFor(Future<http.Response> Function(http.Request) callback) =>
    ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient(callback),
    );
Widget view(
  ScrobblerApi api, {
  String name = 'Song & one',
  String album = 'Record',
  int elapsed = 0,
}) => MaterialApp(
  home: Scaffold(
    body: SingleChildScrollView(
      child: ListeningContext(
        api: api,
        track: ScrobbleTrack.fromJson({
          'name': name,
          'artist': 'A / B',
          'album': album,
          'time_played': elapsed,
        }),
      ),
    ),
  ),
);

void main() {
  testWidgets('shows track album and artist history without clicking', (
    tester,
  ) async {
    final api = apiFor((request) async {
      expect(request.url.queryParameters, {
        'track': 'Song & one',
        'artist': 'A / B',
        'album': 'Record',
      });
      return response(17);
    });
    await tester.pumpWidget(view(api));
    await tester.pumpAndSettle();
    expect(find.text('17'), findsOneWidget);
    expect(find.text('Album favorite'), findsOneWidget);
    expect(find.text('Older record'), findsOneWidget);
    expect(find.text('2026'), findsOneWidget);
    expect(find.text('First heard'), findsNWidgets(2));
    expect(tester.takeException(), isNull);
    api.close();
  });
  testWidgets('playback ticks reuse data and library invalidation refreshes', (
    tester,
  ) async {
    var calls = 0;
    final api = apiFor((request) async => response(++calls));
    await tester.pumpWidget(view(api));
    await tester.pumpAndSettle();
    await tester.pumpWidget(view(api, elapsed: 10));
    await tester.pumpAndSettle();
    expect(calls, 1);
    LibraryCache.forApi(api).invalidate();
    await tester.pumpWidget(view(api, elapsed: 11));
    await tester.pumpAndSettle();
    expect(calls, 2);
    api.close();
  });
  testWidgets('ignores previous track response after track switch', (
    tester,
  ) async {
    final old = Completer<http.Response>();
    final api = apiFor(
      (request) async => request.url.queryParameters['track'] == 'Old'
          ? old.future
          : response(27),
    );
    await tester.pumpWidget(view(api, name: 'Old'));
    await tester.pump();
    await tester.pumpWidget(view(api, name: 'New'));
    await tester.pumpAndSettle();
    expect(find.text('27'), findsOneWidget);
    old.complete(response(19));
    await tester.pumpAndSettle();
    expect(find.text('27'), findsOneWidget);
    expect(find.text('19'), findsNothing);
    api.close();
  });
  testWidgets('unavailable library is one retryable state, not empty counts', (
    tester,
  ) async {
    var calls = 0;
    final api = apiFor((request) async {
      calls++;
      return calls == 1 ? http.Response('{}', 503) : response(0);
    });
    await tester.pumpWidget(view(api));
    await tester.pumpAndSettle();
    expect(find.text('Listening history unavailable'), findsOneWidget);
    expect(find.text('0'), findsNothing);
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();
    expect(
      find.text('No recorded listens for this track yet.'),
      findsOneWidget,
    );
    expect(calls, 2);
    api.close();
  });
  testWidgets('unknown album omits optional query and has explicit state', (
    tester,
  ) async {
    final api = apiFor((request) async {
      expect(request.url.queryParameters.containsKey('album'), isFalse);
      final result = stats(0)..['album'] = null;
      return http.Response(jsonEncode(result), 200);
    });
    await tester.pumpWidget(view(api, album: ''));
    await tester.pumpAndSettle();
    expect(find.text('Album not identified'), findsOneWidget);
    expect(
      find.text('Album information is not available for this track.'),
      findsOneWidget,
    );
    api.close();
  });
  testWidgets('narrow layout has no horizontal overflow', (tester) async {
    tester.view.resetPhysicalSize();
    tester.view.physicalSize = const Size(400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = apiFor((request) async => response(17));
    await tester.pumpWidget(view(api));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    api.close();
  });
  testWidgets('returning to a recent track reuses its cached context', (
    tester,
  ) async {
    var calls = 0;
    final api = apiFor((request) async => response(++calls));
    await tester.pumpWidget(view(api, name: 'First'));
    await tester.pumpAndSettle();
    await tester.pumpWidget(view(api, name: 'Second'));
    await tester.pumpAndSettle();
    expect(calls, 2);
    await tester.pumpWidget(view(api, name: 'First'));
    await tester.pumpAndSettle();
    expect(calls, 2);
    expect(find.text('1'), findsWidgets);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
}
