import '../../services/scrobbler_api.dart';

class IpodPlay {
  IpodPlay.fromJson(Map<String, dynamic> json)
    : id = (json['id'] as num).toInt(),
      track = '${json['track_name'] ?? 'Unknown track'}',
      artist = '${json['artist_name'] ?? 'Unknown artist'}',
      album = json['album_name'] as String?,
      playedAt = DateTime.parse('${json['played_at']}').toLocal(),
      estimated = json['played_at_estimated'] == true;

  final int id;
  final String track, artist;
  final String? album;
  final DateTime playedAt;
  // Only a track's most recent play is timestamped on the iPod; earlier
  // repeats are assumed to have run back-to-back before it.
  final bool estimated;
}

class IpodApi {
  const IpodApi(this.api);
  final ScrobblerApi api;

  Future<List<IpodPlay>> plays() async =>
      ((await api.request('GET', '/ipod/plays/'))['plays'] as List? ?? [])
          .map((play) => IpodPlay.fromJson(play as Map<String, dynamic>))
          .toList();

  Future<String> scrobble(List<int> ids) => _command('/ipod/scrobble/', ids);
  Future<String> discard(List<int> ids) => _command('/ipod/discard/', ids);

  // Reading a large iTunesDB can take a while on older iPods.
  Future<String> rescan() async =>
      '${(await api.request('POST', '/ipod/rescan/', null, const Duration(seconds: 60)))['message']}';

  Future<String> _command(String path, List<int> ids) async =>
      '${(await api.request('POST', path, {'play_ids': ids}))['message']}';
}
