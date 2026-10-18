import 'package:flutter/foundation.dart';
import 'scrobbler_api.dart';

/// Session-only library responses, isolated by backend client identity.
class LibraryCache extends ChangeNotifier {
  LibraryCache(
    this.api, {
    this.ttl = const Duration(seconds: 60),
    this.capacity = 80,
    DateTime Function()? now,
  }) : _now = now ?? DateTime.now;

  static final _clients = Expando<LibraryCache>();
  static LibraryCache forApi(ScrobblerApi api) =>
      _clients[api] ??= LibraryCache(api);

  final ScrobblerApi api;
  final Duration ttl;
  final int capacity;
  final DateTime Function() _now;
  final _entries = <String, _Entry>{};
  final _pending = <String, Future<Map<String, dynamic>>>{};

  /// Library queries run against a possibly remote database, so they get far
  /// more time than playback calls.
  static const libraryTimeout = Duration(seconds: 30);

  /// The latest response for [path], even if stale, for display while loading.
  Map<String, dynamic>? peek(String path) {
    final entry = _entries.remove(path);
    if (entry == null) return null;
    _entries[path] = entry;
    return entry.data;
  }

  Future<Map<String, dynamic>> get(String path, {bool force = false}) {
    final pending = _pending[path];
    if (pending != null) return pending;
    final entry = _entries[path];
    if (!force &&
        entry != null &&
        !entry.stale &&
        _now().difference(entry.loaded) < ttl) {
      return Future.value(peek(path)!);
    }
    late final Future<Map<String, dynamic>> request;
    request = api
        .request('GET', path, null, libraryTimeout)
        .then((data) {
          // Invalidation drops a request from _pending; a response begun
          // before then must not repopulate the cache.
          if (identical(_pending[path], request)) {
            _entries.remove(path);
            _entries[path] = _Entry(data, _now());
            while (_entries.length > capacity) {
              _entries.remove(_entries.keys.first);
            }
          }
          return data;
        })
        .whenComplete(() {
          if (identical(_pending[path], request)) _pending.remove(path);
        });
    _pending[path] = request;
    return request;
  }

  /// Marks every response stale.
  void invalidate() => invalidateWhere((_) => true);

  /// Marks the responses whose paths [affected] matches stale, and tells
  /// listeners so visible pages can refetch them.
  void invalidateWhere(bool Function(Uri path) affected) {
    for (final MapEntry(:key, :value) in _entries.entries) {
      if (affected(Uri.parse(key))) value.stale = true;
    }
    _pending.removeWhere((path, _) => affected(Uri.parse(path)));
    notifyListeners();
  }
}

class _Entry {
  _Entry(this.data, this.loaded);
  final Map<String, dynamic> data;
  final DateTime loaded;
  bool stale = false;
}
