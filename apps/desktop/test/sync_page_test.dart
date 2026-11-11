import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/features/sync/sync_page.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

Map<String, dynamic> stateWith({
  Map<String, dynamic> sync = const {},
  int revision = 0,
}) => {
  'database_available': true,
  'library_revision': revision,
  'session': {'pending': [], 'scrobbles': []},
  'sync': {'id': 0, 'running': false, ...sync},
};

http.Response response(Object value) => http.Response(jsonEncode(value), 200);

class Backend {
  Map<String, dynamic> state = stateWith();
  final commands = <http.Request>[];

  ScrobblerController controller() => ScrobblerController(
    api: ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient((request) async {
        if (request.url.path == '/state/') return response(state);
        commands.add(request);
        return response({'message': 'ok'});
      }),
    ),
  );
}

Future<ScrobblerController> openPage(
  WidgetTester tester,
  Backend backend,
) async {
  final controller = backend.controller();
  addTearDown(controller.dispose);
  await controller.refresh();
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SyncPage(
          controller: controller,
          today: () => DateTime(2026, 11, 11, 15),
        ),
      ),
    ),
  );
  // A running sync's progress bar animates until it finishes.
  await tester.pump();
  return controller;
}

void main() {
  testWidgets('syncs the last week by default, through today', (tester) async {
    final backend = Backend();
    await openPage(tester, backend);
    expect(find.text('Nov 5, 2026 through today'), findsOneWidget);

    await tester.tap(find.text('Sync now'));
    await tester.pumpAndSettle();

    expect(backend.commands.single.url.path, '/sync/scrobbles/');
    expect(jsonDecode(backend.commands.single.body), {
      'time_from': '2026-11-05',
      'time_to': null,
    });
  });

  testWidgets('sends no dates for all history', (tester) async {
    final backend = Backend();
    await openPage(tester, backend);
    await tester.tap(find.text('All history'));
    await tester.pump();
    await tester.tap(find.text('Sync now'));
    await tester.pumpAndSettle();

    expect(jsonDecode(backend.commands.single.body), {
      'time_from': null,
      'time_to': null,
    });
  });

  testWidgets('shows progress, then announces the result', (tester) async {
    final backend = Backend()
      ..state = stateWith(
        sync: {
          'id': 1,
          'running': true,
          'time_from': '2026-11-05',
          'fetched': 400,
          'saved': 12,
        },
      );
    final controller = await openPage(tester, backend);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(
      find.text(
        'Nov 5, 2026 through today · checked 400 scrobbles, 12 new so far…',
      ),
      findsOneWidget,
    );
    expect(
      tester.widget<FilledButton>(find.byType(FilledButton).first).onPressed,
      isNull,
    );

    backend.state = stateWith(
      sync: {
        'id': 1,
        'running': false,
        'time_from': '2026-11-05',
        'fetched': 431,
        'saved': 15,
      },
      revision: 3,
    );
    await controller.refresh();
    await tester.pump();

    expect(controller.notice, 'Synced from Last.fm: 15 new of 431 scrobbles.');
    expect(
      find.text(
        'Nov 5, 2026 through today · checked 431 scrobbles, saved 15 new.',
      ),
      findsOneWidget,
    );
    await tester.pump(const Duration(seconds: 5));
  });

  testWidgets('shows why a sync could not start', (tester) async {
    final controller = ScrobblerController(
      api: ScrobblerApi(
        baseUrl: Uri.parse('http://localhost:8000'),
        token: 'test',
        client: MockClient((request) async {
          if (request.url.path == '/state/') return response(stateWith());
          return http.Response(
            jsonEncode({'detail': 'Scrobbles are already being synced.'}),
            409,
          );
        }),
      ),
    );
    addTearDown(controller.dispose);
    await controller.refresh();
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: SyncPage(controller: controller)),
      ),
    );
    await tester.tap(find.text('Sync now'));
    await tester.pumpAndSettle();

    expect(find.text('Scrobbles are already being synced.'), findsOneWidget);
  });
}
