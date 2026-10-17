import 'package:flutter/material.dart';
import '../../models/scrobbler_state.dart';
import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import 'listening_timeline.dart';

/// Listening history for the current recording, displayed without navigation.
class ListeningContext extends StatefulWidget {
  const ListeningContext({super.key, required this.api, required this.track});
  final ScrobblerApi api;
  final ScrobbleTrack track;

  @override
  State<ListeningContext> createState() => _ListeningContextState();
}

class _ListeningContextState extends State<ListeningContext> {
  Map<String, dynamic>? _data;
  String? _error;
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    LibraryCache.forApi(widget.api).addListener(_refresh);
    _load();
  }

  @override
  void didUpdateWidget(ListeningContext oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      LibraryCache.forApi(oldWidget.api).removeListener(_refresh);
      LibraryCache.forApi(widget.api).addListener(_refresh);
      _data = null;
    }
    final previous = oldWidget.track;
    final current = widget.track;
    if (oldWidget.api != widget.api ||
        previous.name != current.name ||
        previous.artist != current.artist ||
        previous.album != current.album) {
      _load();
    }
  }

  void _refresh() => _load();

  String? _dataPath;
  Future<void> _load({bool force = false}) async {
    final generation = ++_generation;
    final path = Uri(
      path: '/library/context/',
      queryParameters: {
        'artist': widget.track.artist,
        'track': widget.track.name,
        if (widget.track.album.isNotEmpty) 'album': widget.track.album,
      },
    ).toString();
    final cache = LibraryCache.forApi(widget.api);
    setState(() {
      if (_dataPath != path) _data = cache.peek(path);
      _dataPath = path;
      _error = null;
    });
    try {
      final data = await cache.get(path, force: force);
      if (!mounted || generation != _generation) return;
      setState(() => _data = data);
    } catch (error) {
      if (!mounted || generation != _generation) return;
      setState(
        () => _error = error is ApiException && error.statusCode == 503
            ? 'Listening history is unavailable. Connect your synced library to see track, album, and artist statistics.'
            : 'Could not load listening history. Please try again.',
      );
    }
  }

  @override
  void dispose() {
    LibraryCache.forApi(widget.api).removeListener(_refresh);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null && _data == null) {
      return _Panel(
        title: 'Listening history unavailable',
        children: [
          Text(_error!),
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => _load(force: true),
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ),
        ],
      );
    }
    if (_data == null) {
      return const _Panel(
        title: 'Your listening history',
        children: [
          LinearProgressIndicator(),
          SizedBox(height: 12),
          Text('Loading track, album, and artist statistics…'),
        ],
      );
    }
    final track = object(_data!['track']);
    final album = _data!['album'] == null ? null : object(_data!['album']);
    final artist = object(_data!['artist']);
    final panels = <Widget>[
      _Panel(
        title: 'Track history',
        subtitle: widget.track.name,
        children: [
          _Metric(value: _count(track), label: 'scrobbles'),
          if (_count(track) == 0)
            const Text('No recorded listens for this track yet.'),
          _DateRow(label: 'First heard', value: track['first_scrobbled_at']),
          _DateRow(label: 'Last heard', value: track['last_scrobbled_at']),
          const _Label('Recent listens'),
          if (_rows(track['recent_scrobbles']).isEmpty)
            const Text('No recorded listens'),
          ..._rows(track['recent_scrobbles'])
              .take(5)
              .map(
                (value) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Text(_date(value, time: true)),
                ),
              ),
        ],
      ),
      _Panel(
        title: 'Album history',
        subtitle: widget.track.album.isEmpty
            ? 'Album not identified'
            : widget.track.album,
        children: [
          if (album == null)
            const Text('Album information is not available for this track.')
          else ...[
            _Metric(
              value: _count(album),
              label: 'scrobbles · ${album['unique_tracks'] ?? 0} tracks heard',
            ),
            if (_count(album) == 0)
              const Text('No recorded listens for this album yet.'),
            _DateRow(label: 'First heard', value: album['first_scrobbled_at']),
            _DateRow(label: 'Last heard', value: album['last_scrobbled_at']),
            const _Label('Most played tracks'),
            _Rankings(rows: _rows(album['top_tracks'])),
          ],
        ],
      ),
      _Panel(
        title: 'Artist history',
        subtitle: widget.track.artist,
        children: [
          _Metric(value: _count(artist), label: 'scrobbles'),
          if (_count(artist) == 0)
            const Text('No recorded listens for this artist yet.'),
          const _Label('Most played albums'),
          _Rankings(rows: _rows(artist['top_albums'])),
        ],
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'From your library',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            IconButton(
              onPressed: () => _load(force: true),
              tooltip: 'Refresh listening history',
              icon: const Icon(Icons.refresh, size: 19),
            ),
          ],
        ),
        if (_error != null) Text(_error!),
        ListeningTimeline(
          track: _rows(track['years']),
          album: album == null ? null : _rows(album['years']),
          artist: _rows(artist['years']),
        ),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 900
                ? 3
                : constraints.maxWidth >= 620
                ? 2
                : 1;
            final width = (constraints.maxWidth - 12 * (columns - 1)) / columns;
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: panels
                  .map((panel) => SizedBox(width: width, child: panel))
                  .toList(),
            );
          },
        ),
      ],
    );
  }
}

