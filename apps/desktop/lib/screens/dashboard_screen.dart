import 'package:flutter/material.dart';
import '../controllers/scrobbler_controller.dart';
import '../services/library_cache.dart';
import '../features/library/listening_history_page.dart';
import '../features/library/wrapped_page.dart';
import '../features/listening/listening_page.dart';
import '../features/listening/collection_pages.dart';
import '../features/manual/manual_album_page.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  int _page = 0;
  final Set<int> _visitedPages = {0};
  static const _labels = [
    'Listening',
    'History',
    'Wrapped',
    'Add a listen',
    'Session',
    'Profile',
    'Settings',
  ];
  static const _icons = [
    Icons.graphic_eq_rounded,
    Icons.history_rounded,
    Icons.auto_awesome_rounded,
    Icons.library_add_rounded,
    Icons.queue_music_rounded,
    Icons.person_outline_rounded,
    Icons.tune_rounded,
  ];
  Widget _content(int page) {
    final controller = widget.controller;
    return switch (page) {
      0 => ListeningPage(controller: controller),
      1 => ListeningHistoryPage(api: controller.api),
      2 => WrappedPage(api: controller.api),
      3 => ManualAlbumPage(api: controller.api),
      4 => SessionPage(state: controller.state),
      5 => ProfilePage(state: controller.state),
      _ => SettingsPage(controller: controller),
    };
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.controller,
    builder: (context, _) => LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 860;
        final controller = widget.controller;
        final theme = Theme.of(context);
        return Scaffold(
          body: SafeArea(
            child: Column(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Container(
                        width: compact ? 76 : 184,
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
                                  Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: Colors.transparent,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Icon(
                                      Icons.graphic_eq_rounded,
                                      color: theme.colorScheme.primary,
                                    ),
                                  ),
                                  if (!compact) ...[
                                    const SizedBox(width: 12),
                                    Text(
                                      'Scrobbler',
                                      style: theme.textTheme.titleLarge,
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
                                  for (var i = 0; i < _labels.length; i++)
                                    Padding(
                                      padding: const EdgeInsets.only(bottom: 6),
                                      child: Tooltip(
                                        message: compact ? _labels[i] : '',
                                        child: Material(
                                          color: i == _page
                                              ? theme.colorScheme.primary
                                                    .withValues(alpha: .08)
                                              : Colors.transparent,
                                          borderRadius: BorderRadius.circular(
                                            12,
                                          ),
                                          child: InkWell(
                                            borderRadius: BorderRadius.circular(
                                              12,
                                            ),
                                            onTap: () {
                                              setState(() {
                                                _page = i;
                                                _visitedPages.add(i);
                                              });
                                              LibraryCache.forApi(
                                                controller.api,
                                              ).revalidate();
                                            },
                                            child: Padding(
                                              padding: EdgeInsets.symmetric(
                                                horizontal: compact ? 14 : 16,
                                                vertical: 12,
                                              ),
                                              child: Row(
                                                children: [
                                                  Icon(
                                                    _icons[i],
                                                    size: 22,
                                                    color: i == _page
                                                        ? theme
                                                              .colorScheme
                                                              .primary
                                                        : theme
                                                              .colorScheme
                                                              .onSurfaceVariant,
                                                  ),
                                                  if (!compact) ...[
                                                    const SizedBox(width: 13),
                                                    Text(
                                                      _labels[i],
                                                      style: TextStyle(
                                                        fontWeight: i == _page
                                                            ? FontWeight.w700
                                                            : FontWeight.w400,
                                                        color: i == _page
                                                            ? theme
                                                                  .colorScheme
                                                                  .primary
                                                            : theme
                                                                  .colorScheme
                                                                  .onSurfaceVariant,
                                                      ),
                                                    ),
                                                  ],
                                                ],
                                              ),
                                            ),
                                          ),
                                        ),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.all(18),
                              child: compact
                                  ? Icon(
                                      Icons.storage_rounded,
                                      color: theme.colorScheme.secondary,
                                    )
                                  : Text(
                                      controller.state?.databaseAvailable ==
                                              true
                                          ? 'Library connected'
                                          : 'Library unavailable',
                                      style: theme.textTheme.bodySmall
                                          ?.copyWith(
                                            color: theme.colorScheme.secondary,
                                          ),
                                    ),
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
                                vertical: 16,
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      _labels[_page].toUpperCase(),
                                      style: theme.textTheme.labelSmall,
                                    ),
                                  ),
                                  Icon(
                                    Icons.circle,
                                    size: 7,
                                    color: controller.connected
                                        ? theme.colorScheme.secondary
                                        : theme.colorScheme.tertiary,
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    controller.connected
                                        ? 'Connected'
                                        : 'Reconnecting',
                                    style: theme.textTheme.labelLarge,
                                  ),
                                  const SizedBox(width: 12),
                                  Tooltip(
                                    message: 'Enable or pause scrobbling',
                                    child: Switch(
                                      value:
                                          controller.state?.scrobbleEnabled ??
                                          false,
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
                                child: Text(
                                  controller.error ?? controller.notice!,
                                ),
                              ),
                            Expanded(
                              child: IndexedStack(
                                index: _page,
                                children: [
                                  for (var i = 0; i < _labels.length; i++)
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

class _PlayerBar extends StatelessWidget {
  const _PlayerBar({required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final track = controller.state?.currentTrack;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(top: BorderSide(color: theme.colorScheme.outline)),
      ),
      child: Row(
        children: [
          Icon(Icons.album_rounded, color: theme.colorScheme.primary, size: 32),
          const SizedBox(width: 16),
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
              '${controller.state?.pending.length ?? 0} queued',
              style: theme.textTheme.labelLarge,
            ),
          ],
        ],
      ),
    );
  }
}
