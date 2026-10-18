import 'package:flutter/material.dart';
import '../../models/scrobbler_state.dart';
import '../../services/library_cache.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/album_art.dart';
import '../../widgets/page_heading.dart';
import '../library/library_api.dart';
import '../library/library_models.dart';
import '../library/library_widgets.dart';
import '../library/listening_heatmap.dart';

/// Lifetime Last.fm totals, this year's listening, and this day in past years.
class OverviewPage extends StatefulWidget {
  const OverviewPage({
    super.key,
    required this.api,
    required this.state,
    this.onOpenWrapped,
  });
  final ScrobblerApi api;
  final ScrobblerState? state;
  final VoidCallback? onOpenWrapped;
  @override
  State<OverviewPage> createState() => _OverviewPageState();
}

class _OverviewPageState extends State<OverviewPage> {
  Json? _year, _onThisDay;
  Object? _error;
  late DateTime _today;
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    LibraryCache.forApi(widget.api).addListener(_refresh);
    _load();
  }

  @override
  void didUpdateWidget(OverviewPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      LibraryCache.forApi(oldWidget.api).removeListener(_refresh);
      LibraryCache.forApi(widget.api).addListener(_refresh);
      _year = _onThisDay = null;
      _load();
    }
  }

  void _refresh() => _load();

  Future<void> _load({bool force = false}) async {
    final generation = ++_generation;
    final now = DateTime.now();
    _today = DateTime(now.year, now.month, now.day);
    final api = LibraryApi(widget.api);
    final cache = LibraryCache.forApi(widget.api);
    setState(() {
      _year ??= cache.peek('/library/wrapped/${_today.year}/');
      _onThisDay ??= cache.peek(LibraryApi.onThisDayPath(_today));
      _error = null;
    });
    try {
      final results = await Future.wait([
        api.wrapped(_today.year, force: force),
        api.onThisDay(_today, force: force),
      ]);
      if (!mounted || generation != _generation) return;
      setState(() {
        _year = results[0];
        _onThisDay = results[1];
      });
    } catch (error) {
      if (mounted && generation == _generation) setState(() => _error = error);
    }
  }

  @override
  void dispose() {
    LibraryCache.forApi(widget.api).removeListener(_refresh);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profile = widget.state?.profile;
    final year = _year;
    final onThisDay = _onThisDay;
    return ListView(
      padding: AppSpacing.page,
      children: [
        PageHeading(
          title: 'Overview',
          subtitle: profile == null
              ? 'Your Last.fm profile is unavailable. Check your credentials and connection.'
              : 'Last.fm · ${profile.name}',
          trailing: IconButton(
            tooltip: 'Refresh overview',
            onPressed: () => _load(force: true),
            icon: const Icon(Icons.refresh),
          ),
        ),
        if (profile != null) ...[
          const _SectionTitle('Lifetime on Last.fm'),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              StatTile(
                value: formatCountText(profile.playcount),
                label: 'Scrobbles',
              ),
              StatTile(
                value: formatCountText(profile.artists),
                label: 'Artists',
              ),
              StatTile(value: formatCountText(profile.albums), label: 'Albums'),
            ],
          ),
          const SizedBox(height: 36),
        ],
        if (_error != null && year == null)
          LibraryFailure(error: _error!, retry: () => _load(force: true))
        else if (year == null)
          const LinearProgressIndicator()
        else ...[
          _SectionTitle(
            '${_today.year} so far',
            trailing: widget.onOpenWrapped == null
                ? null
                : TextButton.icon(
                    onPressed: widget.onOpenWrapped,
                    icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                    label: const Text('Open Wrapped'),
                  ),
          ),
          _ThisYear(data: year, today: _today),
          const SizedBox(height: 36),
          _SectionTitle(
            'On this day',
            subtitle:
                '${formatMonth(_today.month)} ${_today.day} in earlier years',
          ),
          if (onThisDay != null)
            _OnThisDay(api: widget.api, data: onThisDay, today: _today),
        ],
        if (_error != null && year != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(
              'Showing saved results. Couldn’t refresh your library just now.',
              style: theme.textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title, {this.subtitle, this.trailing});
  final String title;
  final String? subtitle;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: theme.textTheme.titleLarge),
                if (subtitle != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(subtitle!, style: theme.textTheme.bodyMedium),
                  ),
              ],
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}

class _ThisYear extends StatelessWidget {
  const _ThisYear({required this.data, required this.today});
  final Json data;
  final DateTime today;
  @override
  Widget build(BuildContext context) {
    final daily = DailyCounts.fromWrapped(data);
    final elapsed = today.difference(DateTime(today.year)).inDays + 1;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LibraryStats(
          values: {
            'Scrobbles': number(data['total_scrobbles']),
            'Days listened': daily.daysListened,
            'Longest streak': daily.longestStreak,
          },
          notes: {
            'Days listened': 'of $elapsed so far',
            if (daily.longestStreak > 0)
              'Longest streak': daily.longestStreak == 1
                  ? 'day'
                  : 'days in a row',
          },
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: ScrobblerColors.of(context).surfaceRaised,
            borderRadius: AppRadii.largeAll,
          ),
          child: ListeningHeatmap(daily: daily, today: today),
        ),
      ],
    );
  }
}

class _OnThisDay extends StatelessWidget {
  const _OnThisDay({
    required this.api,
    required this.data,
    required this.today,
  });
  final ScrobblerApi api;
  final Json data;
  final DateTime today;
  @override
  Widget build(BuildContext context) {
    final years = records(data, 'years');
    if (years.isEmpty) {
      return Text(
        'Nothing recorded on ${formatMonth(today.month)} ${today.day} in earlier years yet.',
      );
    }
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 900
            ? 3
            : constraints.maxWidth >= 560
            ? 2
            : 1;
        final width = (constraints.maxWidth - 12 * (columns - 1)) / columns;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final year in years)
              SizedBox(
                width: width,
                child: _YearCard(api: api, data: year, today: today),
              ),
          ],
        );
      },
    );
  }
}

class _YearCard extends StatelessWidget {
  const _YearCard({required this.api, required this.data, required this.today});
  final ScrobblerApi api;
  final Json data;
  final DateTime today;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    final year = number(data['year']);
    final ago = today.year - year;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: colors.surfaceRaised,
        borderRadius: AppRadii.largeAll,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      ago == 1 ? '1 YEAR AGO' : '$ago YEARS AGO',
                      style: theme.textTheme.labelSmall,
                    ),
                    const SizedBox(height: 4),
                    Text('$year', style: theme.textTheme.headlineMedium),
                  ],
                ),
              ),
              Text(
                '${formatCount(number(data['total_scrobbles']))} scrobbles',
                style: AppFonts.numeric(theme.textTheme.bodySmall),
              ),
            ],
          ),
          const SizedBox(height: 14),
          for (final track in records(data, 'top_tracks'))
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                children: [
                  AlbumArt(
                    api: api,
                    artist: label(track['artist']),
                    album: label(track['album']),
                    size: 40,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          label(track['name']),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.titleMedium,
                        ),
                        Text(
                          label(track['artist']),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '×${formatCount(number(track['count']))}',
                    style: AppFonts.numeric(theme.textTheme.bodyMedium),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
