import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/features/ipod/ipod_page.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

const plays = [
  {
    'id': 10,
    'track_name': 'Filler',
    'artist_name': 'Minor Threat',
    'album_name': 'Complete Discography',
    'played_at': '2026-10-17T22:30:00Z',
    'played_at_estimated': false,
  },
  {
    'id': 11,
    'track_name': 'Screaming At A Wall',
    'artist_name': 'Minor Threat',
    'album_name': null,
    'played_at': '2026-10-17T22:32:00Z',
    'played_at_estimated': true,
  },
];

Map<String, dynamic> stateWith({Map<String, dynamic> ipod = const {}}) => {
  'database_available': true,
  'session': {'pending': [], 'scrobbles': []},
  'ipod': {
    'connected': true,
    'name': 'IPOD',
    'capture_id': 1,
    'pending_count': 2,
    'job': {'id': 0, 'running': false},
    ...ipod,
  },
};

http.Response response(Object value) => http.Response(jsonEncode(value), 200);

class Backend {
  List<Map<String, Object?>> pending = plays;
  Map<String, dynamic> state = stateWith();
  final commands = <http.Request>[];

  ScrobblerController controller() => ScrobblerController(
    api: ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient((request) async {
        switch (request.url.path) {
          case '/state/':
            return response(state);
          case '/ipod/plays/':
            return response({'plays': pending});
        }
        commands.add(request);
        return response({'message': 'ok', 'count': 1});
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
      home: Scaffold(body: IpodPage(controller: controller)),
    ),
  );
  await tester.pumpAndSettle();
  return controller;
}

void main() {
  testWidgets('lists plays all selected, marking estimated times', (
    tester,
  ) async {
    await openPage(tester, Backend());
    expect(find.text('IPOD connected'), findsOneWidget);
    expect(find.text('Filler'), findsOneWidget);
    expect(find.text('Minor Threat · Complete Discography'), findsOneWidget);
    expect(find.text('2 of 2 selected'), findsOneWidget);
    expect(find.textContaining(RegExp(r'^~ ')), findsOneWidget);
  });

  testWidgets('scrobbles only the checked plays', (tester) async {
    final backend = Backend();
    await openPage(tester, backend);
    await tester.tap(find.text('Screaming At A Wall'));
    await tester.pump();
    expect(find.text('1 of 2 selected'), findsOneWidget);
    await tester.tap(find.text('Scrobble selected'));
    await tester.pumpAndSettle();
    final command = backend.commands.single;
    expect(command.url.path, '/ipod/scrobble/');
    expect(jsonDecode(command.body), {
      'play_ids': [10],
    });
  });

  testWidgets('discard asks for confirmation', (tester) async {
    final backend = Backend();
    await openPage(tester, backend);
    await tester.tap(find.text('Discard selected'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(backend.commands, isEmpty);

    await tester.tap(find.text('Discard selected'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Discard'));
    await tester.pumpAndSettle();
    final command = backend.commands.single;
    expect(command.url.path, '/ipod/discard/');
    expect(jsonDecode(command.body), {
      'play_ids': [10, 11],
    });
  });

  testWidgets('reloads when a new capture arrives', (tester) async {
    final backend = Backend()..pending = [];
    final controller = await openPage(tester, backend);
    expect(find.textContaining('No iPod plays to review'), findsOneWidget);

    backend
      ..pending = plays
      ..state = stateWith(ipod: {'capture_id': 2, 'last_captured': 2});
    await controller.refresh();
    await tester.pumpAndSettle();
    expect(find.text('2 of 2 selected'), findsOneWidget);
    // Let the capture notice expire.
    await tester.pump(const Duration(seconds: 4));
  });

  testWidgets('locks review while a scrobble job runs', (tester) async {
    final backend = Backend()
      ..state = stateWith(
        ipod: {
          'job': {'id': 1, 'running': true, 'total': 4, 'scrobbled': 1},
        },
      );
    await openPage(tester, backend);
    expect(find.text('Scrobbling 1 of 4…'), findsOneWidget);
    final scrobble = tester.widget<ButtonStyleButton>(
      find.ancestor(
        of: find.text('Scrobble selected'),
        matching: find.byWidgetPredicate(
          (widget) => widget is ButtonStyleButton,
        ),
      ),
    );
    expect(scrobble.onPressed, isNull);
  });
}
