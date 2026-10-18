import 'package:flutter/material.dart';
import '../../models/scrobbler_state.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/album_art.dart';

/// Pending and submitted scrobbles for this session, shown beside playback.
class SessionQueue extends StatelessWidget {
  const SessionQueue({super.key, required this.api, required this.state});
  final ScrobblerApi api;
  final ScrobblerState? state;
  static const _submittedShown = 12;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final pending = state?.pending ?? const <ScrobbleTrack>[];
    final submitted = (state?.scrobbles ?? const <ScrobbleTrack>[]).reversed
        .toList();
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ScrobblerColors.of(context).surfaceRaised,
        borderRadius: AppRadii.largeAll,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('This session', style: theme.textTheme.titleMedium),
          const SizedBox(height: 16),
          _Heading('Pending', pending.length),
          if (pending.isEmpty)
            const _Empty('Your queue is clear.')
          else
            for (final track in pending)
              _Row(api: api, track: track, pending: true),
          const SizedBox(height: 18),
          _Heading('Submitted', submitted.length),
          if (submitted.isEmpty)
            const _Empty('No tracks submitted this session.')
          else ...[
            for (final track in submitted.take(_submittedShown))
              _Row(api: api, track: track),
            if (submitted.length > _submittedShown)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  '+ ${formatCount(submitted.length - _submittedShown)} earlier',
                  style: theme.textTheme.bodySmall,
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _Heading extends StatelessWidget {
  const _Heading(this.title, this.count);
  final String title;
  final int count;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      '${title.toUpperCase()} · ${formatCount(count)}',
      style: Theme.of(context).textTheme.labelSmall,
    ),
  );
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;
  @override
  Widget build(BuildContext context) =>
      Text(text, style: Theme.of(context).textTheme.bodyMedium);
}

class _Row extends StatelessWidget {
  const _Row({required this.api, required this.track, this.pending = false});
  final ScrobblerApi api;
  final ScrobbleTrack track;
  final bool pending;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          AlbumArt(
            api: api,
            artist: track.artist,
            album: track.album,
            size: 36,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  track.name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyLarge?.copyWith(fontSize: 13),
                ),
                Text(
                  track.artist,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (pending)
            Tooltip(
              message: 'Waiting to submit to Last.fm',
              child: Icon(
                Icons.schedule_rounded,
                size: 16,
                color: colors.warning,
              ),
            )
          else if (track.submittedAt != null)
            Text(
              formatClock(track.submittedAt!.toLocal()),
              style: AppFonts.numeric(theme.textTheme.bodySmall),
            ),
        ],
      ),
    );
  }
}
