typedef Json = Map<String, dynamic>;

List<Json> records(Json json, String key) =>
    (json[key] as List? ?? []).whereType<Json>().toList();
int number(dynamic value) => (value as num?)?.toInt() ?? 0;
String label(dynamic value) => value?.toString() ?? '';

class HistoryEntry {
  HistoryEntry.fromJson(Json json)
    : track = label(json['track']),
      artist = label(json['artist']),
      album = label(json['album']),
      date = DateTime.tryParse(label(json['scrobbled_at']))?.toLocal();
  final String track, artist, album;
  final DateTime? date;
}

class HistoryPage {
  HistoryPage.fromJson(Json json)
    : items = records(json, 'items').map(HistoryEntry.fromJson).toList(),
      page = number(json['page']),
      pageSize = number(json['page_size']),
      total = number(json['total']);
  final List<HistoryEntry> items;
  final int page, pageSize, total;
  bool get hasNext => page * pageSize < total;
}
