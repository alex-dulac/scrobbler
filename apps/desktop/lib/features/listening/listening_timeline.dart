import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Annual counts share a chronological axis, but each row has its own scale.
class ListeningTimeline extends StatelessWidget {
  const ListeningTimeline({
    super.key,
    required this.track,
    required this.album,
    required this.artist,
    this.currentYear,
  });

  final List<dynamic> track, artist;
  final List<dynamic>? album;
  final int? currentYear;

  static Map<int, int> annualCounts(List<dynamic> rows) {
    final result = <int, int>{};
    for (final row in rows) {
      if (row is! Map) continue;
      final year = int.tryParse('${row['year']}');
      final count = int.tryParse('${row['count']}');
      if (year != null && count != null && count >= 0) {
        result[year] = (result[year] ?? 0) + count;
      }
    }
    return result;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final now = currentYear ?? DateTime.now().year;
    final series = [
      ('Track', annualCounts(track), theme.colorScheme.primary),
      if (album != null)
        ('Album', annualCounts(album!), theme.colorScheme.secondary),
      ('Artist', annualCounts(artist), theme.colorScheme.tertiary),
    ];
    final recordedYears = series.expand((row) => row.$2.keys).toList();
    if (recordedYears.isEmpty) return const SizedBox.shrink();
    final first = recordedYears.reduce(math.min);
    final last = math.max(now, recordedYears.reduce(math.max));
    final years = [for (var year = first; year <= last; year++) year];
    return Container(
      padding: const EdgeInsets.all(16),
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outline),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Listening over time', style: theme.textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Annual scrobbles · each row has its own scale · $now is year to date',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (context, constraints) {
              const labelWidth = 110.0;
              final width = math.max(
                constraints.maxWidth,
                labelWidth + years.length * 52.0,
              );
              return SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SizedBox(
                  width: width,
                  child: Column(
                    children: [
                      for (final row in series)
                        _AnnualRow(
                          label: row.$1,
                          counts: row.$2,
                          color: row.$3,
                          years: years,
                        ),
                      Row(
                        children: [
                          const SizedBox(width: labelWidth),
                          for (final year in years)
                            Expanded(
                              child: Text(
                                '$year',
                                textAlign: TextAlign.center,
                                style: theme.textTheme.labelSmall,
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _AnnualRow extends StatelessWidget {
  const _AnnualRow({
    required this.label,
    required this.counts,
    required this.color,
    required this.years,
  });
  final String label;
  final Map<int, int> counts;
  final Color color;
  final List<int> years;

  @override
  Widget build(BuildContext context) {
    final peak = counts.values.fold<int>(0, math.max);
    final peakYears = years
        .where((year) => peak > 0 && counts[year] == peak)
        .toList();
    final peakLabel = peakYears.length == 1
        ? 'Peak ${peakYears.single}'
        : peakYears.isEmpty
        ? 'No listens'
        : '${peakYears.length} peak years';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          SizedBox(
            width: 110,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 5),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(color: color, fontWeight: FontWeight.w700),
                  ),
                  Text(peakLabel, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
          for (final year in years)
            Expanded(
              child: Tooltip(
                message: '$label · $year: ${counts[year] ?? 0} scrobbles',
                child: Semantics(
                  label: '$label, $year, ${counts[year] ?? 0} scrobbles',
                  excludeSemantics: true,
                  child: SizedBox(
                    height: 58,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Text(
                          '${counts[year] ?? 0}',
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const SizedBox(height: 4),
                        Container(
                          height: peak == 0
                              ? 2
                              : math.max(2, (counts[year] ?? 0) / peak * 36),
                          margin: const EdgeInsets.symmetric(horizontal: 5),
                          decoration: BoxDecoration(
                            color: (counts[year] ?? 0) == 0
                                ? Theme.of(context).colorScheme.outline
                                : color.withValues(
                                    alpha: counts[year] == peak ? 1 : .55,
                                  ),
                            borderRadius: const BorderRadius.vertical(
                              top: Radius.circular(3),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
