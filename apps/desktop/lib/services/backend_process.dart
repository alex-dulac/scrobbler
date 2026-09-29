import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

class BackendConnection {
  const BackendConnection({required this.baseUrl, required this.token});

  final Uri baseUrl;
  final String token;

  static BackendConnection fromReadyMessage(String line, String token) {
    final message = jsonDecode(line) as Map<String, dynamic>;
    final port = message['port'];
    if (message['event'] != 'ready' ||
        message['host'] != '127.0.0.1' ||
        port is! int ||
        port < 1 ||
        port > 65535) {
      throw const FormatException('Invalid backend readiness message');
    }
    return BackendConnection(
      baseUrl: Uri(scheme: 'http', host: '127.0.0.1', port: port),
      token: token,
    );
  }
}

/// Owns only the process started by this application, never an external server.
class BackendProcess {
  BackendProcess({
    this.projectDirectory,
    this.startupTimeout = const Duration(seconds: 45),
    this.shutdownTimeout = const Duration(seconds: 15),
  });

  final Directory? projectDirectory;
  final Duration startupTimeout;
  final Duration shutdownTimeout;
  Process? _process;
  StreamSubscription<String>? _output;
  StreamSubscription<String>? _errors;
  Future<void>? _shutdown;
  bool _stopping = false;
  void Function(String message)? onUnexpectedExit;
  final List<String> _diagnostics = [];

  bool get isManaged => _process != null;

  Future<BackendConnection> start() async {
    const externalUrl = String.fromEnvironment('SCROBBLER_BACKEND_URL');
    const externalToken = String.fromEnvironment('SCROBBLER_BACKEND_TOKEN');
    if (externalUrl.isNotEmpty) {
      final uri = Uri.parse(externalUrl);
      if (!uri.hasAuthority ||
          !['http', 'https'].contains(uri.scheme) ||
          externalToken.isEmpty) {
        throw StateError(
          'External mode requires a valid SCROBBLER_BACKEND_URL '
          'and SCROBBLER_BACKEND_TOKEN.',
        );
      }
      return BackendConnection(baseUrl: uri, token: externalToken);
    }

    final project = _findProject();
    final python = File('${project.path}/.venv/bin/python');
    if (!python.existsSync()) {
      throw StateError(
        'Python environment is missing. Run uv sync in '
        '${project.path}, then retry.',
      );
    }
    final random = Random.secure();
    final token = base64Url.encode(
      List.generate(32, (_) => random.nextInt(256)),
    );
    _stopping = false;
    _shutdown = null;
    _diagnostics.clear();
    final process = await Process.start(
      python.path,
      ['-u', '-m', 'desktop_backend'],
      workingDirectory: project.path,
      environment: {'APP_TOKEN': token, 'SCROBBLER_DESKTOP': '1'},
    );
    _process = process;
    final ready = Completer<BackendConnection>();
    _output = process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
          if (ready.isCompleted) return;
          try {
            ready.complete(BackendConnection.fromReadyMessage(line, token));
          } on FormatException {
            // Only the structured readiness message establishes a connection.
          } on TypeError {
            // Ignore ordinary output emitted by Python dependencies.
          }
        });
    _errors = process.stderr
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
          _diagnostics.add(line.replaceAll(token, '[redacted]'));
          if (_diagnostics.length > 12) _diagnostics.removeAt(0);
        });
    unawaited(
      process.exitCode.then((code) {
        final message =
            'Backend exited (code $code). ${_diagnostics.join('\n')}';
        if (!ready.isCompleted) {
          ready.completeError(StateError(message));
        } else if (!_stopping) {
          onUnexpectedExit?.call(message);
        }
      }),
    );
    try {
      return await ready.future.timeout(startupTimeout);
    } catch (_) {
      await stop();
      rethrow;
    }
  }

  Future<void> stop() => _shutdown ??= _stop();

  Future<void> _stop() async {
    _stopping = true;
    final process = _process;
    if (process != null) {
      process.kill(ProcessSignal.sigterm);
      try {
        await process.exitCode.timeout(shutdownTimeout);
      } on TimeoutException {
        process.kill(ProcessSignal.sigkill);
        await process.exitCode;
      }
      await process.stdin.close();
    }
    await _output?.cancel();
    await _errors?.cancel();
    _process = null;
  }

  Directory _findProject() {
    const configured = String.fromEnvironment('SCROBBLER_PROJECT_DIR');
    var directory =
        projectDirectory ??
        (configured.isEmpty ? Directory.current : Directory(configured));
    while (true) {
      if (File('${directory.path}/desktop_backend.py').existsSync()) {
        return directory;
      }
      if (projectDirectory != null ||
          configured.isNotEmpty ||
          directory.parent.path == directory.path) {
        break;
      }
      directory = directory.parent;
    }
    throw StateError(
      'Cannot locate the Python backend. Launch with '
      'scripts/run_desktop.sh, or set --dart-define=SCROBBLER_PROJECT_DIR='
      '/absolute/path/to/py-scrobbler.',
    );
  }
}
