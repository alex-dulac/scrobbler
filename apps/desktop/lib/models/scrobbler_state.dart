Map<String, dynamic> object(Object? value) =>
    value is Map<String, dynamic> ? value : <String, dynamic>{};

class ScrobbleTrack {
  ScrobbleTrack.fromJson(Map<String, dynamic> json)
    : name = (json['clean_name'] ?? json['name'] ?? 'Unknown track').toString(),
      artist = (json['artist'] ?? 'Unknown artist').toString(),
      album = (json['clean_album'] ?? json['album'] ?? '').toString(),
      playing = json['playing'] == true,
      scrobbled = json['scrobbled'] == true,
      elapsed = (json['time_played'] as num?)?.toDouble() ?? 0,
      duration = (json['duration'] as num?)?.toDouble() ?? 0,
      scrobbleThreshold = (json['scrobble_threshold'] as num?)?.toDouble(),
      submittedAt = DateTime.tryParse('${json['scrobbled_at']}');

  final String name, artist, album;
  final bool playing, scrobbled;
  final double elapsed, duration;
  final double? scrobbleThreshold;
  final DateTime? submittedAt;
}

class ListenerProfile {
  ListenerProfile.fromJson(Map<String, dynamic> json)
    : name = '${json['name'] ?? 'Last.fm'}',
      playcount = '${json['playcount'] ?? '—'}',
      artists = '${json['artist_count'] ?? '—'}',
      albums = '${json['album_count'] ?? '—'}';
  final String name, playcount, artists, albums;
}

class ScrobblerState {
  ScrobblerState.fromJson(Map<String, dynamic> json)
    : currentTrack = json['current_song'] == null
          ? null
          : ScrobbleTrack.fromJson(object(json['current_song'])),
      scrobbleEnabled = json['scrobble_enabled'] == true,
      isScrobbling = json['is_scrobbling'] == true,
      integration = '${json['active_integration_id'] ?? 'apple_music'}',
      runtimeState = '${json['runtime_state'] ?? 'unknown'}',
      databaseAvailable = json['database_available'] == true,
      artworkUrl = object(json['lastfm_album'])['cover_image'] as String?,
      profile = json['user'] == null
          ? null
          : ListenerProfile.fromJson(object(json['user'])),
      scrobbles = _tracks(object(json['session'])['scrobbles']),
      pending = _tracks(object(json['session'])['pending']);

  final ScrobbleTrack? currentTrack;
  final bool scrobbleEnabled, isScrobbling, databaseAvailable;
  final String integration, runtimeState;
  final String? artworkUrl;
  final ListenerProfile? profile;
  final List<ScrobbleTrack> scrobbles, pending;

  static List<ScrobbleTrack> _tracks(Object? values) => values is List
      ? values
            .map((value) => ScrobbleTrack.fromJson(object(value)))
            .toList(growable: false)
      : const [];
}
