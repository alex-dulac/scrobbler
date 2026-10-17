import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../models/scrobbler_state.dart';
import 'listening_page.dart';

class SessionPage extends StatelessWidget {
  const SessionPage({super.key, required this.state});
  final ScrobblerState? state;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(32),
    children: [
      Text('Session', style: Theme.of(context).textTheme.displaySmall),
      const SizedBox(height: 12),
      const Text('Submitted and pending scrobbles for this session.'),
      const SizedBox(height: 32),
      Text(
        'Pending submissions (${state?.pending.length ?? 0})',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 16),
      if (state?.pending.isNotEmpty != true)
        const Text('Your queue is clear.')
      else
        ...state!.pending.map(
          (track) => _ListenTile(track: track, pending: true),
        ),
      const SizedBox(height: 32),
      Text(
        'Submitted this session (${state?.scrobbles.length ?? 0})',
        style: Theme.of(context).textTheme.titleLarge,
      ),
      const SizedBox(height: 16),
      if (state?.scrobbles.isNotEmpty != true)
        const Text('No tracks submitted this session.')
      else
        ...state!.scrobbles.reversed.map((track) => _ListenTile(track: track)),
    ],
  );
}

class _ListenTile extends StatelessWidget {
  const _ListenTile({required this.track, this.pending = false});
  final ScrobbleTrack track;
  final bool pending;
  @override
  Widget build(BuildContext context) => ListTile(
    contentPadding: EdgeInsets.zero,
    leading: Icon(
      pending ? Icons.schedule_rounded : Icons.check_circle_rounded,
      color: pending
          ? Theme.of(context).colorScheme.tertiary
          : Theme.of(context).colorScheme.secondary,
    ),
    title: Text(track.name),
    subtitle: Text(
      '${track.artist}${track.album.isEmpty ? '' : ' · ${track.album}'}',
    ),
    trailing: track.submittedAt == null
        ? null
        : Text(
            TimeOfDay.fromDateTime(
              track.submittedAt!.toLocal(),
            ).format(context),
          ),
  );
}

class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key, required this.state});
  final ScrobblerState? state;
  @override
  Widget build(BuildContext context) {
    final profile = state?.profile;
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        Text('Last.fm profile', style: theme.textTheme.displaySmall),
        const SizedBox(height: 16),
        if (profile == null)
          const Text(
            'Your Last.fm profile is unavailable. Check your credentials and connection.',
          )
        else ...[
          Text(profile.name, style: theme.textTheme.titleLarge),
          const SizedBox(height: 32),
          Wrap(
            spacing: 16,
            runSpacing: 16,
            children: [
              _ProfileStat(
                'Scrobbles',
                profile.playcount,
                theme.colorScheme.primary,
              ),
              _ProfileStat(
                'Artists',
                profile.artists,
                theme.colorScheme.secondary,
              ),
              _ProfileStat(
                'Albums',
                profile.albums,
                theme.colorScheme.tertiary,
              ),
            ],
          ),
          const SizedBox(height: 24),
          const Text(
            'Lifetime totals from your Last.fm profile. Explore History and Wrapped for your locally synced library.',
          ),
        ],
      ],
    );
  }
}

class _ProfileStat extends StatelessWidget {
  const _ProfileStat(this.label, this.value, this.color);
  final String label, value;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    width: 200,
    padding: const EdgeInsets.all(24),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .14),
      borderRadius: BorderRadius.circular(22),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.headlineLarge?.copyWith(color: color),
        ),
        const SizedBox(height: 16),
        Text(label),
      ],
    ),
  );
}

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(32),
    children: [
      Text('Settings', style: Theme.of(context).textTheme.displaySmall),
      const SizedBox(height: 28),
      Align(
        alignment: Alignment.centerLeft,
        child: SourcePicker(controller: controller),
      ),
      const SizedBox(height: 28),
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Backend address'),
        subtitle: Text(controller.api.baseUrl.toString()),
      ),
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('History database'),
        subtitle: Text(
          controller.state?.databaseAvailable == true
              ? 'Connected · History and Wrapped use your synced library'
              : 'Unavailable · Live scrobbling and your pending queue still work',
        ),
      ),
      const SizedBox(height: 28),
      const Text(
        'Close the window to keep listening in the background. The menu bar brings you back; Quit stops the app.',
      ),
    ],
  );
}
