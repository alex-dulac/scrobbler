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
  static String onThisDayPath(DateTime day) => Uri(
    path: '/library/on-this-day/',
    queryParameters: {
      'date':
          '${day.year.toString().padLeft(4, '0')}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}',
    },
  ).toString();
  Future<Json> onThisDay(DateTime day, {bool force = false}) =>
      cache.get(onThisDayPath(day), force: force);
  Future<Json> artist(String artist, {bool force = false}) =>
      cache.get(artistPath(artist), force: force);

  /// Whether a scrobble by [artist] at local time [at] can change the
  /// response at [path]. Unknown paths are assumed affected.
  ///
  /// Other artists' ranks can shift too; those refresh when their entries
  /// expire rather than refetching every artist on each scrobble.
  static bool affectedBy(
    Uri path, {
    required String artist,
    required DateTime at,
  }) {
    final segments = path.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segments.length < 2 || segments[0] != 'library') return true;
    switch (segments[1]) {
      case 'wrapped':
        // A year's ranks are compared with the year before.
        final year = int.tryParse(segments.length > 2 ? segments[2] : '');
        return year == null || year == at.year || year == at.year + 1;
      case 'on-this-day':
        // Only earlier years of the same calendar day are shown.
        final day = DateTime.tryParse(path.queryParameters['date'] ?? '');
        return day == null ||
            (day.month == at.month && day.day == at.day && day.year > at.year);
      case 'artists' || 'context':
        return path.queryParameters['artist'] == artist;
      default:
        return true;
    }
  }
}
