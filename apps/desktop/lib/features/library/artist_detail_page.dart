import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import 'library_api.dart';
import 'library_models.dart';
import 'library_widgets.dart';

class ArtistDetailPage extends StatefulWidget {
  const ArtistDetailPage({super.key, required this.api, required this.artist});
  final ScrobblerApi api;
  final String artist;
  @override
  State<ArtistDetailPage> createState() => _ArtistDetailPageState();
}

class _ArtistDetailPageState extends State<ArtistDetailPage> {
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

  void _refresh() => _load();
  Future<void> _load({bool force = false}) async {
    final generation = ++_generation;
    final api = LibraryApi(widget.api);
    setState(() {
      _data ??= api.cache.peek(LibraryApi.artistPath(widget.artist));
      _loading = true;
      _error = null;
    });
    try {
      final data = await api.artist(widget.artist, force: force);
      if (!mounted || generation != _generation) return;
      setState(() {
        _data = data;
        _loading = false;
      });
    } catch (error) {
      if (!mounted || generation != _generation) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  @override
  void didUpdateWidget(ArtistDetailPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      LibraryCache.forApi(oldWidget.api).removeListener(_refresh);
      LibraryCache.forApi(widget.api).addListener(_refresh);
    }
    if (oldWidget.api != widget.api || oldWidget.artist != widget.artist) {
      _data = null;
      _load();
    }
  }

  @override
  void dispose() {
    LibraryCache.forApi(widget.api).removeListener(_refresh);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Artist history'),
      actions: [
        IconButton(
          tooltip: 'Refresh artist',
          onPressed: _loading ? null : () => _load(force: true),
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: ListView(
      padding: const EdgeInsets.all(32),
      children: [
        LibraryHeading(
          eyebrow: 'ARTIST',
          title: widget.artist,
          subtitle: 'Listening counts and rankings from the synced library.',
        ),
        if (_loading && _data == null) const LinearProgressIndicator(),
        if (_error != null)
          LibraryFailure(error: _error!, retry: () => _load(force: true)),
        if (_data != null) ...[
          LibraryStats(
            values: {
              'Scrobbles': number(_data!['total_scrobbles']),
              'Years listening': records(_data!, 'years').length,
            },
          ),
          LibraryRanking(
            title: 'Top tracks',
            items: records(_data!, 'top_tracks'),
          ),
          LibraryRanking(
            title: 'Top albums',
            items: records(_data!, 'top_albums'),
          ),
          LibraryRanking(
            title: 'Through the years',
            items: records(_data!, 'years')
                .map(
                  (row) => <String, dynamic>{
                    'name': '${row['year']}',
                    'count': row['count'],
                  },
                )
                .toList(),
          ),
        ],
      ],
    ),
  );
}
