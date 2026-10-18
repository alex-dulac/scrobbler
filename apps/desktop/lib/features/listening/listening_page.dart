import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/album_art.dart';
import 'listening_context.dart';
import 'session_queue.dart';

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
    final progress = track == null
        ? 0.0
        : track.scrobbled
        ? 1.0
        : (track.scrobbleThreshold ?? 0) > 0
        ? (track.elapsed / track.scrobbleThreshold!).clamp(0.0, 1.0)
        : 0.0;
    final hero = ArtworkTint(
      api: controller.api,
      artist: track?.artist ?? '',
      album: track?.album ?? '',
      url: state?.artworkUrl,
      builder: (context, tint) {
        final surface = ScrobblerColors.of(context).surfaceRaised;
        return Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            borderRadius: AppRadii.largeAll,
            gradient: RadialGradient(
              center: const Alignment(-.85, -.9),
              radius: 1.6,
              // Opaque stops: fading through transparency leaves a light ring.
              colors: [
                Color.alphaBlend(tint.withValues(alpha: .30), surface),
                Color.alphaBlend(tint.withValues(alpha: .08), surface),
                surface,
              ],
              stops: const [0, .45, 1],
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      track == null
                          ? 'NOTHING PLAYING'
                          : track.playing
                          ? 'NOW PLAYING'
                          : 'PAUSED',
                      style: theme.textTheme.labelSmall?.copyWith(color: tint),
                    ),
                  ),
                  Text(
                    '${formatCount(state?.scrobbles.length ?? 0)} submitted this session',
                    style: theme.textTheme.labelSmall,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              LayoutBuilder(
                builder: (context, constraints) => Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    AlbumArt(
                      api: controller.api,
                      artist: track?.artist ?? '',
                      album: track?.album ?? '',
                      url: state?.artworkUrl,
                      size: constraints.maxWidth >= 600 ? 220 : 148,
                    ),
                    const SizedBox(width: 28),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            track?.name ?? 'No track selected',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.displaySmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            track?.artist ??
                                'Open Apple Music or Spotify to start playback.',
                            style: theme.textTheme.titleLarge,
                          ),
                          if (track?.album.isNotEmpty == true)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                track!.album,
                                style: theme.textTheme.bodyLarge?.copyWith(
                                  color: ScrobblerColors.of(context).textMuted,
                                ),
                              ),
                            ),
                          if (metadata.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(top: 10),
                              child: Text(
                                metadata.join(' · '),
                                style: AppFonts.numeric(
                                  theme.textTheme.bodySmall,
                                ),
                              ),
                            ),
                          if (track != null) ...[
                            const SizedBox(height: 18),
                            LinearProgressIndicator(
                              minHeight: 4,
                              borderRadius: AppRadii.smallAll,
                              color: tint,
                              backgroundColor: theme.colorScheme.outline
                                  .withValues(alpha: .35),
                              value: progress,
                            ),
                            const SizedBox(height: 8),
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
                                  style: AppFonts.numeric(
                                    theme.textTheme.bodySmall,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
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
            ],
          ),
        );
      },
    );
    final history = track != null
        ? ListeningContext(api: controller.api, track: track)
        : const Text(
            'Track, album, and artist listening history will appear here when a track is selected.',
          );
    final queue = SessionQueue(api: controller.api, state: state);
    return LayoutBuilder(
      builder: (context, constraints) => ListView(
        padding: AppSpacing.page,
        children: constraints.maxWidth >= 1040
            ? [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [hero, const SizedBox(height: 28), history],
                      ),
                    ),
                    const SizedBox(width: 24),
                    SizedBox(width: 300, child: queue),
                  ],
                ),
              ]
            : [
                hero,
                const SizedBox(height: 28),
                history,
                const SizedBox(height: 28),
                queue,
              ],
      ),
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
