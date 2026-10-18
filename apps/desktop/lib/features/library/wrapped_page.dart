import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/page_heading.dart';
import 'artist_detail_page.dart';
import 'library_api.dart';
import 'library_models.dart';
import 'library_widgets.dart';
import 'listening_heatmap.dart';
import '../../widgets/library_refresh.dart';

class WrappedPage extends StatefulWidget {
  const WrappedPage({super.key, required this.api});
  final ScrobblerApi api;
  @override
  State<WrappedPage> createState() => _WrappedPageState();
}

class _WrappedPageState extends State<WrappedPage>
    with LibraryRefresh<WrappedPage> {
  List<int> _years = [];
  int? _year;
  Json? _data;
  Object? _error;
  bool _loading = true;
  int _generation = 0;
  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(WrappedPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      _data = null;
      _years = [];
      _year = null;
      _load();
    }
  }

  @override
  ScrobblerApi get libraryApi => widget.api;

  @override
  void reloadLibrary() => _load();

  Future<void> _load({int? year, bool force = false}) async {
    if (year != null && year != _year) {
      _year = year;
      _data = LibraryCache.forApi(widget.api).peek('/library/wrapped/$year/');
    }
    final generation = ++_generation;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = LibraryApi(widget.api);
      final years = await api.years(force: force);
      final preferred = year ?? _year;
      final selected = years.contains(preferred)
          ? preferred
          : (years.isEmpty ? null : years.first);
      final data = selected == null
          ? null
          : await api.wrapped(selected, force: force);
      if (mounted && generation == _generation) {
        setState(() {
          _years = years;
          _year = selected;
          _data = data;
          _loading = false;
        });
      }
    } catch (error) {
      if (mounted && generation == _generation) {
        setState(() {
          _error = error;
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: AppSpacing.page,
    children: [
      const PageHeading(
        title: 'Yearly listening summary',
        subtitle:
            'Totals, monthly activity, and rankings from the synced library.',
      ),
      Row(
        children: [
          if (_years.isNotEmpty)
            DropdownButton<int>(
              value: _year,
              items: _years
                  .map(
                    (year) =>
                        DropdownMenuItem(value: year, child: Text('$year')),
                  )
                  .toList(),
              onChanged: (year) {
                if (year != null) _load(year: year);
              },
            ),
          const Spacer(),
          IconButton(
            tooltip: 'Refresh year',
            onPressed: _loading ? null : () => _load(force: true),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      const SizedBox(height: 12),
      if (_loading && _data == null) const LinearProgressIndicator(),
      if (_error != null)
        LibraryFailure(error: _error!, retry: () => _load(force: true)),
      if (!_loading && _error == null && _years.isEmpty)
        const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Text('No listening history has been synced yet.'),
        ),
      if (_data != null) ..._summary(context, _data!),
    ],
  );

  List<Widget> _summary(BuildContext context, Json data) {
    final theme = Theme.of(context);
    final year = number(data['year']);
    final now = DateTime.now();
    final total = number(data['total_scrobbles']);
    final previous = number(data['previous_total_scrobbles']);
    final hasPrevious = previous > 0;
    final daily = DailyCounts.fromWrapped(data);
    final busiest = daily.busiestDay;
    // A year in progress can't be compared fairly with a whole one.
    final change = hasPrevious && year < now.year
        ? ((total - previous) / previous * 100).round()
        : null;
    return [
      LibraryStats(
        values: {
          'Scrobbles': total,
          'Artists': number(data['unique_artists']),
          'Albums': number(data['unique_albums']),
          'Tracks': number(data['unique_tracks']),
          'Days listened': daily.daysListened,
          'Longest streak': daily.longestStreak,
        },
        notes: {
          if (change != null)
            'Scrobbles':
                '${change >= 0 ? '+' : '−'}${change.abs()}% vs ${year - 1}',
          if (daily.longestStreak > 0)
            'Longest streak': daily.longestStreak == 1
                ? 'day'
                : 'days in a row',
        },
      ),
      const SizedBox(height: 36),
      Text('Monthly scrobbles', style: theme.textTheme.titleLarge),
      const SizedBox(height: 24),
      _MonthlyChart(
        months: records(data, 'monthly'),
        currentMonth: year == now.year ? now.month : null,
      ),
      const SizedBox(height: 36),
      Text('Every day of $year', style: theme.textTheme.titleLarge),
      const SizedBox(height: 4),
      Text(
        busiest == null
            ? 'No listening recorded this year.'
            : 'Busiest day: ${formatDate(busiest.key)} with ${formatCount(busiest.value)} scrobbles.',
        style: theme.textTheme.bodyMedium,
      ),
      const SizedBox(height: 16),
      ListeningHeatmap(daily: daily),
      LibraryRanking(
        title: 'Top artists',
        showMovement: hasPrevious,
        items: records(data, 'top_artists'),
        onSelect: (artist) => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => ArtistDetailPage(api: widget.api, artist: artist),
          ),
        ),
      ),
      LibraryRanking(
        title: 'Top albums',
        showMovement: hasPrevious,
        items: records(data, 'top_albums'),
      ),
      LibraryRanking(
        title: 'Top tracks',
        showMovement: hasPrevious,
        items: records(data, 'top_tracks'),
      ),
    ];
  }
}

/// One series, so one hue. The peak is labelled directly; a month still in
/// progress is drawn lighter so it doesn't read as a drop.
class _MonthlyChart extends StatelessWidget {
  const _MonthlyChart({required this.months, this.currentMonth});
  final List<Json> months;
  final int? currentMonth;
  static const _plotHeight = 140.0;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    final counts = {
      for (final row in months) number(row['month']): number(row['count']),
    };
    final maximum = counts.values.fold<int>(0, (a, b) => a > b ? a : b);
    final peak = maximum == 0
        ? null
        : counts.entries.firstWhere((entry) => entry.value == maximum).key;
    return SizedBox(
      // Room for the peak's value label above and month labels below.
      height: _plotHeight + 64,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(12, (index) {
          final month = index + 1;
          final count = counts[month] ?? 0;
          final future = currentMonth != null && month > currentMonth!;
          final inProgress = month == currentMonth;
          final description =
              '${formatMonth(month)}: ${formatCount(count)} scrobbles${inProgress ? ' so far' : ''}';
          return Expanded(
            child: Tooltip(
              message: description,
              child: Semantics(
                label: description,
                excludeSemantics: true,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (month == peak)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Text(
                            formatCount(count),
                            style: AppFonts.numeric(theme.textTheme.labelLarge),
                          ),
                        ),
                      Container(
                        height: future || count == 0
                            ? 2
                            : math.max(2, _plotHeight * count / maximum),
                        decoration: BoxDecoration(
                          color: future || count == 0
                              ? colors.outline
                              : theme.colorScheme.primary.withValues(
                                  alpha: inProgress ? .45 : 1,
                                ),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        formatMonth(month),
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: inProgress
                              ? theme.colorScheme.onSurface
                              : null,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
