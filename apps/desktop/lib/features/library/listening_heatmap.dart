import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import 'library_models.dart';

/// Daily scrobble counts for one calendar year, keyed by local date.
class DailyCounts {
  DailyCounts(this.year, this.counts);

  factory DailyCounts.fromWrapped(Json wrapped) {
    final counts = <DateTime, int>{};
    for (final row in records(wrapped, 'daily')) {
      final date = DateTime.tryParse(label(row['date']));
      if (date != null) {
        counts[DateTime(date.year, date.month, date.day)] = number(
          row['count'],
        );
      }
    }
    return DailyCounts(number(wrapped['year']), counts);
  }

  final int year;
  final Map<DateTime, int> counts;

  int operator [](DateTime day) =>
      counts[DateTime(day.year, day.month, day.day)] ?? 0;

  int get daysListened => counts.values.where((count) => count > 0).length;

  int get longestStreak {
    var longest = 0, current = 0;
    for (
      var day = DateTime(year);
      day.year == year;
      day = DateTime(day.year, day.month, day.day + 1)
    ) {
      current = this[day] > 0 ? current + 1 : 0;
      longest = math.max(longest, current);
    }
    return longest;
  }

  MapEntry<DateTime, int>? get busiestDay => counts.entries
      .where((entry) => entry.value > 0)
      .fold<MapEntry<DateTime, int>?>(
        null,
        (best, entry) =>
            best == null || entry.value > best.value ? entry : best,
      );
}

/// A calendar heatmap: one column per week (Monday first), one hue whose
/// brightness rises with the day's scrobbles.
class ListeningHeatmap extends StatelessWidget {
  const ListeningHeatmap({super.key, required this.daily, this.today});
  final DailyCounts daily;

  /// Days after this are left blank; defaults to the current date.
  final DateTime? today;

  // Sequential ramp on the dark surface: dim plum to the lilac accent.
  static const ramp = [
    Color(0xFF4A3D73),
    Color(0xFF6E58A8),
    Color(0xFF9A80D8),
    Color(0xFFC4A7FF),
  ];
  static const _gap = 2.0;
  static const _dayLabelWidth = 28.0;
  static const _monthLabelHeight = 18.0;

  /// Quartile thresholds over listening days, so one huge day can't flatten
  /// the rest of the year into the lowest step.
  static List<int> thresholds(Iterable<int> counts) {
    final values = counts.where((count) => count > 0).toList()..sort();
    if (values.isEmpty) return const [1, 1, 1];
    int at(double q) => values[((values.length - 1) * q).round()];
    return [at(.25), at(.5), at(.75)];
  }

  static int level(int count, List<int> thresholds) {
    if (count <= 0) return 0;
    var step = 1;
    for (final threshold in thresholds) {
      if (count > threshold) step++;
    }
    return step;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    final now = today ?? DateTime.now();
    final last = DateTime(now.year, now.month, now.day);
    final first = DateTime(daily.year);
    final offset = first.weekday - 1;
    final days = DateTime(daily.year + 1).difference(first).inDays;
    final weeks = ((days + offset) / 7).ceil();
    final limits = thresholds(daily.counts.values);
    final busiest = daily.busiestDay;
    return Semantics(
      label:
          '${daily.year} listening calendar: ${daily.daysListened} days with listens'
          '${busiest == null ? '' : ', busiest ${formatDate(busiest.key)} with ${formatCount(busiest.value)} scrobbles'}',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final pitch = math.min(
            18.0,
            (constraints.maxWidth - _dayLabelWidth) / weeks,
          );
          final cell = math.max(4.0, pitch - _gap);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: _monthLabelHeight,
                child: Stack(
                  children: [
                    for (var month = 1; month <= 12; month++)
                      Positioned(
                        left:
                            _dayLabelWidth +
                            ((DateTime(
                                          daily.year,
                                          month,
                                        ).difference(first).inDays +
                                        offset) ~/
                                    7) *
                                pitch,
                        child: Text(
                          formatMonth(month),
                          style: theme.textTheme.labelSmall,
                        ),
                      ),
                  ],
                ),
              ),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: _dayLabelWidth,
                    child: Column(
                      children: [
                        for (final day in const [
                          'Mon',
                          '',
                          'Wed',
                          '',
                          'Fri',
                          '',
                          '',
                        ])
                          SizedBox(
                            height: pitch,
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: Text(
                                day,
                                style: theme.textTheme.labelSmall,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  for (var week = 0; week < weeks; week++)
                    Column(
                      children: [
                        for (var weekday = 0; weekday < 7; weekday++)
                          _cell(
                            context,
                            DateTime(
                              daily.year,
                              1,
                              1 + week * 7 + weekday - offset,
                            ),
                            last,
                            limits,
                            colors,
                            cell,
                          ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text('Less', style: theme.textTheme.labelSmall),
                  const SizedBox(width: 6),
                  for (final color in [colors.surfaceHighest, ...ramp])
                    Container(
                      width: 10,
                      height: 10,
                      margin: const EdgeInsets.only(right: _gap),
                      decoration: BoxDecoration(
                        color: color,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  const SizedBox(width: 4),
                  Text('More', style: theme.textTheme.labelSmall),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _cell(
    BuildContext context,
    DateTime day,
    DateTime last,
    List<int> limits,
    ScrobblerColors colors,
    double size,
  ) {
    final blank = SizedBox.square(dimension: size + _gap);
    if (day.year != daily.year || day.isAfter(last)) return blank;
    final count = daily[day];
    final step = level(count, limits);
    return Tooltip(
      message:
          '${formatDate(day)} · ${count == 0 ? 'No' : formatCount(count)} scrobble${count == 1 ? '' : 's'}',
      waitDuration: const Duration(milliseconds: 150),
      child: Container(
        width: size,
        height: size,
        margin: const EdgeInsets.only(right: _gap, bottom: _gap),
        decoration: BoxDecoration(
          color: step == 0 ? colors.surfaceHighest : ramp[step - 1],
          borderRadius: BorderRadius.circular(math.min(3, size / 4)),
        ),
      ),
    );
  }
}
