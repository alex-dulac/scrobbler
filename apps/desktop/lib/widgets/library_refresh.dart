import 'dart:async';
import 'package:flutter/widgets.dart';
import '../services/library_cache.dart';
import '../services/scrobbler_api.dart';

/// Reloads library data when the cache changes, but only while visible.
///
/// Hidden tabs and pages under a pushed route have tickers disabled; they
/// reload when shown again, which also renews responses that expired while
/// hidden (a fresh cached response costs no request).
mixin LibraryRefresh<T extends StatefulWidget> on State<T> {
  ScrobblerApi get libraryApi;
  void reloadLibrary();

  LibraryCache? _cache;
  bool? _visible;

  void _cacheChanged() {
    if (_visible ?? true) reloadLibrary();
  }

  void _listen() {
    final cache = LibraryCache.forApi(libraryApi);
    if (identical(cache, _cache)) return;
    _cache?.removeListener(_cacheChanged);
    _cache = cache..addListener(_cacheChanged);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _listen();
    final visible = TickerMode.valuesOf(context).enabled;
    final shown = _visible == false && visible;
    _visible = visible;
    // Loading calls setState, which can't run mid-build.
    if (shown) {
      scheduleMicrotask(() {
        if (mounted) reloadLibrary();
      });
    }
  }

  @override
  void didUpdateWidget(covariant T oldWidget) {
    super.didUpdateWidget(oldWidget);
    _listen();
  }

  @override
  void dispose() {
    _cache?.removeListener(_cacheChanged);
    super.dispose();
  }
}