int _count(Map<String, dynamic> value) =>
    (value['total_scrobbles'] as num?)?.toInt() ?? 0;
List<dynamic> _rows(Object? value) => value is List ? value : const [];
String _date(Object? value, {bool time = false}) {
  final date = DateTime.tryParse('$value')?.toLocal();
  if (date == null) return '—';
  const months = [
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
  final day = '${months[date.month - 1]} ${date.day}, ${date.year}';
  return time
      ? '$day · ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}'
      : day;
}

class _Panel extends StatelessWidget {
  const _Panel({required this.title, this.subtitle, required this.children});
  final String title;
  final String? subtitle;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      border: Border.all(color: Theme.of(context).colorScheme.outline),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.labelLarge),
        if (subtitle != null)
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Text(
              subtitle!,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
        const SizedBox(height: 16),
        ...children,
      ],
    ),
  );
}

class _Metric extends StatelessWidget {
  const _Metric({required this.value, required this.label});
  final int value;
  final String label;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 8,
      children: [
        Text('$value', style: Theme.of(context).textTheme.headlineMedium),
        Text(label),
      ],
    ),
  );
}

class _DateRow extends StatelessWidget {
  const _DateRow({required this.label, required this.value});
  final String label;
  final Object? value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      children: [
        Expanded(child: Text(label)),
        Text(_date(value)),
      ],
    ),
  );
}

class _Label extends StatelessWidget {
  const _Label(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12, bottom: 8),
    child: Text(text, style: Theme.of(context).textTheme.labelLarge),
  );
}

class _Rankings extends StatelessWidget {
  const _Rankings({required this.rows});
  final List<dynamic> rows;
  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) return const Text('No recorded listens');
    final items = rows.take(5).map(object).toList();
    final maximum = items.fold<num>(
      1,
      (max, item) =>
          (item['count'] as num? ?? 0) > max ? item['count'] as num : max,
    );
    return Column(
      children: items.map((item) {
        final count = item['count'] as num? ?? 0;
        return Padding(
          padding: const EdgeInsets.only(bottom: 7),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      '${item['name'] ?? 'Unknown'}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text('$count'),
                ],
              ),
              const SizedBox(height: 5),
              LinearProgressIndicator(
                value: (count / maximum).clamp(0, 1),
                minHeight: 3,
                color: Theme.of(context).colorScheme.primary,
                backgroundColor: Theme.of(
                  context,
                ).colorScheme.surfaceContainerHighest,
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
