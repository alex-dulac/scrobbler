import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import 'artist_detail_page.dart';
import 'library_api.dart';
import 'library_models.dart';
import 'library_widgets.dart';

class WrappedPage extends StatefulWidget {
  const WrappedPage({super.key, required this.api});
  final ScrobblerApi api;
  @override
  State<WrappedPage> createState() => _WrappedPageState();
}

class _WrappedPageState extends State<WrappedPage> {
  List<int> _years = [];
  int? _year;
  Json? _data;
  Object? _error;
  bool _loading = true;
  int _generation = 0;
  @override
  void initState() {
    super.initState();
    LibraryCache.forApi(widget.api).addListener(_refresh);
    _load();
  }

  @override
  void didUpdateWidget(WrappedPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      LibraryCache.forApi(oldWidget.api).removeListener(_refresh);
      LibraryCache.forApi(widget.api).addListener(_refresh);
      _data = null;
      _years = [];
      _year = null;
      _load();
    }
  }

  void _refresh() => _load();

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
  void dispose() {
    LibraryCache.forApi(widget.api).removeListener(_refresh);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(32),
    children: [
      const LibraryHeading(
        eyebrow: 'WRAPPED',
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
      if (_data != null) ...[
        LibraryStats(
          values: {
            'Scrobbles': number(_data!['total_scrobbles']),
            'Artists': number(_data!['unique_artists']),
            'Albums': number(_data!['unique_albums']),
            'Tracks': number(_data!['unique_tracks']),
          },
        ),
        const SizedBox(height: 32),
        Text(
          'Monthly scrobbles',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 24),
        _MonthlyChart(months: records(_data!, 'monthly')),
        LibraryRanking(
          title: 'Top artists',
          items: records(_data!, 'top_artists'),
          onSelect: (artist) => Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => ArtistDetailPage(api: widget.api, artist: artist),
            ),
          ),
        ),
        LibraryRanking(
          title: 'Top albums',
          items: records(_data!, 'top_albums'),
        ),
        LibraryRanking(
          title: 'Top tracks',
          items: records(_data!, 'top_tracks'),
        ),
      ],
    ],
  );
}

class _MonthlyChart extends StatelessWidget {
  const _MonthlyChart({required this.months});
  final List<Json> months;
  @override
  Widget build(BuildContext context) {
    final counts = {
      for (final row in months) number(row['month']): number(row['count']),
    };
    final maximum = counts.values.fold<int>(1, (a, b) => a > b ? a : b);
    const names = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return SizedBox(
      height: 160,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: List.generate(12, (index) {
          final count = counts[index + 1] ?? 0;
          return Expanded(
            child: Tooltip(
              message: '${names[index]}: $count scrobbles',
              child: Semantics(
                label: '${names[index]}: $count scrobbles',
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 3),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      Container(
                        height: count == 0 ? 2 : 120 * count / maximum,
                        decoration: BoxDecoration(
                          color: [
                            Theme.of(context).colorScheme.primary,
                            Theme.of(context).colorScheme.secondary,
                            Theme.of(context).colorScheme.tertiary,
                          ][index % 3].withValues(alpha: count == 0 ? .15 : .8),
                          borderRadius: BorderRadius.circular(5),
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        names[index],
                        style: Theme.of(context).textTheme.labelSmall,
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
