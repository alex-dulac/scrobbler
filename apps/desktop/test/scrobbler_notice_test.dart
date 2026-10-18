import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:py_scrobbler_desktop/controllers/scrobbler_controller.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

class _NoticeApi extends ScrobblerApi {
  _NoticeApi() : super(baseUrl: Uri.parse('http://localhost'), token: 'test');
  Future<Map<String, dynamic>> Function()? command;
  Map<String, dynamic> state = {};

  @override
  Future<Map<String, dynamic>> request(
    String method,
    String path, [
    Map<String, dynamic>? body,
    Duration timeout = const Duration(seconds: 8),
  ]) async {
    if (method == 'GET') return state;
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

  testWidgets('announces new iPod captures once', (tester) async {
    final api = _NoticeApi();
    final controller = ScrobblerController(api: api);
    addTearDown(controller.dispose);
    await controller.refresh();
    expect(controller.notice, isNull);

    api.state = {
      'ipod': {'capture_id': 1, 'last_captured': 3},
    };
    await controller.refresh();
    expect(
      controller.notice,
      'iPod connected: captured 3 new plays to review.',
    );
    expect(controller.noticeOpensIpod, isTrue);

    await tester.pump(const Duration(seconds: 4));
    await controller.refresh();
    expect(controller.notice, isNull);
    expect(controller.noticeOpensIpod, isFalse);
  });

  testWidgets('reports iPod capture errors', (tester) async {
    final api = _NoticeApi();
    final controller = ScrobblerController(api: api);
    addTearDown(controller.dispose);
    await controller.refresh();
    api.state = {
      'ipod': {'capture_id': 1, 'error': 'Failed to read plays from iPod'},
    };
    await controller.refresh();
    expect(controller.notice, 'Failed to read plays from iPod');
    expect(controller.noticeOpensIpod, isFalse);
    await tester.pump(const Duration(seconds: 8));
  });

  testWidgets('announces a finished iPod scrobble job', (tester) async {
    final api = _NoticeApi()
      ..state = {
        'ipod': {
          'job': {'id': 1, 'running': true, 'total': 3},
        },
      };
    final controller = ScrobblerController(api: api);
    addTearDown(controller.dispose);
    await controller.refresh();
    api.state = {
      'ipod': {
        'job': {
          'id': 1,
          'running': false,
          'total': 3,
          'scrobbled': 2,
          'failed': 1,
        },
      },
    };
    await controller.refresh();
    expect(
      controller.notice,
      'Scrobbled 2 iPod plays. 1 failed; retry them from the iPod page.',
    );
    expect(controller.noticeOpensIpod, isTrue);
    await tester.pump(const Duration(seconds: 8));
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
