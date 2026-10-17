import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/features/manual/manual_album_page.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

const preview = {
  'preview_id': 'reviewed-album-id',
  'artist': 'A & B / C',
  'album': 'Record #1?',
  'tracks': [
    {
      'name': 'Opening track',
      'started_at': '2026-01-01T12:00:00Z',
      'duration_seconds': 180,
      'eligible': true,
    },
    {
      'name': 'Short interlude',
      'started_at': '2026-01-01T12:03:00Z',
      'duration_seconds': 20,
      'eligible': false,
    },
  ],
};
http.Response response(Object value, [int code = 200]) =>
    http.Response(jsonEncode(value), code);
ScrobblerApi apiFor(Future<http.Response> Function(http.Request) handle) =>
    ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient(
        (request) async => request.url.path == '/artwork/'
            ? response({'url': null})
            : handle(request),
      ),
    );
Future<void> openPreview(WidgetTester tester, ScrobblerApi api) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: ManualAlbumPage(api: api)),
    ),
  );
  await tester.enterText(find.widgetWithText(TextField, 'Artist'), 'A & B / C');
  await tester.enterText(find.widgetWithText(TextField, 'Album'), 'Record #1?');
  await tester.tap(find.text('Preview album'));
  await tester.pumpAndSettle();
  await tester.scrollUntilVisible(
    find.text('Opening track'),
    150,
    scrollable: find.byType(Scrollable).first,
  );
}

Future<void> tapQueue(WidgetTester tester) async {
  await tester.scrollUntilVisible(
    find.text('Queue 1 reviewed tracks'),
    200,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.tap(find.text('Queue 1 reviewed tracks'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'preview uses encoded identity and UTC time, and marks ineligible tracks',
    (tester) async {
      final requests = <http.Request>[];
      final before = DateTime.now().toUtc();
      final api = apiFor((request) async {
        requests.add(request);
        return response(preview);
      });
      await openPreview(tester, api);
      final request = requests.single;
      expect(request.method, 'GET');
      expect(request.url.path, '/manual/album/');
      expect(request.url.queryParameters['artist'], 'A & B / C');
      expect(request.url.queryParameters['album'], 'Record #1?');
      final time = DateTime.parse(request.url.queryParameters['finished_at']!);
      expect(time.isUtc, isTrue);
      expect(time.isBefore(before), isFalse);
      expect(find.text('Opening track'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Short interlude'),
        150,
        scrollable: find.byType(Scrollable).first,
      );
      expect(
        find.text('Not submitted · tracks must be longer than 30 seconds'),
        findsOneWidget,
      );
      await tester.pumpWidget(const SizedBox());
      api.close();
    },
  );
  testWidgets('submits only preview ID and disables resubmission once queued', (
    tester,
  ) async {
    final posts = <http.Request>[];
    final api = apiFor((request) async {
      if (request.method == 'POST') {
        posts.add(request);
        return response({'count': 1, 'message': 'Saved.'});
      }
      return response(preview);
    });
    await openPreview(tester, api);
    await tapQueue(tester);
    expect(posts.single.url.path, '/manual/submit/');
    expect(jsonDecode(posts.single.body), {'preview_id': 'reviewed-album-id'});
    final queued = find.widgetWithText(FilledButton, 'Added to your queue');
    expect(tester.widget<FilledButton>(queued).onPressed, isNull);
    await tester.tap(queued);
    await tester.pumpAndSettle();
    expect(posts, hasLength(1));
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets('editing identity invalidates the reviewed preview', (
    tester,
  ) async {
    final api = apiFor((_) async => response(preview));
    await openPreview(tester, api);
    expect(find.text('Opening track'), findsOneWidget);
    await tester.ensureVisible(find.widgetWithText(TextField, 'Album'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Album'),
      'A different album',
    );
    await tester.pumpAndSettle();
    expect(find.text('Opening track'), findsNothing);
    expect(find.text('Queue 1 reviewed tracks'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets('failed submission retries the same preview ID', (tester) async {
    final posts = <Object>[];
    final api = apiFor((request) async {
      if (request.method == 'POST') {
        posts.add(jsonDecode(request.body));
        return posts.length == 1
            ? response({'detail': 'Temporarily unavailable'}, 503)
            : response({'count': 1, 'message': 'Saved.'});
      }
      return response(preview);
    });
    await openPreview(tester, api);
    await tapQueue(tester);
    expect(find.text('Temporarily unavailable'), findsOneWidget);
    await tapQueue(tester);
    expect(posts, [
      {'preview_id': 'reviewed-album-id'},
      {'preview_id': 'reviewed-album-id'},
    ]);
    expect(find.text('Added to your queue'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
  testWidgets('manual preview lays out at 600 pixel content width', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(600, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = apiFor((_) async => response(preview));
    await openPreview(tester, api);
    await tester.scrollUntilVisible(
      find.text('Queue 1 reviewed tracks'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });
}
