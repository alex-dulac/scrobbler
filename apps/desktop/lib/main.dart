import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'controllers/scrobbler_controller.dart';
import 'screens/dashboard_screen.dart';
import 'services/backend_process.dart';
import 'services/scrobbler_api.dart';
import 'theme/app_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ScrobblerApp());
}

class ScrobblerApp extends StatefulWidget {
  const ScrobblerApp({super.key});

  @override
  State<ScrobblerApp> createState() => _ScrobblerAppState();
}

class _ScrobblerAppState extends State<ScrobblerApp> {
  static const _desktop = MethodChannel('py_scrobbler/desktop');
  final _backend = BackendProcess();
  ScrobblerController? _controller;
  String? _startupError;
  bool _starting = false;
  bool _quitting = false;
  Future<void>? _startTask;

  @override
  void initState() {
    super.initState();
    _desktop.setMethodCallHandler(_handleDesktop);
    _backend.onUnexpectedExit = (message) {
      if (!mounted || _quitting) return;
      _controller?.stop();
      setState(() => _startupError = message);
      unawaited(_updateMenu());
    };
    _startTask = _connect();
  }

  Future<void> _handleDesktop(MethodCall call) async {
    switch (call.method) {
      case 'toggleScrobbling':
        final controller = _controller;
        if (!_quitting && controller != null && controller.connected) {
          await controller.setScrobbling(
            !(controller.state?.scrobbleEnabled ?? true),
          );
        }
      case 'quitRequested':
        if (_quitting) return;
        setState(() => _quitting = true);
        // Startup and shutdown must not race and leave a late child orphaned.
        try {
          await _startTask;
          _controller?.stop();
          await _backend.stop();
        } finally {
          await _desktop.invokeMethod<void>('quitReady');
        }
      case 'showDashboard':
        break;
    }
  }

  Future<void> _connect() async {
    if (_starting || _quitting) return;
    setState(() {
      _starting = true;
      _startupError = null;
    });
    _controller?.removeListener(_onStateChanged);
    _controller?.dispose();
    _controller = null;
    unawaited(_updateMenu());
    try {
      await _backend.stop();
      if (_quitting) return;
      final connection = await _backend.start();
      if (_quitting) return;
      final controller = ScrobblerController(
        api: ScrobblerApi(baseUrl: connection.baseUrl, token: connection.token),
      );
      controller.addListener(_onStateChanged);
      _controller = controller;
      controller.start();
    } catch (error) {
      if (mounted) setState(() => _startupError = error.toString());
    } finally {
      if (mounted) setState(() => _starting = false);
      unawaited(_updateMenu());
    }
  }

  void _onStateChanged() => unawaited(_updateMenu());

  Future<void> _updateMenu() async {
    final controller = _controller;
    final track = controller?.state?.currentTrack;
    try {
      await _desktop.invokeMethod<void>('updateStatus', {
        'track': _startupError != null || controller?.connected != true
            ? 'Backend disconnected'
            : track == null
            ? 'Waiting for playback'
            : '${track.name} — ${track.artist}',
        'enabled': controller?.state?.scrobbleEnabled ?? false,
        'connected': _startupError == null && controller?.connected == true,
        'busy': _quitting || (controller?.busy ?? false),
      });
    } on MissingPluginException {
      // Unit tests do not have the macOS host.
    }
  }

  @override
  void dispose() {
    _desktop.setMethodCallHandler(null);
    _controller?.removeListener(_onStateChanged);
    _controller?.dispose();
    unawaited(_backend.stop());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Scrobbler',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark,
      home: _quitting
          ? const _ConnectionScreen(message: 'Stopping your scrobbler…')
          : _startupError != null
          ? _ConnectionScreen(
              message: 'Could not connect to the scrobbler',
              detail: _startupError,
              onRetry: () => _startTask = _connect(),
            )
          : _controller == null
          ? const _ConnectionScreen(message: 'Starting your scrobbler…')
          : DashboardScreen(controller: _controller!),
    );
  }
}

class _ConnectionScreen extends StatelessWidget {
  const _ConnectionScreen({required this.message, this.detail, this.onRetry});
  final String message;
  final String? detail;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.music_note_rounded, size: 48),
                const SizedBox(height: 24),
                Text(
                  message,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 24),
                if (detail == null) const CircularProgressIndicator(),
                if (detail != null) SelectableText(detail!),
                if (onRetry != null) ...[
                  const SizedBox(height: 24),
                  FilledButton(
                    onPressed: onRetry,
                    child: const Text('Retry connection'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
