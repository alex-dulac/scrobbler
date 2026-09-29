import 'package:flutter/material.dart';
import '../controllers/scrobbler_controller.dart';
import '../models/scrobbler_state.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _page = 0;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.controller,
    builder: (context, _) {
      final controller = widget.controller;
      final state = controller.state;
      final enabled = controller.connected && !controller.busy;
      return Scaffold(
        body: SafeArea(
          child: Row(
            children: [
              NavigationRail(
                selectedIndex: _page,
                onDestinationSelected: (value) => setState(() => _page = value),
                labelType: NavigationRailLabelType.all,
                leading: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 20),
                  child: Icon(Icons.album, size: 32),
                ),
                destinations: const [
                  NavigationRailDestination(
                    icon: Icon(Icons.graphic_eq),
                    label: Text('Listening'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.history),
                    label: Text('Session'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.person_outline),
                    label: Text('Profile'),
                  ),
                  NavigationRailDestination(
                    icon: Icon(Icons.settings_outlined),
                    label: Text('Settings'),
                  ),
                ],
              ),
              const VerticalDivider(width: 1),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(32),
                  children: [
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 20,
                      children: [
                        Text(
                          [
                            'Now listening',
                            'Listening session',
                            'Your Last.fm',
                            'Settings',
                          ][_page],
                          style: Theme.of(context).textTheme.headlineLarge,
                        ),
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.circle,
                              size: 9,
                              color: controller.connected
                                  ? Colors.tealAccent
                                  : Colors.orangeAccent,
                            ),
                            const SizedBox(width: 8),
                            Text(
                              controller.connected
                                  ? 'Connected'
                                  : 'Reconnecting',
                            ),
                            const SizedBox(width: 16),
                            const Text('Scrobbling'),
                            Switch(
                              value: state?.scrobbleEnabled ?? false,
                              onChanged: enabled
                                  ? controller.setScrobbling
                                  : null,
                            ),
                          ],
                        ),
                      ],
                    ),
                    const SizedBox(height: 24),
                    if (controller.error != null)
                      _message(controller.error!, Icons.cloud_off),
                    if (controller.notice != null)
                      _message(controller.notice!, Icons.info_outline),
                    if (state == null)
                      const Padding(
                        padding: EdgeInsets.all(48),
                        child: Center(
                          child: Text('Waiting for the scrobbler backend…'),
                        ),
                      )
                    else
                      ...switch (_page) {
                        0 => _listening(state, enabled),
                        1 => _session(state),
                        2 => _profile(state),
                        _ => _settings(state, enabled),
                      },
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    },
  );

  Widget _message(String text, IconData icon) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(icon),
            const SizedBox(width: 12),
            Expanded(child: Text(text)),
          ],
        ),
      ),
    ),
  );

  List<Widget> _listening(ScrobblerState state, bool enabled) {
    final track = state.currentTrack;
    final controller = widget.controller;
    return [
      Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: SizedBox(
                      width: 128,
                      height: 128,
                      child: state.artworkUrl == null
                          ? _artworkPlaceholder()
                          : Image.network(
                              state.artworkUrl!,
                              fit: BoxFit.cover,
                              errorBuilder: (_, error, stack) =>
                                  _artworkPlaceholder(),
                            ),
                    ),
                  ),
                  const SizedBox(width: 24),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          track == null
                              ? 'READY WHEN YOU ARE'
                              : track.playing
                              ? 'NOW PLAYING'
                              : 'PAUSED',
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          track?.name ?? 'Play something you love',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          track?.artist ??
                              'Open Apple Music or Spotify to get started.',
                        ),
                        if (track?.album.isNotEmpty == true) Text(track!.album),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              if (track != null) ...[
                LinearProgressIndicator(
                  value: track.scrobbled
                      ? 1
                      : (track.scrobbleThreshold ?? 0) > 0
                      ? (track.elapsed / track.scrobbleThreshold!).clamp(0, 1)
                      : 0,
                ),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('${_time(track.elapsed)} listened'),
                    Text(
                      track.scrobbled
                          ? 'Scrobbled to Last.fm'
                          : state.isScrobbling
                          ? 'Submitting…'
                          : track.scrobbleThreshold != null
                          ? 'Scrobble at ${_time(track.scrobbleThreshold!)}'
                          : 'Waiting to scrobble',
                    ),
                  ],
                ),
                const SizedBox(height: 16),
              ],
              Wrap(
                spacing: 12,
                runSpacing: 12,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  IconButton(
                    tooltip: 'Previous track',
                    onPressed: enabled && track != null
                        ? () => controller.playback('previous')
                        : null,
                    icon: const Icon(Icons.skip_previous),
                  ),
                  IconButton(
                    tooltip: 'Play / pause',
                    onPressed: enabled && track != null
                        ? () => controller.playback('pause')
                        : null,
                    icon: Icon(
                      track?.playing == true ? Icons.pause : Icons.play_arrow,
                    ),
                  ),
                  IconButton(
                    tooltip: 'Next track',
                    onPressed: enabled && track != null
                        ? () => controller.playback('next')
                        : null,
                    icon: const Icon(Icons.skip_next),
                  ),
                  FilledButton.icon(
                    onPressed:
                        enabled &&
                            track?.playing == true &&
                            track?.scrobbled == false &&
                            state.scrobbleEnabled &&
                            !state.isScrobbling
                        ? controller.scrobbleCurrent
                        : null,
                    icon: const Icon(Icons.check),
                    label: const Text('Scrobble now'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
      const SizedBox(height: 24),
      _sourcePicker(state, enabled),
      const SizedBox(height: 24),
      Wrap(
        spacing: 24,
        runSpacing: 12,
        children: [
          Text('${state.scrobbles.length} submitted this session'),
          Text('${state.pending.length} queued'),
        ],
      ),
      const SizedBox(height: 16),
      const Text(
        'Closing the window keeps scrobbling in the menu bar. Choose Quit to stop the app.',
      ),
    ];
  }

  Widget _sourcePicker(ScrobblerState state, bool enabled) => Wrap(
    spacing: 16,
    crossAxisAlignment: WrapCrossAlignment.center,
    children: [
      const Text('Music source'),
      SegmentedButton<String>(
        segments: const [
          ButtonSegment(value: 'apple_music', label: Text('Apple Music')),
          ButtonSegment(value: 'spotify', label: Text('Spotify')),
        ],
        selected: {state.integration},
        onSelectionChanged: enabled
            ? (selection) =>
                  widget.controller.selectIntegration(selection.single)
            : null,
      ),
    ],
  );

  List<Widget> _session(ScrobblerState state) => [
    Text(
      'Pending submissions (${state.pending.length})',
      style: Theme.of(context).textTheme.titleLarge,
    ),
    const SizedBox(height: 12),
    if (state.pending.isEmpty)
      const Text('Your queue is clear.')
    else
      ...state.pending.map((track) => _trackTile(track, pending: true)),
    const SizedBox(height: 32),
    Text(
      'Submitted this session (${state.scrobbles.length})',
      style: Theme.of(context).textTheme.titleLarge,
    ),
    const SizedBox(height: 12),
    if (state.scrobbles.isEmpty)
      const Text('Tracks will appear here after they are submitted to Last.fm.')
    else
      ...state.scrobbles.reversed.map(_trackTile),
  ];
  Widget _trackTile(ScrobbleTrack track, {bool pending = false}) => ListTile(
    contentPadding: EdgeInsets.zero,
    leading: Icon(pending ? Icons.schedule : Icons.check_circle_outline),
    title: Text(track.name),
    subtitle: Text(
      '${track.artist}${track.album.isEmpty ? '' : ' • ${track.album}'}',
    ),
    trailing: track.submittedAt == null
        ? null
        : Text(
            TimeOfDay.fromDateTime(
              track.submittedAt!.toLocal(),
            ).format(context),
          ),
  );

  List<Widget> _profile(ScrobblerState state) {
    final profile = state.profile;
    if (profile == null) {
      return [
        const Text(
          'Last.fm profile is unavailable. Check the backend credentials and network connection.',
        ),
      ];
    }
    return [
      Text(profile.name, style: Theme.of(context).textTheme.displaySmall),
      const SizedBox(height: 24),
      Wrap(
        spacing: 32,
        runSpacing: 24,
        children: [
          _stat('Scrobbles', profile.playcount),
          _stat('Artists', profile.artists),
          _stat('Albums', profile.albums),
        ],
      ),
    ];
  }

  Widget _stat(String label, String value) => SizedBox(
    width: 180,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(value, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 8),
            Text(label),
          ],
        ),
      ),
    ),
  );
  List<Widget> _settings(ScrobblerState state, bool enabled) => [
    _sourcePicker(state, enabled),
    const SizedBox(height: 24),
    ListTile(
      contentPadding: EdgeInsets.zero,
      title: const Text('Backend address'),
      subtitle: Text(widget.controller.api.baseUrl.toString()),
    ),
    ListTile(
      contentPadding: EdgeInsets.zero,
      title: const Text('Runtime'),
      subtitle: Text(state.runtimeState),
    ),
    ListTile(
      contentPadding: EdgeInsets.zero,
      title: const Text('History database'),
      subtitle: Text(
        state.databaseAvailable
            ? 'Available'
            : 'Unavailable — session data remains visible here',
      ),
    ),
    const SizedBox(height: 24),
    const Text(
      'The app stays in the menu bar when its window is closed. Use the menu bar to reopen the dashboard or explicitly quit.',
    ),
  ];
  Widget _artworkPlaceholder() => const ColoredBox(
    color: Color(0xFF28231F),
    child: Center(child: Icon(Icons.album, size: 64)),
  );
  String _time(double seconds) =>
      '${seconds ~/ 60}:${(seconds.toInt() % 60).toString().padLeft(2, '0')}';
}
