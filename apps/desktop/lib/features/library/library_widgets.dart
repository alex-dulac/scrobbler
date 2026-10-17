import 'package:flutter/material.dart';
import 'library_models.dart';
import '../../services/scrobbler_api.dart';

class LibraryFailure extends StatelessWidget {
  const LibraryFailure({super.key, required this.error, required this.retry});
  final Object error;
  final VoidCallback retry;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 32),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.cloud_off_outlined, size: 32),
        const SizedBox(height: 16),
        Text(
          error is ApiException && (error as ApiException).statusCode == 503
              ? 'Your listening library is unavailable'
              : 'Couldn’t load your listening library',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        Text(
          error is ApiException && (error as ApiException).statusCode == 503
              ? 'Connect your history database and restart the app, then try again. Live scrobbling and queued listens remain available.'
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

class LibraryHeading extends StatelessWidget {
  const LibraryHeading({
    super.key,
    required this.eyebrow,
    required this.title,
    required this.subtitle,
  });
  final String eyebrow, title, subtitle;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        eyebrow.toUpperCase(),
        style: TextStyle(
          letterSpacing: 2,
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
      const SizedBox(height: 12),
      Text(title, style: Theme.of(context).textTheme.headlineLarge),
      const SizedBox(height: 8),
      Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
      const SizedBox(height: 28),
    ],
  );
}

class LibraryStats extends StatelessWidget {
  const LibraryStats({super.key, required this.values});
  final Map<String, int> values;
  @override
  Widget build(BuildContext context) => Wrap(
    spacing: 12,
    runSpacing: 12,
    children: values.entries
        .map(
          (entry) => Container(
            constraints: const BoxConstraints(minWidth: 125),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHigh,
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${entry.value}',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 4),
                Text(entry.key),
              ],
            ),
          ),
        )
        .toList(),
  );
}

class LibraryRanking extends StatelessWidget {
  const LibraryRanking({
    super.key,
    required this.title,
    required this.items,
    this.onSelect,
  });
  final String title;
  final List<Json> items;
  final void Function(String)? onSelect;
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
              borderRadius: BorderRadius.circular(12),
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
                        style: TextStyle(
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
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Text('${number(item['count'])}'),
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
