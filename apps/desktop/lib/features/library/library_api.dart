import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import 'library_models.dart';

class LibraryApi {
  const LibraryApi(this.api);
  final ScrobblerApi api;
  LibraryCache get cache => LibraryCache.forApi(api);
  static String historyPath(String query, int page) => Uri(
    path: '/library/history/',
    queryParameters: {'query': query, 'page': '$page', 'page_size': '40'},
  ).toString();
  static String artistPath(String artist) => Uri(
    path: '/library/artists/',
    queryParameters: {'artist': artist},
  ).toString();
  Future<HistoryPage> history(
    String query,
    int page, {
    bool force = false,
  }) async => HistoryPage.fromJson(
    await cache.get(historyPath(query, page), force: force),
  );
  Future<List<int>> years({bool force = false}) async =>
      ((await cache.get('/library/years/', force: force))['years'] as List? ??
              [])
          .map(number)
          .toList();
  Future<Json> wrapped(int year, {bool force = false}) =>
      cache.get('/library/wrapped/$year/', force: force);
  Future<Json> artist(String artist, {bool force = false}) =>
      cache.get(artistPath(artist), force: force);
}
