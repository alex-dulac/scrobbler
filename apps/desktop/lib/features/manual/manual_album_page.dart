import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../widgets/album_art.dart';

class ManualAlbumPage extends StatefulWidget {
  const ManualAlbumPage({super.key, required this.api});
  final ScrobblerApi api;
  @override
  State<ManualAlbumPage> createState() => _ManualAlbumPageState();
}

class _ManualAlbumPageState extends State<ManualAlbumPage> {
  final _artist = TextEditingController();
  final _album = TextEditingController();
  DateTime _finished = DateTime.now();
  Map<String, dynamic>? _preview;
  bool _busy = false;
  bool _queued = false;
  String? _error, _notice;

  @override
  void dispose() {
    _artist.dispose();
    _album.dispose();
    super.dispose();
  }

  void _invalidate() => setState(() {
    _preview = null;
    _queued = false;
    _error = null;
    _notice = null;
  });
  Future<void> _pickTime() async {
    final day = await showDatePicker(
      context: context,
      initialDate: _finished,
      firstDate: DateTime(2002),
      lastDate: DateTime.now(),
    );
    if (day == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_finished),
    );
    if (time == null || !mounted) return;
    _invalidate();
    setState(
      () => _finished = DateTime(
        day.year,
        day.month,
        day.day,
        time.hour,
        time.minute,
      ),
    );
  }

  Future<void> _loadPreview() async {
    if (_artist.text.trim().isEmpty || _album.text.trim().isEmpty) {
      setState(
        () => _error = 'Enter an artist and album to find the track list.',
      );
      return;
    }
    setState(() {
      _busy = true;
      _preview = null;
      _error = null;
      _notice = null;
      _queued = false;
    });
    try {
      final query = Uri(
        queryParameters: {
          'artist': _artist.text.trim(),
          'album': _album.text.trim(),
          'finished_at': _finished.toUtc().toIso8601String(),
        },
      ).query;
      final result = await widget.api.request(
        'GET',
        '/manual/album/?$query',
        null,
        const Duration(seconds: 45),
      );
      if (mounted) setState(() => _preview = result);
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Album lookup timed out. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    final preview = _preview;
    if (preview == null || _busy || _queued) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await widget.api.request('POST', '/manual/submit/', {
        'preview_id': preview['preview_id'],
      });
      if (mounted) {
        setState(() {
          _queued = true;
          _notice = '${result['count']} tracks queued. ${result['message']}';
        });
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not confirm submission. Retry this same preview safely.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _date(DateTime time) =>
      '${time.month}/${time.day}/${time.year} · ${TimeOfDay.fromDateTime(time).format(context)}';
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final preview = _preview;
    final tracks = (preview?['tracks'] as List?) ?? const [];
    final eligible = tracks.where((track) => track['eligible'] != false).length;
    return ListView(
      padding: const EdgeInsets.all(32),
      children: [
        Text('ALBUM PREVIEW', style: theme.textTheme.labelSmall),
        const SizedBox(height: 12),
        Text('Manual album scrobbling', style: theme.textTheme.displaySmall),
        const SizedBox(height: 12),
        const Text(
          'Record an album you listened to on vinyl, CD, or away from your computer. Review every track and time before adding it to Last.fm.',
        ),
        const SizedBox(height: 28),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 280,
              child: TextField(
                controller: _artist,
                enabled: !_busy,
                onChanged: (_) => _invalidate(),
                decoration: const InputDecoration(
                  labelText: 'Artist',
                  hintText: 'Artist name',
                ),
              ),
            ),
            SizedBox(
              width: 280,
              child: TextField(
                controller: _album,
                enabled: !_busy,
                onChanged: (_) => _invalidate(),
                decoration: const InputDecoration(
                  labelText: 'Album',
                  hintText: 'Album title',
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            OutlinedButton.icon(
              onPressed: _busy ? null : _pickTime,
              icon: const Icon(Icons.schedule),
              label: Text('Finished ${_date(_finished)}'),
            ),
            FilledButton.icon(
              onPressed: _busy ? null : _loadPreview,
              icon: const Icon(Icons.queue_music),
              label: const Text('Preview album'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        const Text(
          'Times use your local timezone. Track start times are calculated backward from when you finished.',
        ),
        if (_busy)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: LinearProgressIndicator(),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(
              _error!,
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        if (_notice != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(
              _notice!,
              style: TextStyle(color: theme.colorScheme.secondary),
            ),
          ),
        if (preview != null) ...[
          const SizedBox(height: 28),
          Row(
            children: [
              AlbumArt(
                api: widget.api,
                artist: '${preview['artist']}',
                album: '${preview['album']}',
                url: preview['artwork_url'] as String?,
                size: 88,
              ),
              const SizedBox(width: 20),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${preview['album']}',
                      style: theme.textTheme.headlineMedium,
                    ),
                    Text('${preview['artist']} · $eligible eligible tracks'),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          ...tracks.asMap().entries.map((entry) {
            final track = entry.value as Map;
            final start = DateTime.parse('${track['started_at']}').toLocal();
            final eligible = track['eligible'] != false;
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Text(
                '${entry.key + 1}'.padLeft(2, '0'),
                style: theme.textTheme.labelLarge,
              ),
              title: Text('${track['name']}'),
              subtitle: Text(
                eligible
                    ? _date(start)
                    : 'Not submitted · tracks must be longer than 30 seconds',
              ),
              trailing: Text(
                '${((track['duration_seconds'] as num) / 60).floor()}:${((track['duration_seconds'] as num).floor() % 60).toString().padLeft(2, '0')}',
              ),
            );
          }),
          const SizedBox(height: 20),
          Align(
            alignment: Alignment.centerLeft,
            child: FilledButton.icon(
              onPressed: _busy || _queued ? null : _submit,
              icon: Icon(_queued ? Icons.check : Icons.add),
              label: Text(
                _queued
                    ? 'Added to your queue'
                    : 'Queue $eligible reviewed tracks',
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'This adds the reviewed listens to your durable queue. Submission waits while scrobbling is paused.',
          ),
        ],
      ],
    );
  }
}
