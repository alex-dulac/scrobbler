import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/scrobbler_state.dart';
import '../services/scrobbler_api.dart';

class ScrobblerController extends ChangeNotifier {
  ScrobblerController({required this.api});
  final ScrobblerApi api;
  ScrobblerState? state;
  bool connected = false;
  bool busy = false;
  String? error;
  String? notice;
  Timer? _timer;
  bool _running = false;
  bool _disposed = false;
  int _generation = 0;
  Future<void>? _refresh;

  void start() {
    if (_running || _disposed) return;
    _running = true;
    unawaited(_poll());
  }

  Future<void> _poll() async {
    final generation = _generation;
    await refresh();
    if (_running && !_disposed && generation == _generation) {
      _timer = Timer(const Duration(seconds: 1), _poll);
    }
  }

  Future<void> refresh() =>
      _refresh ??= _fetch().whenComplete(() => _refresh = null);

  Future<void> _fetch() async {
    final generation = _generation;
    try {
      final snapshot = await api.fetchState();
      if (_disposed || generation != _generation) return;
      state = snapshot;
      connected = true;
      error = null;
    } catch (exception) {
      if (_disposed || generation != _generation) return;
      connected = false;
      error = exception is ApiException
          ? exception.message
          : 'Cannot reach the backend. Reconnecting…';
    }
    if (!_disposed) notifyListeners();
  }

  Future<void> _command(
    String method,
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    if (busy || !connected || _disposed) return;
    final generation = _generation;
    busy = true;
    notice = null;
    notifyListeners();
    try {
      final result = await api.request(method, path, body);
      if (_disposed || generation != _generation) return;
      notice = result['message'] as String?;
      await _refresh;
      if (_disposed || generation != _generation) return;
      await refresh();
    } catch (exception) {
      if (!_disposed && generation == _generation) {
        notice = exception is ApiException
            ? exception.message
            : 'Command failed. Please try again.';
      }
    } finally {
      busy = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> setScrobbling(bool enabled) =>
      _command('PUT', '/scrobble/status/', {'enabled': enabled});
  Future<void> selectIntegration(String integration) =>
      _command('PUT', '/integration/', {'integration': integration});
  Future<void> playback(String action) =>
      _command('POST', '/playback/', {'action': action});
  Future<void> scrobbleCurrent() => _command('POST', '/scrobble/');

  void stop() {
    _running = false;
    _generation++;
    _timer?.cancel();
  }

  @override
  void dispose() {
    stop();
    _disposed = true;
    api.close();
    super.dispose();
  }
}
