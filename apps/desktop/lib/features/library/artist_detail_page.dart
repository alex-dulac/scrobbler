import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/album_art.dart';
import '../listening/listening_timeline.dart';
import 'library_api.dart';
import 'library_models.dart';
import 'library_widgets.dart';
import '../../widgets/library_refresh.dart';

class ArtistDetailPage extends StatefulWidget {
  const ArtistDetailPage({super.key, required this.api, required this.artist});
  final ScrobblerApi api;
  final String artist;
  @override
  State<ArtistDetailPage> createState() => _ArtistDetailPageState();
}

class _ArtistDetailPageState extends State<ArtistDetailPage>
    with LibraryRefresh<ArtistDetailPage> {
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
  ScrobblerApi get libraryApi => widget.api;

  @override
  void reloadLibrary() => _load();
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
    if (oldWidget.api != widget.api || oldWidget.artist != widget.artist) {
      _data = null;
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    final albums = data == null ? <Json>[] : records(data, 'top_albums');
    final first = data?['first_track'] as Json?;
    // The most played album sets the page's accent colour.
    final coverAlbum = albums.isNotEmpty
        ? label(albums.first['name'])
        : label(first?['album']);
    return Scaffold(
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
      body: ArtworkTint(
        api: widget.api,
        artist: widget.artist,
        album: coverAlbum,
        builder: (context, tint) => ListView(
          padding: AppSpacing.page,
          children: [
            if (_loading && data == null) const LinearProgressIndicator(),
            if (_error != null)
              LibraryFailure(error: _error!, retry: () => _load(force: true)),
            if (data != null) ...[
              _ArtistHero(
                api: widget.api,
                artist: widget.artist,
                album: coverAlbum,
                data: data,
                tint: tint,
              ),
              const SizedBox(height: 36),
              _YearsChart(years: records(data, 'years'), tint: tint),
              const SizedBox(height: 36),
              LayoutBuilder(
                builder: (context, constraints) {
                  final albumSection = _AlbumGrid(
                    api: widget.api,
                    artist: widget.artist,
                    albums: albums,
                    total: number(data['total_scrobbles']),
                  );
                  final trackSection = _TopTracks(
                    api: widget.api,
                    artist: widget.artist,
                    tracks: records(data, 'top_tracks'),
                    tint: tint,
                  );
                  if (constraints.maxWidth < 980) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        albumSection,
                        const SizedBox(height: 36),
                        trackSection,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 5, child: albumSection),
                      const SizedBox(width: 40),
                      Expanded(flex: 4, child: trackSection),
                    ],
                  );
                },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ArtistHero extends StatelessWidget {
  const _ArtistHero({
    required this.api,
    required this.artist,
    required this.album,
    required this.data,
    required this.tint,
  });
  final ScrobblerApi api;
  final String artist, album;
  final Json data;
  final Color tint;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = ScrobblerColors.of(context);
    final total = number(data['total_scrobbles']);
    final rank = (data['rank'] as num?)?.toInt();
    final firstHeard = DateTime.tryParse(label(data['first_scrobbled_at']));
    final lastPlayed = DateTime.tryParse(label(data['last_scrobbled_at']));
    final first = data['first_track'] as Json?;
    return Container(
      padding: const EdgeInsets.all(28),
      decoration: BoxDecoration(
        borderRadius: AppRadii.largeAll,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            tint.withValues(alpha: .22),
            colors.surfaceRaised.withValues(alpha: .6),
          ],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AlbumArt(api: api, artist: artist, album: album, size: 120),
              const SizedBox(width: 24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ARTIST',
                      style: theme.textTheme.labelSmall?.copyWith(color: tint),
                    ),
                    const SizedBox(height: 8),
                    Text(artist, style: theme.textTheme.displaySmall),
                    const SizedBox(height: 18),
                    if (total == 0)
                      const Text('No listening data yet.')
                    else
                      Wrap(
                        spacing: 36,
                        runSpacing: 14,
                        children: [
                          _HeroFact(
                            value: formatCount(total),
                            label: total == 1 ? 'Scrobble' : 'Scrobbles',
                          ),
                          if (rank != null)
                            _HeroFact(value: '#$rank', label: 'Of all artists'),
                          if (firstHeard != null)
                            _HeroFact(
                              value:
                                  '${formatMonth(firstHeard.month)} ${firstHeard.year}',
                              label: 'First heard',
                            ),
                          if (lastPlayed != null)
                            _HeroFact(
                              value: formatWhen(lastPlayed),
                              label: 'Last played',
                            ),
                        ],
                      ),
                  ],
                ),
              ),
            ],
          ),
          if (first != null) ...[
            const SizedBox(height: 24),
            Divider(color: colors.outline.withValues(alpha: .6)),
            const SizedBox(height: 18),
            _FirstListen(api: api, artist: artist, data: first),
          ],
        ],
      ),
    );
  }
}

