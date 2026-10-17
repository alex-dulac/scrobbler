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
  int _revision = 0;

  Map<String, dynamic>? peek(String path) {
    final entry = _entries.remove(path);
    if (entry == null) return null;
    _entries[path] = entry;
    return entry.data;
  }

  Future<Map<String, dynamic>> get(String path, {bool force = false}) {
    final key = '$_revision:$path';
    final pending = _pending[key];
    if (pending != null) return pending;
    final entry = _entries[path];
    if (!force &&
        entry != null &&
        entry.revision == _revision &&
        _now().difference(entry.loaded) < ttl) {
      return Future.value(peek(path)!);
    }
    final revision = _revision;
    late final Future<Map<String, dynamic>> request;
    request = api
        .request('GET', path)
        .then((data) {
          // Responses begun before invalidation must not repopulate the cache.
          if (revision == _revision) {
            _entries.remove(path);
            _entries[path] = _Entry(data, _now(), revision);
            while (_entries.length > capacity) {
              _entries.remove(_entries.keys.first);
            }
          }
          return data;
        })
        .whenComplete(() {
          _pending.remove(key);
        });
    _pending[key] = request;
    return request;
  }

  void invalidate() {
    _revision++;
    notifyListeners();
  }

  /// Called when revisiting tabs; fresh responses avoid network requests.
  void revalidate() => notifyListeners();
}

class _Entry {
  const _Entry(this.data, this.loaded, this.revision);
  final Map<String, dynamic> data;
  final DateTime loaded;
  final int revision;
}
