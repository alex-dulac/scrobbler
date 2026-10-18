Map<String, dynamic> object(Object? value) =>
    value is Map<String, dynamic> ? value : <String, dynamic>{};

class ScrobbleTrack {
  ScrobbleTrack.fromJson(Map<String, dynamic> json)
    : name = (json['clean_name'] ?? json['name'] ?? 'Unknown track').toString(),
      artist = (json['artist'] ?? 'Unknown artist').toString(),
      album = (json['clean_album'] ?? json['album'] ?? '').toString(),
      genre = (json['genre'] ?? '').toString(),
      releaseYear = _positiveInteger(json['year']),
      trackNumber = _positiveInteger(json['track_number']),
      playing = json['playing'] == true,
      scrobbled = json['scrobbled'] == true,
      elapsed = (json['time_played'] as num?)?.toDouble() ?? 0,
      duration = (json['duration'] as num?)?.toDouble() ?? 0,
      scrobbleThreshold = (json['scrobble_threshold'] as num?)?.toDouble(),
      submittedAt = DateTime.tryParse('${json['scrobbled_at']}');

  final String name, artist, album, genre;
  final int? releaseYear, trackNumber;
  final bool playing, scrobbled;
  final double elapsed, duration;
  final double? scrobbleThreshold;
  final DateTime? submittedAt;

  static int? _positiveInteger(Object? value) {
    final number = value is num ? value.toInt() : int.tryParse('$value');
    return number != null && number > 0 ? number : null;
  }
}

class ListenerProfile {
  ListenerProfile.fromJson(Map<String, dynamic> json)
    : name = '${json['name'] ?? 'Last.fm'}',
      playcount = '${json['playcount'] ?? '—'}',
      artists = '${json['artist_count'] ?? '—'}',
      albums = '${json['album_count'] ?? '—'}';
  final String name, playcount, artists, albums;
}

class IpodStatus {
  IpodStatus.fromJson(Map<String, dynamic> json)
    : connected = json['connected'] == true,
      name = json['name'] as String?,
      captureId = _count(json['capture_id']),
      lastCaptured = _count(json['last_captured']),
      error = json['error'] as String?,
      pendingCount = _count(json['pending_count']),
      jobId = _count(object(json['job'])['id']),
      jobRunning = object(json['job'])['running'] == true,
      jobTotal = _count(object(json['job'])['total']),
      jobScrobbled = _count(object(json['job'])['scrobbled']),
      jobFailed = _count(object(json['job'])['failed']),
      jobError = object(json['job'])['error'] as String?;

  final bool connected, jobRunning;
  final String? name, error, jobError;
  // captureId and jobId increase with each capture and scrobble job, so a
  // change means there is something new to announce.
  final int captureId, lastCaptured, pendingCount;
  final int jobId, jobTotal, jobScrobbled, jobFailed;

  static int _count(Object? value) => value is num ? value.toInt() : 0;
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
      pending = _tracks(object(json['session'])['pending']),
      ipod = IpodStatus.fromJson(object(json['ipod']));

  final ScrobbleTrack? currentTrack;
  final bool scrobbleEnabled, isScrobbling, databaseAvailable;
  final String integration, runtimeState;
  final String? artworkUrl;
  final ListenerProfile? profile;
  final List<ScrobbleTrack> scrobbles, pending;
  final IpodStatus ipod;

  static List<ScrobbleTrack> _tracks(Object? values) => values is List
      ? values
            .map((value) => ScrobbleTrack.fromJson(object(value)))
            .toList(growable: false)
      : const [];
}
