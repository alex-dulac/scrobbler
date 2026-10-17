import 'dart:async';
import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../services/library_cache.dart';
import 'artist_detail_page.dart';
import 'library_api.dart';
import 'library_models.dart';
import 'library_widgets.dart';

class ListeningHistoryPage extends StatefulWidget {
  const ListeningHistoryPage({super.key, required this.api});
  final ScrobblerApi api;
  @override
  State<ListeningHistoryPage> createState() => _ListeningHistoryPageState();
}

class _ListeningHistoryPageState extends State<ListeningHistoryPage> {
  final _search = TextEditingController();
  Timer? _debounce;
  HistoryPage? _data;
  Object? _error;
  bool _loading = true;
  int _generation = 0;
  int _page = 1;
  @override
  void initState() {
    super.initState();
    LibraryCache.forApi(widget.api).addListener(_refresh);
    _load();
  }

  @override
  void didUpdateWidget(ListeningHistoryPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.api != widget.api) {
      LibraryCache.forApi(oldWidget.api).removeListener(_refresh);
      LibraryCache.forApi(widget.api).addListener(_refresh);
      _data = null;
      _dataPath = null;
      _load();
    }
  }

  void _refresh() => _load();

  String? _dataPath;
  Future<void> _load({bool force = false}) async {
    final path = LibraryApi.historyPath(_search.text.trim(), _page);
    if (_dataPath != path) {
      final cached = LibraryCache.forApi(widget.api).peek(path);
      _data = cached == null ? null : HistoryPage.fromJson(cached);
      _dataPath = path;
    }
    final generation = ++_generation;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await LibraryApi(
        widget.api,
      ).history(_search.text.trim(), _page, force: force);
      if (mounted && generation == _generation) {
        setState(() {
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

  void _searchChanged(String value) {
    _debounce?.cancel();
    ++_generation;
    setState(() {
      _page = 1;
      _data = null;
      _dataPath = null;
      _loading = true;
      _error = null;
    });
    _debounce = Timer(const Duration(milliseconds: 350), _load);
  }

  @override
  void dispose() {
    LibraryCache.forApi(widget.api).removeListener(_refresh);
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(32),
    children: [
      const LibraryHeading(
        eyebrow: 'The archive',
        title: 'Listening history',
        subtitle: 'Search your synced listening history.',
      ),
      TextField(
        controller: _search,
        onChanged: _searchChanged,
        decoration: InputDecoration(
          hintText: 'Search tracks, artists, or albums',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: IconButton(
            tooltip: 'Refresh history',
            onPressed: _loading ? null : () => _load(force: true),
            icon: const Icon(Icons.refresh),
          ),
        ),
      ),
      const SizedBox(height: 20),
      if (_loading && _data == null) const LinearProgressIndicator(),
      if (_error != null)
        LibraryFailure(error: _error!, retry: () => _load(force: true)),
      if (_data != null) ...[
        Text(
          '${_data!.total} listens${_search.text.trim().isEmpty ? '' : ' matching your search'}',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        if (_data!.items.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 40),
            child: Text(
              _search.text.trim().isEmpty
                  ? 'No listening history has been synced yet.'
                  : 'No listens match this search. Try an artist or a different title.',
            ),
          ),
        ..._data!.items.map(
          (entry) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    Icons.music_note,
                    color: Theme.of(context).colorScheme.primary,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.track,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      InkWell(
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => ArtistDetailPage(
                              api: widget.api,
                              artist: entry.artist,
                            ),
                          ),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 5),
                          child: Text(
                            entry.artist,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.primary,
                            ),
                          ),
                        ),
                      ),
                      if (entry.album.isNotEmpty)
                        Text(
                          entry.album,
                          style: Theme.of(context).textTheme.bodySmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  _date(entry.date),
                  textAlign: TextAlign.right,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
        const Divider(height: 28),
        Row(
          children: [
            Text('Page $_page'),
            const Spacer(),
            IconButton(
              tooltip: 'Previous page',
              onPressed: !_loading && _page > 1
                  ? () {
                      _page--;
                      _load();
                    }
                  : null,
              icon: const Icon(Icons.chevron_left),
            ),
            IconButton(
              tooltip: 'Next page',
              onPressed: !_loading && _data!.hasNext
                  ? () {
                      _page++;
                      _load();
                    }
                  : null,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ],
    ],
  );
  String _date(DateTime? date) => date == null
      ? 'Unknown date'
      : '${date.day}/${date.month}/${date.year}\n${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
}
