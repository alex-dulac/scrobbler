import 'dart:async';
import 'package:py_scrobbler_desktop/features/library/listening_history_page.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/features/listening/listening_page.dart';
import 'package:py_scrobbler_desktop/screens/dashboard_screen.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';
import 'package:py_scrobbler_desktop/services/library_cache.dart';
import 'package:py_scrobbler_desktop/theme/app_theme.dart';

Map<String, dynamic> snapshot = {
  'active_integration_id': 'apple_music',
  'scrobble_enabled': true,
  'current_song': {
    'name': 'Test track',
    'artist': 'Test artist',
    'playing': true,
    'duration': 180,
    'time_played': 40,
    'scrobble_threshold': 90,
  },
  'session': {'pending': [], 'scrobbles': []},
};
ScrobblerController controllerFor(http.Client client) => ScrobblerController(
  api: ScrobblerApi(
    baseUrl: Uri.parse('http://localhost:8000'),
    token: 'secret',
    client: client,
  ),
);
void main() {
  test('authenticates and sends explicit scrobbling setting', () async {
    final requests = <http.Request>[];
    final controller = controllerFor(
      MockClient((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(
            request.method == 'GET' ? snapshot : {'message': 'Updated'},
          ),
          200,
        );
      }),
    );
    await controller.refresh();
    await controller.setScrobbling(false);
    expect(requests[0].headers['Authorization'], 'Bearer secret');
    final command = requests.singleWhere((r) => r.method == 'PUT');
    expect(command.url.path, '/scrobble/status/');
    expect(jsonDecode(command.body), {'enabled': false});
    controller.dispose();
  });
  test('stopped controller ignores pending response', () async {
    final response = Completer<http.Response>();
    final controller = controllerFor(MockClient((_) => response.future));
    final refresh = controller.refresh();
    controller.stop();
    response.complete(http.Response(jsonEncode(snapshot), 200));
    await refresh;
    expect(controller.connected, false);
    expect(controller.state, isNull);
    controller.dispose();
  });
  test('recovers after a failed request', () async {
    var fail = true;
    final controller = controllerFor(
      MockClient(
        (_) async => http.Response(jsonEncode(snapshot), fail ? 503 : 200),
      ),
    );
    await controller.refresh();
    expect(controller.connected, false);
    fail = false;
    await controller.refresh();
    expect(controller.connected, true);
    expect(controller.error, isNull);
    controller.dispose();
  });
  test(
    'library invalidation follows scrobbles and reconnects, not playback ticks',
    () async {
      var current = Map<String, dynamic>.from(snapshot);
      var fail = false;
      final controller = controllerFor(
        MockClient(
          (_) async => http.Response(jsonEncode(current), fail ? 503 : 200),
        ),
      );
      var invalidations = 0;
      final cache = LibraryCache.forApi(controller.api);
      void changed() => invalidations++;
      cache.addListener(changed);
      await controller.refresh();
      await controller.refresh();
      expect(invalidations, 0);
      current = {
        ...current,
        'session': {
          'pending': [],
          'scrobbles': [
            {
              'name': 'Submitted',
              'artist': 'Artist',
              'scrobbled_at': '2026-09-29T12:00:00Z',
            },
          ],
        },
      };
      await controller.refresh();
      expect(invalidations, 1);
      await controller.refresh();
      expect(invalidations, 1);
      fail = true;
      await controller.refresh();
      fail = false;
      await controller.refresh();
      expect(invalidations, 2);
      current = {...current, 'database_available': true};
      await controller.refresh();
      expect(invalidations, 3);
      cache.removeListener(changed);
      controller.dispose();
    },
  );
  testWidgets('shows live track and session navigation', (tester) async {
    final controller = controllerFor(
      MockClient((_) async => http.Response(jsonEncode(snapshot), 200)),
    );
    await controller.refresh();
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: DashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Test track'), findsWidgets);
    expect(find.text('Track history'), findsOneWidget);
    expect(find.text('Album history'), findsOneWidget);
    expect(find.text('Artist history'), findsOneWidget);
    expect(find.text('Good music.\nGreat company.'), findsNothing);
    expect(find.text('Test artist'), findsWidgets);
    expect(find.text('Scrobble at 1:30'), findsOneWidget);
    expect(
      tester
          .widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator))
          .value,
      closeTo(40 / 90, 0.0001),
    );
    // The session queue now lives on the Listening page.
    await tester.scrollUntilVisible(
      find.text('Your queue is clear.'),
      300,
      scrollable: find
          .descendant(
            of: find.byType(ListeningPage),
            matching: find.byType(Scrollable),
          )
          .first,
    );
    expect(find.text('Your queue is clear.'), findsOneWidget);
    expect(find.byTooltip('Session'), findsNothing);
    expect(find.byTooltip('Overview'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
  testWidgets('tabs retain history search, page, scroll and loaded results', (
    tester,
  ) async {
    final requests = <Uri>[];
    final controller = controllerFor(
      MockClient((request) async {
        requests.add(request.url);
        if (request.url.path == '/library/history/') {
          final page = int.parse(request.url.queryParameters['page']!);
          return http.Response(
            jsonEncode({
              'items': List.generate(
                40,
                (i) => {
                  'track': 'History $page track $i',
                  'artist': 'Archive artist',
                  'album': 'Archive album',
                  'scrobbled_at': '2026-01-01T12:00:00Z',
                },
              ),
              'page': page,
              'page_size': 40,
              'total': 100,
            }),
            200,
          );
        }
        return http.Response(jsonEncode(snapshot), 200);
      }),
    );
    await controller.refresh();
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: DashboardScreen(controller: controller),
      ),
    );
    await tester.pumpAndSettle();
    expect(requests.where((u) => u.path == '/library/history/'), isEmpty);
    await tester.tap(find.byTooltip('History'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Archive');
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    final searchController = tester
        .widget<TextField>(find.byType(TextField))
        .controller!;
    final historyList = find.descendant(
      of: find.byType(ListeningHistoryPage),
      matching: find.byType(ListView),
    );
    final scrollable = find
        .descendant(of: historyList, matching: find.byType(Scrollable))
        .first;
    final position = tester.state<ScrollableState>(scrollable).position;
    await tester.scrollUntilVisible(
      find.byTooltip('Next page'),
      500,
      scrollable: scrollable,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Next page'));
    await tester.pumpAndSettle();
    final offset = position.pixels;
    final count = requests.where((u) => u.path == '/library/history/').length;
    await tester.tap(find.byTooltip('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('History'));
    await tester.pumpAndSettle();
    expect(searchController.text, 'Archive');
    expect(find.text('Page 2'), findsOneWidget);
    expect(tester.state<ScrollableState>(scrollable).position.pixels, offset);
    expect(requests.where((u) => u.path == '/library/history/').length, count);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
}
