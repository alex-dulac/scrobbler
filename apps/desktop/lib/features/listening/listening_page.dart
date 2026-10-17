import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../widgets/album_art.dart';
import 'listening_context.dart';

class ListeningPage extends StatelessWidget {
  const ListeningPage({super.key, required this.controller});
  final ScrobblerController controller;

  @override
  Widget build(BuildContext context) {
    final state = controller.state;
    final track = state?.currentTrack;
    final theme = Theme.of(context);
    final enabled = controller.connected && !controller.busy;
    final metadata = <String>[
      if ((track?.duration ?? 0) > 0) '${_time(track!.duration)} duration',
      if (track?.releaseYear != null) '${track!.releaseYear}',
      if (track?.genre.isNotEmpty == true) track!.genre,
      if (track?.trackNumber != null) 'Track ${track!.trackNumber}',
    ];
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
      children: [
        Row(
          children: [
            Expanded(
              child: Text('Now playing', style: theme.textTheme.headlineMedium),
            ),
            Text(
              '${state?.scrobbles.length ?? 0} submitted this session',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 18),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AlbumArt(
              api: controller.api,
              artist: track?.artist ?? '',
              album: track?.album ?? '',
              url: state?.artworkUrl,
              size: 136,
            ),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    track?.name ?? 'No track selected',
                    style: theme.textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    track?.artist ??
                        'Open Apple Music or Spotify to start playback.',
                    style: theme.textTheme.titleMedium,
                  ),
                  if (track?.album.isNotEmpty == true)
                    Padding(
                      padding: const EdgeInsets.only(top: 3),
                      child: Text(track!.album),
                    ),
                  if (metadata.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Text(
                        metadata.join(' · '),
                        style: theme.textTheme.bodySmall,
                      ),
                    ),
                  if (track != null) ...[
                    const SizedBox(height: 14),
                    LinearProgressIndicator(
                      minHeight: 4,
                      borderRadius: BorderRadius.circular(2),
                      color: theme.colorScheme.primary,
                      backgroundColor: theme.colorScheme.outline.withValues(
                        alpha: .35,
                      ),
                      value: track.scrobbled
                          ? 1
                          : (track.scrobbleThreshold ?? 0) > 0
                          ? (track.elapsed / track.scrobbleThreshold!).clamp(
                              0,
                              1,
                            )
                          : 0,
                    ),
                    const SizedBox(height: 7),
                    Wrap(
                      spacing: 14,
                      runSpacing: 4,
                      children: [
                        Text(
                          track.scrobbled
                              ? 'Submitted to Last.fm'
                              : state?.isScrobbling == true
                              ? 'Submitting…'
                              : 'Scrobble at ${_time(track.scrobbleThreshold ?? 0)}',
                          style: theme.textTheme.labelLarge,
                        ),
                        Text(
                          '${_time(track.elapsed)} listened · ${track.playing ? 'Playing' : 'Paused'}',
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 10,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            SourcePicker(controller: controller),
            OutlinedButton.icon(
              onPressed:
                  enabled &&
                      track?.playing == true &&
                      track?.scrobbled == false &&
                      state?.scrobbleEnabled == true &&
                      state?.isScrobbling == false
                  ? controller.scrobbleCurrent
                  : null,
              icon: const Icon(Icons.add_task, size: 17),
              label: const Text('Scrobble now'),
            ),
          ],
        ),
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 22),
          child: Divider(),
        ),
        if (track != null)
          ListeningContext(api: controller.api, track: track)
        else
          const Text(
            'Track, album, and artist listening history will appear here when a track is selected.',
          ),
      ],
    );
  }

  String _time(double seconds) =>
      '${seconds ~/ 60}:${(seconds.toInt() % 60).toString().padLeft(2, '0')}';
}

class SourcePicker extends StatelessWidget {
  const SourcePicker({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) => SegmentedButton<String>(
    segments: const [
      ButtonSegment(value: 'apple_music', label: Text('Apple Music')),
      ButtonSegment(value: 'spotify', label: Text('Spotify')),
    ],
    selected: {controller.state?.integration ?? 'apple_music'},
    onSelectionChanged: controller.connected && !controller.busy
        ? (value) => controller.selectIntegration(value.single)
        : null,
  );
}

class PlaybackControls extends StatelessWidget {
  const PlaybackControls({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) {
    final track = controller.state?.currentTrack;
    final enabled = controller.connected && !controller.busy && track != null;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          tooltip: 'Previous track',
          onPressed: enabled ? () => controller.playback('previous') : null,
          icon: const Icon(Icons.skip_previous_rounded),
        ),
        IconButton.filled(
          tooltip: 'Play / pause',
          onPressed: enabled ? () => controller.playback('pause') : null,
          icon: Icon(
            track?.playing == true
                ? Icons.pause_rounded
                : Icons.play_arrow_rounded,
          ),
        ),
        IconButton(
          tooltip: 'Next track',
          onPressed: enabled ? () => controller.playback('next') : null,
          icon: const Icon(Icons.skip_next_rounded),
        ),
      ],
    );
  }
}
