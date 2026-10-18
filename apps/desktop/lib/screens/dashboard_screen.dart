import 'package:flutter/material.dart';
import '../controllers/scrobbler_controller.dart';
import '../features/library/listening_history_page.dart';
import '../features/library/wrapped_page.dart';
import '../features/listening/listening_page.dart';
import '../features/ipod/ipod_page.dart';
import '../features/manual/manual_album_page.dart';
import '../features/overview/overview_page.dart';
import '../features/settings/settings_page.dart';
import '../theme/app_theme.dart';
import '../theme/format.dart';
import '../widgets/album_art.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

typedef _Destination = ({String label, IconData icon, String? section});

class _DashboardScreenState extends State<DashboardScreen> {
  int _page = 0;
  final Set<int> _visitedPages = {0};
  // A section names the group its first destination opens; Settings is
  // pinned to the bottom of the sidebar, outside the groups.
  static const List<_Destination> _destinations = [
    (label: 'Listening', icon: Icons.graphic_eq_rounded, section: 'Now'),
    (
      label: 'Overview',
      icon: Icons.space_dashboard_outlined,
      section: 'Library',
    ),
    (label: 'History', icon: Icons.history_rounded, section: null),
    (label: 'Wrapped', icon: Icons.auto_awesome_rounded, section: null),
    (label: 'Add a listen', icon: Icons.library_add_rounded, section: 'Import'),
    (label: 'iPod', icon: Icons.album_rounded, section: null),
    (label: 'Settings', icon: Icons.tune_rounded, section: null),
  ];
  static const _listeningPage = 0;
  static const _wrappedPage = 3;
  static const _ipodPage = 5;
  static const _settingsPage = 6;

  void _open(int page) {
    setState(() {
      _page = page;
      _visitedPages.add(page);
    });
  }

  Widget _content(int page) {
    final controller = widget.controller;
    return switch (page) {
      _listeningPage => ListeningPage(controller: controller),
      1 => OverviewPage(
        api: controller.api,
        state: controller.state,
        onOpenWrapped: () => _open(_wrappedPage),
      ),
      2 => ListeningHistoryPage(api: controller.api),
      _wrappedPage => WrappedPage(api: controller.api),
      4 => ManualAlbumPage(api: controller.api),
      _ipodPage => IpodPage(controller: controller),
      _ => SettingsPage(controller: controller),
    };
  }

  int _badge(int page) => switch (page) {
    _listeningPage => widget.controller.state?.pending.length ?? 0,
    _ipodPage => widget.controller.state?.ipod.pendingCount ?? 0,
    _ => 0,
  };

