import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/services/library_cache.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';

ScrobblerApi apiFor(Future<http.Response> Function(http.Request) handler) =>
    ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient(handler),
    );
http.Response data(int value) =>
    http.Response(jsonEncode({'count': value}), 200);

void main() {
  test(
    'reuses fresh results, expires, forces refresh, and bounds memory',
    () async {
      var calls = 0;
      var now = DateTime(2026);
      final api = apiFor((_) async => data(++calls));
      final cache = LibraryCache(api, capacity: 2, now: () => now);
      expect((await cache.get('/a'))['count'], 1);
      expect((await cache.get('/a'))['count'], 1);
      now = now.add(const Duration(seconds: 61));
      expect(cache.peek('/a')!['count'], 1);
      expect((await cache.get('/a'))['count'], 2);
      expect((await cache.get('/a', force: true))['count'], 3);
      await cache.get('/b');
      cache.peek('/a');
      await cache.get('/c');
      expect(cache.peek('/b'), isNull);
      expect(cache.peek('/a'), isNotNull);
      api.close();
    },
  );

  test(
    'deduplicates pending requests and prevents stale cache writes',
    () async {
      final responses = <Completer<http.Response>>[];
      final api = apiFor((_) {
        final response = Completer<http.Response>();
        responses.add(response);
        return response.future;
      });
      final cache = LibraryCache(api);
      final first = cache.get('/a');
      final duplicate = cache.get('/a');
      expect(identical(first, duplicate), isTrue);
      await Future<void>.delayed(Duration.zero);
      cache.invalidate();
      final fresh = cache.get('/a');
      await Future<void>.delayed(Duration.zero);
      expect(responses.length, 2);
      responses[1].complete(data(2));
      await fresh;
      responses[0].complete(data(1));
      await first;
      expect(cache.peek('/a')!['count'], 2);
      api.close();
    },
  );

  test('targeted invalidation refetches only affected paths', () async {
    final requests = <String>[];
    final responses = <Completer<http.Response>>[];
    final api = apiFor((request) {
      requests.add(request.url.path);
      if (request.url.path == '/slow') {
        final response = Completer<http.Response>();
        responses.add(response);
        return response.future;
      }
      return Future.value(data(requests.length));
    });
    final cache = LibraryCache(api);
    var notified = 0;
    cache.addListener(() => notified++);
    await cache.get('/a');
    await cache.get('/b');
    final slow = cache.get('/slow');
    await Future<void>.delayed(Duration.zero);
    cache.invalidateWhere((path) => path.path != '/b');
    expect(notified, 1);
    // Stale responses stay available for display while refetching.
    expect(cache.peek('/a')!['count'], 1);
    await cache.get('/a');
    await cache.get('/b');
    expect(requests, ['/a', '/b', '/slow', '/a']);
    // The in-flight request was invalidated, so it can't fill the cache.
    responses.single.complete(data(7));
    await slow;
    expect(cache.peek('/slow'), isNull);
    api.close();
  });

  test('failed refresh retains cached result and is retryable', () async {
    var fail = false;
    var calls = 0;
    final api = apiFor((_) async {
      calls++;
      return fail ? http.Response('Unavailable', 503) : data(calls);
    });
    final cache = LibraryCache.forApi(api);
    await cache.get('/a');
    fail = true;
    await expectLater(
      cache.get('/a', force: true),
      throwsA(isA<ApiException>()),
    );
    expect(cache.peek('/a')!['count'], 1);
    fail = false;
    expect((await cache.get('/a', force: true))['count'], 3);
    final otherApi = apiFor((_) async => data(99));
    expect(LibraryCache.forApi(otherApi).peek('/a'), isNull);
    expect(identical(LibraryCache.forApi(api), cache), isTrue);
    api.close();
    otherApi.close();
  });
}