class _HeroFact extends StatelessWidget {
  const _HeroFact({required this.value, required this.label});
  final String value, label;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(value, style: theme.textTheme.headlineMedium),
        const SizedBox(height: 4),
        Text(label.toUpperCase(), style: theme.textTheme.labelSmall),
      ],
    );
  }
}

/// The track that started it all.
class _FirstListen extends StatelessWidget {
  const _FirstListen({
    required this.api,
    required this.artist,
    required this.data,
  });
  final ScrobblerApi api;
  final String artist;
  final Json data;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final album = label(data['album']);
    final when = DateTime.tryParse(label(data['scrobbled_at']));
    return Row(
      children: [
        AlbumArt(api: api, artist: artist, album: album, size: 44),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('FIRST LISTEN', style: theme.textTheme.labelSmall),
              const SizedBox(height: 4),
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: label(data['name']),
                      style: theme.textTheme.titleMedium,
                    ),
                    if (album.isNotEmpty) TextSpan(text: '  from $album'),
                  ],
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        if (when != null) ...[
          const SizedBox(width: 16),
          Text(
            formatFullDate(when),
            style: AppFonts.numeric(theme.textTheme.bodySmall),
          ),
        ],
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title, {this.subtitle});
  final String title;
  final String? subtitle;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: theme.textTheme.titleLarge),
          if (subtitle != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(subtitle!, style: theme.textTheme.bodyMedium),
            ),
        ],
      ),
    );
  }
}

