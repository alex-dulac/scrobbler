import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/features/library/library_api.dart';
import 'package:py_scrobbler_desktop/features/library/listening_history_page.dart';
import 'package:py_scrobbler_desktop/features/library/wrapped_page.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

ScrobblerApi apiFor(Future<http.Response> Function(http.Request) handler) =>
    ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient(handler),
    );
http.Response data(Object value) => http.Response(jsonEncode(value), 200);
Map<String, dynamic> history(String title, {int total = 1}) => {
  'items': [
    {
      'track': title,
      'artist': 'A & B',
      'album': 'Record',
      'scrobbled_at': '2026-01-01T12:00:00Z',
    },
  ],
  'page': 1,
  'page_size': 40,
  'total': total,
};
void main() {
  test(
    'library API preserves encoded artist names and history query',
    () async {
      final urls = <Uri>[];
      final api = apiFor((request) async {
        urls.add(request.url);
        return data(history('Song'));
      });
      await LibraryApi(api).history('A & B / C', 2);
      await LibraryApi(api).artist('A & B / C');
      expect(urls.first.queryParameters['query'], 'A & B / C');
      expect(urls.first.queryParameters['page'], '2');
      expect(urls.last.queryParameters['artist'], 'A & B / C');
      api.close();
    },
  );
  testWidgets('history search ignores a stale response and debounces typing', (
    tester,
  ) async {
    final stale = Completer<http.Response>();
    var calls = 0;
    final api = apiFor((request) async {
      calls++;
      if (calls == 1) return stale.future;
      return data(history('New song'));
    });
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: ListeningHistoryPage(api: api)),
      ),
    );
    await tester.enterText(find.byType(TextField), 'new');
    await tester.pump(const Duration(milliseconds: 200));
    expect(calls, 1);
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pumpAndSettle();
    expect(find.text('New song'), findsOneWidget);
    stale.complete(data(history('Old song')));
    await tester.pumpAndSettle();
    expect(find.text('Old song'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets('database unavailable offers retry and recovers', (tester) async {
    var available = false;
    final api = apiFor(
      (_) async => available
          ? data(history('Recovered'))
          : http.Response('{"detail":"Database unavailable"}', 503),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: ListeningHistoryPage(api: api)),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Your listening library is unavailable'), findsOneWidget);
    available = true;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();
    expect(find.text('Recovered'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets('wrapped loads selected year and shows real counts', (
    tester,
  ) async {
    final api = apiFor(
      (request) async => request.url.path == '/library/years/'
          ? data({
              'years': [2026, 2025],
            })
          : data({
              'year': 2026,
              'total_scrobbles': 123,
              'unique_artists': 4,
              'monthly': [
                {'month': 1, 'count': 123},
              ],
              'top_artists': [],
              'top_albums': [],
              'top_tracks': [],
            }),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: WrappedPage(api: api)),
      ),
    );
    await tester.pumpAndSettle();
    // The scrobble total, and the same value labelling the peak month.
    expect(find.text('123'), findsNWidgets(2));
    expect(find.text('2026'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets(
    'history stays visible during refresh and after a refresh failure',
    (tester) async {
      final refresh = Completer<http.Response>();
      var calls = 0;
      final api = apiFor((_) {
        calls++;
        return calls == 1
            ? Future.value(data(history('Saved song')))
            : refresh.future;
      });
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: ListeningHistoryPage(api: api)),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Refresh history'));
      await tester.pump();
      expect(calls, 2);
      expect(find.text('Saved song'), findsOneWidget);
      refresh.complete(http.Response('Unavailable', 503));
      await tester.pumpAndSettle();
      expect(find.text('Saved song'), findsOneWidget);
      expect(find.text('Try again'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      api.close();
    },
  );
}
