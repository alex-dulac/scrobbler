import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/scrobbler_state.dart';
import '../services/scrobbler_api.dart';
import '../features/library/library_api.dart';
import '../services/library_cache.dart';

class ScrobblerController extends ChangeNotifier {
  ScrobblerController({required this.api});
  final ScrobblerApi api;
  ScrobblerState? state;
  bool connected = false;
  bool busy = false;
  String? error;
  String? notice;
  // Whether the current notice is about plays waiting on the iPod page.
  bool noticeOpensIpod = false;
  Timer? _timer;
  Timer? _noticeTimer;
  int _noticeGeneration = 0;
  bool _running = false;
  bool _disposed = false;
  int _generation = 0;
  Future<void>? _refresh;
  // Session scrobbles whose database writes haven't been seen to commit yet.
  final _uncommitted = <ScrobbleTrack>[];

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
      final previous = state;
      state = snapshot;
      if (previous != null) _invalidateLibrary(previous, snapshot);
      connected = true;
      error = null;
      if (previous != null) _announceIpod(previous.ipod, snapshot.ipod);
    } catch (exception) {
      if (_disposed || generation != _generation) return;
      connected = false;
      error = exception is ApiException
          ? exception.message
          : 'Cannot reach the backend. Reconnecting…';
    }
    if (!_disposed) notifyListeners();
  }

  static String _scrobbleIdentity(ScrobbleTrack track) =>
      '${track.artist}\u0000${track.name}\u0000${track.album}\u0000${track.submittedAt}';

  /// Refetches only what new scrobbles can change, once their writes commit.
  ///
  /// The session list gains a scrobble before its database write, so the
  /// backend's library revision (one step per committed write) decides when.
  void _invalidateLibrary(ScrobblerState previous, ScrobblerState current) {
    final cache = LibraryCache.forApi(api);
    final known = previous.scrobbles.map(_scrobbleIdentity).toSet();
    _uncommitted.addAll(
      current.scrobbles.where(
        (track) => !known.contains(_scrobbleIdentity(track)),
      ),
    );
    final written = current.libraryRevision - previous.libraryRevision;
    if (!connected ||
        previous.databaseAvailable != current.databaseAvailable ||
        written < 0) {
      // Reconnected, or the backend restarted: anything may have changed.
      _uncommitted.clear();
      cache.invalidate();
      return;
    }
    // iPod jobs write many plays; their completion refreshes everything.
    if (written == 0 || current.ipod.jobRunning) return;
    if (written > _uncommitted.length) {
      // Writes from outside the session list, so their contents are unknown.
      _uncommitted.clear();
      cache.invalidate();
      return;
    }
    final committed = _uncommitted.take(written).toList();
    _uncommitted.removeRange(0, written);
    cache.invalidateWhere(
      (path) => committed.any(
        (track) => LibraryApi.affectedBy(
          path,
          artist: track.artist,
          at: (track.submittedAt ?? DateTime.now()).toLocal(),
        ),
      ),
    );
  }

  void _announceIpod(IpodStatus previous, IpodStatus current) {
    if (current.captureId != previous.captureId) {
      if (current.error != null) {
        _showNotice(current.error, failed: true);
      } else if (current.lastCaptured > 0) {
        _showNotice(
          'iPod connected: captured ${current.lastCaptured} new plays to review.',
          opensIpod: true,
        );
      }
    }
    final jobFinished =
        current.jobId > 0 &&
        !current.jobRunning &&
        (previous.jobRunning || previous.jobId != current.jobId);
    if (jobFinished) {
      // iPod scrobbles bypass the session list that targets invalidation.
      _uncommitted.clear();
      LibraryCache.forApi(api).invalidate();
      final failed = current.jobFailed;
      _showNotice(
        [
          'Scrobbled ${current.jobScrobbled} iPod plays.',
          if (failed > 0) '$failed failed; retry them from the iPod page.',
          ?current.jobError,
        ].join(' '),
        failed: failed > 0,
        opensIpod: failed > 0,
      );
    }
  }

  void _clearNotice() {
    _noticeTimer?.cancel();
    _noticeTimer = null;
    _noticeGeneration++;
    notice = null;
    noticeOpensIpod = false;
  }

  void _showNotice(
    String? message, {
    bool failed = false,
    bool opensIpod = false,
  }) {
    _clearNotice();
    notice = message;
    noticeOpensIpod = opensIpod;
    if (message == null) return;
    final generation = _noticeGeneration;
    _noticeTimer = Timer(Duration(seconds: failed ? 8 : 4), () {
      if (_disposed || generation != _noticeGeneration) return;
      _clearNotice();
      notifyListeners();
    });
    notifyListeners();
  }

  Future<void> _command(
    String method,
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    if (busy || !connected || _disposed) return;
    final generation = _generation;
    busy = true;
    _clearNotice();
    notifyListeners();
    try {
      final result = await api.request(method, path, body);
      if (_disposed || generation != _generation) return;
      _showNotice(result['message'] as String?);
      await _refresh;
      if (_disposed || generation != _generation) return;
      await refresh();
    } catch (exception) {
      if (!_disposed && generation == _generation) {
        _showNotice(
          exception is ApiException
              ? exception.message
              : 'Command failed. Please try again.',
          failed: true,
        );
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
    _clearNotice();
  }

  @override
  void dispose() {
    stop();
    _disposed = true;
    api.close();
    super.dispose();
  }
}