/// Scrobbles per year from the first listen through this year, gaps included.
class _YearsChart extends StatelessWidget {
  const _YearsChart({required this.years, required this.tint});
  final List<Json> years;
  final Color tint;
  @override
  Widget build(BuildContext context) {
    final colors = ScrobblerColors.of(context);
    final counts = ListeningTimeline.annualCounts(years);
    if (counts.isEmpty) return const SizedBox.shrink();
    final now = DateTime.now().year;
    final first = counts.keys.reduce(math.min);
    final last = math.max(now, counts.keys.reduce(math.max));
    final span = [for (var year = first; year <= last; year++) year];
    final peak = counts.values.reduce(math.max);
    final peakYear = span.firstWhere((year) => counts[year] == peak);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionTitle(
          'Through the years',
          subtitle:
              'Peak $peakYear · ${formatCount(peak)} scrobbles'
              '${last == now ? ' · $now is year to date' : ''}',
        ),
        Container(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
          decoration: BoxDecoration(
            color: colors.surfaceRaised,
            borderRadius: AppRadii.largeAll,
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final slot = constraints.maxWidth / span.length;
              final shortYears = slot < 38;
              final everyCount = slot >= 34;
              return Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (final year in span)
                    Expanded(
                      child: _YearBar(
                        year: year,
                        count: counts[year] ?? 0,
                        peak: peak,
                        tint: tint,
                        showCount: everyCount || year == peakYear,
                        yearLabel: shortYears
                            ? "'${'$year'.substring(2)}"
                            : '$year',
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}

class _YearBar extends StatelessWidget {
  const _YearBar({
    required this.year,
    required this.count,
    required this.peak,
    required this.tint,
    required this.showCount,
    required this.yearLabel,
  });
  final int year, count, peak;
  final Color tint;
  final bool showCount;
  final String yearLabel;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isPeak = count == peak;
    final small = AppFonts.numeric(theme.textTheme.labelSmall);
    return Tooltip(
      message: '$year: ${formatCount(count)} scrobbles',
      child: Semantics(
        label: '$year, ${formatCount(count)} scrobbles',
        excludeSemantics: true,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              height: 16,
              child: showCount && count > 0
                  ? Text(
                      formatCount(count),
                      style: small?.copyWith(
                        color: isPeak ? theme.colorScheme.onSurface : null,
                      ),
                    )
                  : null,
            ),
            const SizedBox(height: 4),
            Container(
              height: count == 0 ? 2 : math.max(3, count / peak * 120),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              decoration: BoxDecoration(
                color: count == 0
                    ? theme.colorScheme.outline
                    : tint.withValues(alpha: isPeak ? 1 : .5),
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(AppRadii.small),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(yearLabel, style: small, maxLines: 1, softWrap: false),
          ],
        ),
      ),
    );
  }
}

class _AlbumGrid extends StatelessWidget {
  const _AlbumGrid({
    required this.api,
    required this.artist,
    required this.albums,
    required this.total,
  });
  final ScrobblerApi api;
  final String artist;
  final List<Json> albums;
  final int total;
  static const _tile = 156.0;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle(
          'Albums',
          subtitle: 'Scrobbles and share of all plays by this artist',
        ),
        if (albums.isEmpty) const Text('No album listening yet.'),
        Wrap(
          spacing: 16,
          runSpacing: 20,
          children: [
            for (final album in albums)
              SizedBox(
                width: _tile,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AlbumArt(
                      api: api,
                      artist: artist,
                      album: label(album['name']),
                      size: _tile,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      label(album['name']),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      total == 0
                          ? formatCount(number(album['count']))
                          : '${formatCount(number(album['count']))} · '
                                '${(number(album['count']) / total * 100).round()}%',
                      style: AppFonts.numeric(theme.textTheme.bodySmall),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _TopTracks extends StatelessWidget {
  const _TopTracks({
    required this.api,
    required this.artist,
    required this.tracks,
    required this.tint,
  });
  final ScrobblerApi api;
  final String artist;
  final List<Json> tracks;
  final Color tint;
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final maximum = tracks.fold<int>(
      1,
      (value, track) => math.max(value, number(track['count'])),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _SectionTitle('Top tracks'),
        if (tracks.isEmpty) const Text('No listening data yet.'),
        for (final (index, track) in tracks.take(10).indexed)
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: Row(
              children: [
                SizedBox(
                  width: 28,
                  child: Text(
                    '${index + 1}'.padLeft(2, '0'),
                    style: AppFonts.numeric(
                      theme.textTheme.bodyMedium,
                    )?.copyWith(color: tint),
                  ),
                ),
                AlbumArt(
                  api: api,
                  artist: artist,
                  album: label(track['album']),
                  size: 40,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              label(track['name']),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: theme.textTheme.titleMedium,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            formatCount(number(track['count'])),
                            style: AppFonts.numeric(theme.textTheme.bodyMedium),
                          ),
                        ],
                      ),
                      if (label(track['album']).isNotEmpty)
                        Text(
                          label(track['album']),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: theme.textTheme.bodySmall,
                        ),
                      const SizedBox(height: 6),
                      LinearProgressIndicator(
                        value: number(track['count']) / maximum,
                        color: tint,
                        backgroundColor: theme.colorScheme.outline.withValues(
                          alpha: .4,
                        ),
                        minHeight: 3,
                        borderRadius: AppRadii.smallAll,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
