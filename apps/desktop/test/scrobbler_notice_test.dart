import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

class _NoticeApi extends ScrobblerApi {
  _NoticeApi() : super(baseUrl: Uri.parse('http://localhost'), token: 'test');
  Future<Map<String, dynamic>> Function()? command;

  @override
  Future<Map<String, dynamic>> request(
    String method,
    String path, [
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 8),
  ]) async {
    if (method == 'GET') return {};
    return command?.call() ?? {'message': 'Scrobbling updated'};
  }
}

void main() {
  testWidgets('toggle notice clears four seconds after success', (
    tester,
  ) async {
    final controller = ScrobblerController(api: _NoticeApi());
    addTearDown(controller.dispose);
    await controller.refresh();
    await controller.setScrobbling(false);
    expect(controller.notice, 'Scrobbling updated');
    await tester.pump(const Duration(seconds: 3));
    expect(controller.notice, isNotNull);
    await tester.pump(const Duration(seconds: 1));
    expect(controller.notice, isNull);
  });

  testWidgets('new command cancels the previous notice deadline', (
    tester,
  ) async {
    final api = _NoticeApi();
    final controller = ScrobblerController(api: api);
    addTearDown(controller.dispose);
    await controller.refresh();
    await controller.setScrobbling(false);
    await tester.pump(const Duration(seconds: 3));
    final response = Completer<Map<String, dynamic>>();
    api.command = () => response.future;
    final pending = controller.setScrobbling(true);
    expect(controller.notice, isNull);
    await tester.pump(const Duration(seconds: 2));
    response.complete({'message': 'Scrobbling enabled'});
    await pending;
    await tester.pump(const Duration(seconds: 3));
    expect(controller.notice, 'Scrobbling enabled');
    await tester.pump(const Duration(seconds: 1));
    expect(controller.notice, isNull);
  });

  testWidgets('failed command stays visible longer and then clears', (
    tester,
  ) async {
    final api = _NoticeApi()
      ..command = () async => throw const ApiException('Try again');
    final controller = ScrobblerController(api: api);
    addTearDown(controller.dispose);
    await controller.refresh();
    await controller.setScrobbling(false);
    await tester.pump(const Duration(seconds: 4));
    expect(controller.notice, 'Try again');
    await tester.pump(const Duration(seconds: 4));
    expect(controller.notice, isNull);
  });

  testWidgets('dispose cancels pending notice notifications', (tester) async {
    final controller = ScrobblerController(api: _NoticeApi());
    await controller.refresh();
    await controller.setScrobbling(false);
    var notifications = 0;
    controller.addListener(() => notifications++);
    controller.dispose();
    await tester.pump(const Duration(seconds: 10));
    expect(notifications, 0);
    expect(tester.takeException(), isNull);
  });
}
