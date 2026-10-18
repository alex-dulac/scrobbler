import 'dart:async';
import 'package:flutter/material.dart';
import 'library_models.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';

class LibraryFailure extends StatelessWidget {
  const LibraryFailure({super.key, required this.error, required this.retry});
  final Object error;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) {
    final unavailable =
        error is ApiException && (error as ApiException).statusCode == 503;
    final slow = error is TimeoutException;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.cloud_off_outlined, size: 32),
          const SizedBox(height: 16),
          Text(
            unavailable
                ? 'Your listening library is unavailable'
                : slow
                ? 'Your listening library is taking too long'
                : 'Couldn’t load your listening library',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            unavailable
                ? 'Connect your history database and restart the app, then try again. Live scrobbling and queued listens remain available.'
                : slow
                ? 'The history database didn’t answer in time. It may be busy or the connection slow; try again in a moment.'
                : 'Check the backend connection, then try again.',
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: retry,
            icon: const Icon(Icons.refresh),
            label: const Text('Try again'),
          ),
        ],
      ),
    );
  }
}

class StatTile extends StatelessWidget {
  const StatTile({
    super.key,
    required this.value,
    required this.label,
    this.note,
  });
  final String value, label;
  final String? note;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      constraints: const BoxConstraints(minWidth: 125),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ScrobblerColors.of(context).surfaceRaised,
        borderRadius: AppRadii.largeAll,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(value, style: theme.textTheme.headlineLarge),
          const SizedBox(height: 6),
          Text(label.toUpperCase(), style: theme.textTheme.labelSmall),
          if (note != null) ...[
            const SizedBox(height: 4),
            Text(note!, style: AppFonts.numeric(theme.textTheme.bodySmall)),
          ],
        ],
      ),
    );
  }
}

class LibraryStats extends StatelessWidget {
  const LibraryStats({super.key, required this.values, this.notes = const {}});
  final Map<String, int> values;
  final Map<String, String> notes;
  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 12,
    runSpacing: 12,
    children: values.entries
        .map(
          (entry) => StatTile(
            value: formatCount(entry.value),
            label: entry.key,
            note: notes[entry.key],
          ),
        )
        .toList(),
  );
}

/// Change in position since the previous year's chart.
class RankMovement extends StatelessWidget {
  const RankMovement({super.key, required this.rank, this.previousRank});
  final int rank;
  final int? previousRank;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final style = AppFonts.numeric(theme.textTheme.labelSmall);
    final previous = previousRank;
    if (previous == null) {
      return Tooltip(
        message: 'New to the chart this year',
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
          decoration: BoxDecoration(
            border: Border.all(color: theme.colorScheme.primary),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            'NEW',
            style: style?.copyWith(color: theme.colorScheme.onSurface),
          ),
        ),
      );
    }
    final change = previous - rank;
    return Tooltip(
      message: 'Last year: #$previous',
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            change > 0
                ? Icons.arrow_upward_rounded
                : change < 0
                ? Icons.arrow_downward_rounded
                : Icons.remove_rounded,
            size: 12,
            color: ScrobblerColors.of(context).textMuted,
          ),
          if (change != 0) Text('${change.abs()}', style: style),
        ],
      ),
    );
  }
}

class LibraryRanking extends StatelessWidget {
  const LibraryRanking({
    super.key,
    required this.title,
    required this.items,
    this.onSelect,
    this.showMovement = false,
  });
  final String title;
  final List<Json> items;
  final void Function(String)? onSelect;

  /// Items carry `previous_rank`; shown when there is a previous year to compare.
  final bool showMovement;
  @override
  Widget build(BuildContext context) {
    final maximum = items.fold<int>(
      1,
      (value, item) =>
          number(item['count']) > value ? number(item['count']) : value,
    );
    return Padding(
      padding: const EdgeInsets.only(top: 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 14),
          if (items.isEmpty) const Text('No listening data yet.'),
          ...items.take(10).toList().asMap().entries.map((entry) {
            final item = entry.value;
            final name = label(item['name']);
            return InkWell(
              onTap: onSelect == null ? null : () => onSelect!(name),
              borderRadius: AppRadii.smallAll,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  vertical: 10,
                  horizontal: 4,
                ),
                child: Row(
                  children: [
                    SizedBox(
                      width: 32,
                      child: Text(
                        '${entry.key + 1}'.padLeft(2, '0'),
                        style:
                            AppFonts.numeric(
                              Theme.of(context).textTheme.bodyMedium,
                            )?.copyWith(
                              color: Theme.of(context).colorScheme.primary,
                            ),
                      ),
                    ),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (label(item['artist']).isNotEmpty)
                            Text(
                              label(item['artist']),
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          const SizedBox(height: 7),
                          LinearProgressIndicator(
                            value: number(item['count']) / maximum,
                            backgroundColor: Theme.of(
                              context,
                            ).colorScheme.outline.withValues(alpha: .4),
                            minHeight: 3,
                            borderRadius: AppRadii.smallAll,
                          ),
                        ],
                      ),
                    ),
                    if (showMovement)
                      SizedBox(
                        width: 52,
                        child: Align(
                          alignment: Alignment.centerRight,
                          child: RankMovement(
                            rank: entry.key + 1,
                            previousRank: (item['previous_rank'] as num?)
                                ?.toInt(),
                          ),
                        ),
                      ),
                    const SizedBox(width: 16),
                    Text(
                      formatCount(number(item['count'])),
                      style: AppFonts.numeric(
                        Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
