import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/screens/dashboard_screen.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';
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
    expect(find.text('Test track'), findsOneWidget);
    expect(find.text('Test artist'), findsOneWidget);
    expect(find.text('Scrobble at 1:30'), findsOneWidget);
    expect(tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    ).value, closeTo(40 / 90, 0.0001));
    await tester.tap(find.text('Session'));
    await tester.pumpAndSettle();
    expect(find.text('Your queue is clear.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
}
