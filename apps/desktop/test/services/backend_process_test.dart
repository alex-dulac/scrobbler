import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:py_scrobbler_desktop/services/backend_process.dart';

void main() {
  group('owned backend lifecycle', () {
    late Directory project;
    late BackendProcess backend;

    setUp(() async {
      project = await Directory.systemTemp.createTemp(
        'scrobbler-backend-test-',
      );
      await Directory('${project.path}/.venv/bin').create(recursive: true);
      // /usr/bin/python3 can be an Xcode shim that dispatches on its invoked
      // name, so a link called `python` must target the real interpreter.
      final python = Process.runSync('/usr/bin/python3', [
        '-c',
        'import sys; print(sys.executable)',
      ]).stdout.toString().trim();
      await Link('${project.path}/.venv/bin/python').create(python);
      backend = BackendProcess(
        projectDirectory: project,
        startupTimeout: const Duration(seconds: 3),
        shutdownTimeout: const Duration(seconds: 1),
      );
    });

    tearDown(() async {
      await backend.stop();
      await project.delete(recursive: true);
    });

    test('starts, stops idempotently, and restarts its owned child', () async {
      await File('${project.path}/desktop_backend.py').writeAsString('''
import json, os, sys
assert os.environ['APP_TOKEN']
print(json.dumps({'event':'ready','host':'127.0.0.1','port':43123}), flush=True)
sys.stdin.buffer.read()
''');
      final connection = await backend.start();
      expect(connection.token.length, greaterThanOrEqualTo(40));
      expect(backend.isManaged, isTrue);
      await Future.wait([backend.stop(), backend.stop()]);
      expect(backend.isManaged, isFalse);
      final second = await backend.start();
      expect(second.token, isNot(connection.token));
    });

    test('reports a failed startup with diagnostics', () async {
      await File('${project.path}/desktop_backend.py').writeAsString('''
import sys
print('A managed scrobbler backend is already running', file=sys.stderr, flush=True)
sys.exit(2)
''');
      await expectLater(backend.start(), throwsA(isA<StateError>()));
      expect(backend.isManaged, isFalse);
    });

    test('kills a child that never announces readiness', () async {
      backend = BackendProcess(
        projectDirectory: project,
        startupTimeout: const Duration(milliseconds: 100),
        shutdownTimeout: const Duration(seconds: 1),
      );
      await File(
        '${project.path}/desktop_backend.py',
      ).writeAsString('import sys\nsys.stdin.buffer.read()\n');
      await expectLater(backend.start(), throwsA(isA<TimeoutException>()));
      expect(backend.isManaged, isFalse);
    });
  }, skip: !Platform.isMacOS);

  test('accepts only a loopback readiness handshake with a valid port', () {
    final connection = BackendConnection.fromReadyMessage(
      '{"event":"ready","host":"127.0.0.1","port":43123}',
      'secret',
    );
    expect(connection.baseUrl.toString(), 'http://127.0.0.1:43123');
    expect(connection.token, 'secret');
    for (final line in [
      '{"event":"ready","host":"0.0.0.0","port":43123}',
      '{"event":"ready","host":"127.0.0.1","port":0}',
      '{"event":"starting","host":"127.0.0.1","port":43123}',
    ]) {
      expect(
        () => BackendConnection.fromReadyMessage(line, 'secret'),
        throwsFormatException,
      );
    }
  });
}