  Widget _navItem(int page, bool compact) {
    final destination = _destinations[page];
    return _NavItem(
      label: destination.label,
      icon: destination.icon,
      selected: page == _page,
      compact: compact,
      badge: _badge(page),
      onTap: () => _open(page),
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.controller,
    builder: (context, _) => LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 860;
        final controller = widget.controller;
        final theme = Theme.of(context);
        final scrobbling = controller.state?.scrobbleEnabled ?? false;
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        width: compact ? 76 : 196,
                        color: theme.colorScheme.surface,
                        child: Column(
                          children: [
                            Padding(
                              padding: EdgeInsets.symmetric(
                                horizontal: compact ? 14 : 16,
                                vertical: 18,
                              ),
                              child: Row(
                                children: [
                                  SizedBox.square(
                                    dimension: 40,
                                    child: Icon(
                                      Icons.graphic_eq_rounded,
                                      color: theme.colorScheme.primary,
                                    ),
                                  ),
                                  if (!compact) ...[
                                    const SizedBox(width: 12),
                                    Text(
                                      'Scrobbler',
                                      style: theme.textTheme.titleLarge
                                          ?.copyWith(letterSpacing: -.4),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                            Expanded(
                              child: ListView(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                ),
                                children: [
                                  for (var i = 0; i < _settingsPage; i++) ...[
                                    if (_destinations[i].section != null)
                                      _SectionLabel(
                                        _destinations[i].section!,
                                        compact: compact,
                                        first: i == 0,
                                      ),
                                    _navItem(i, compact),
                                  ],
                                ],
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                              ),
                              child: _navItem(_settingsPage, compact),
                            ),
                            _StatusChip(
                              connected: controller.connected,
                              library:
                                  controller.state?.databaseAvailable == true,
                              compact: compact,
                            ),
                          ],
                        ),
                      ),
                      Expanded(
                        child: Column(
                          children: [
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 28,
                                vertical: 12,
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      _destinations[_page].label.toUpperCase(),
                                      style: theme.textTheme.labelSmall,
                                    ),
                                  ),
                                  Text(
                                    scrobbling ? 'Scrobbling' : 'Paused',
                                    style: theme.textTheme.labelLarge?.copyWith(
                                      color: scrobbling
                                          ? null
                                          : ScrobblerColors.of(
                                              context,
                                            ).textMuted,
                                    ),
                                  ),
                                  const SizedBox(width: 10),
                                  Tooltip(
                                    message: 'Enable or pause scrobbling',
                                    child: Switch(
                                      value: scrobbling,
                                      onChanged:
                                          controller.connected &&
                                              !controller.busy
                                          ? controller.setScrobbling
                                          : null,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            if (controller.error != null ||
                                controller.notice != null)
                              Container(
                                width: double.infinity,
                                color: theme.colorScheme.primaryContainer,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 28,
                                  vertical: 12,
                                ),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        controller.error ?? controller.notice!,
                                      ),
                                    ),
                                    if (controller.error == null &&
                                        controller.noticeOpensIpod &&
                                        _page != _ipodPage)
                                      TextButton(
                                        onPressed: () => _open(_ipodPage),
                                        child: const Text('Review'),
                                      ),
                                  ],
                                ),
                              ),
                            Expanded(
                              child: IndexedStack(
                                index: _page,
                                children: [
                                  for (var i = 0; i < _destinations.length; i++)
                                    TickerMode(
                                      enabled: i == _page,
                                      child: _visitedPages.contains(i)
                                          ? _content(i)
                                          : const SizedBox.shrink(),
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                _PlayerBar(controller: controller),
              ],
            ),
          ),
        );
      },
    ),
  );
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text, {required this.compact, required this.first});
  final String text;
  final bool compact, first;
  @override
  Widget build(BuildContext context) => compact
      ? Padding(
          padding: EdgeInsets.fromLTRB(14, first ? 0 : 6, 14, 8),
          child: first ? null : const Divider(),
        )
      : Padding(
          padding: EdgeInsets.fromLTRB(16, first ? 4 : 18, 16, 8),
          child: Text(
            text.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: ScrobblerColors.of(context).textFaint,
            ),
          ),
        );
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.selected,
    required this.compact,
    required this.badge,
    required this.onTap,
  });
  final String label;
  final IconData icon;
  final bool selected, compact;
  final int badge;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = selected
        ? theme.colorScheme.primary
        : theme.colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Tooltip(
        message: compact ? label : '',
        child: Material(
          color: selected
              ? theme.colorScheme.primary.withValues(alpha: .08)
              : Colors.transparent,
          borderRadius: AppRadii.smallAll,
          child: InkWell(
            borderRadius: AppRadii.smallAll,
            onTap: onTap,
            child: Padding(
              padding: EdgeInsets.symmetric(
                horizontal: compact ? 14 : 16,
                vertical: 10,
              ),
              child: Row(
                children: [
                  Badge(
                    isLabelVisible: badge > 0,
                    label: Text(formatCount(badge)),
                    child: Icon(icon, size: 22, color: color),
                  ),
                  if (!compact) ...[
                    const SizedBox(width: 13),
                    Text(
                      label,
                      style: TextStyle(
                        fontWeight: selected
                            ? FontWeight.w700
                            : FontWeight.w400,
                        color: color,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Backend connection and library availability in one place.
class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.connected,
    required this.library,
    required this.compact,
  });
  final bool connected, library;
  final bool compact;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    final healthy = connected && library;
    final summary = !connected
        ? 'Reconnecting'
        : library
        ? 'Connected · Library'
        : 'Connected · No library';
    final detail = !connected
        ? 'Reconnecting to the scrobbler backend'
        : library
        ? 'Backend connected; History, Wrapped, and Overview use your synced library'
        : 'Backend connected; your history database is unavailable';
    final dot = Icon(
      healthy ? Icons.check_circle_rounded : Icons.error_outline_rounded,
      size: 14,
      color: healthy ? colors.success : colors.warning,
    );
    return Tooltip(
      message: detail,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 18),
        child: compact
            ? dot
            : Row(
                children: [
                  dot,
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      summary,
                      style: theme.textTheme.bodySmall,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _PlayerBar extends StatelessWidget {
  const _PlayerBar({required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final state = controller.state;
    final track = state?.currentTrack;
    return ArtworkTint(
      api: controller.api,
      artist: track?.artist ?? '',
      album: track?.album ?? '',
      url: state?.artworkUrl,
      builder: (context, tint) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color.alphaBlend(
                tint.withValues(alpha: .12),
                theme.colorScheme.surface,
              ),
              theme.colorScheme.surface,
            ],
            stops: const [0, .5],
          ),
          border: Border(top: BorderSide(color: tint.withValues(alpha: .45))),
        ),
        child: Row(
          children: [
            AlbumArt(
              api: controller.api,
              artist: track?.artist ?? '',
              album: track?.album ?? '',
              url: state?.artworkUrl,
              size: 44,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    track?.name ?? 'No track selected',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.titleMedium,
                  ),
                  Text(
                    track?.artist ?? 'Apple Music + Spotify',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            PlaybackControls(controller: controller),
            if (MediaQuery.sizeOf(context).width > 700) ...[
              const SizedBox(width: 28),
              Text(
                '${formatCount(state?.pending.length ?? 0)} queued',
                style: AppFonts.numeric(theme.textTheme.labelLarge),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
