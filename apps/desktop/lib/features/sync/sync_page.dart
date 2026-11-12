import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../models/scrobbler_state.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/page_heading.dart';

enum SyncRange {
  week('Last 7 days'),
  month('Last 30 days'),
  year('This year'),
  all('All history'),
  custom('Custom');

  const SyncRange(this.label);
  final String label;
}

/// Saves scrobbles made elsewhere, like a phone scrobbling straight to
/// Last.fm, to the history database so library counts include them.
class SyncPage extends StatefulWidget {
  const SyncPage({super.key, required this.controller, this.today});
  final ScrobblerController controller;
  final DateTime Function()? today;
  @override
  State<SyncPage> createState() => _SyncPageState();
}

class _SyncPageState extends State<SyncPage> {
  SyncRange _range = SyncRange.week;
  DateTimeRange? _custom;
  bool _busy = false;
  String? _error;

  ScrobblerController get _controller => widget.controller;
  SyncStatus? get _status => _controller.state?.sync;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_changed);
  }

  @override
  void dispose() {
    _controller.removeListener(_changed);
    super.dispose();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  DateTime get _today {
    final now = (widget.today ?? DateTime.now)();
    return DateTime(now.year, now.month, now.day);
  }

  /// The first and last days to sync, both included; null is open-ended.
  (DateTime?, DateTime?) get _days => switch (_range) {
    SyncRange.week => (_today.subtract(const Duration(days: 6)), null),
    SyncRange.month => (_today.subtract(const Duration(days: 29)), null),
    SyncRange.year => (DateTime(_today.year), null),
    SyncRange.all => (null, null),
    SyncRange.custom => (_custom?.start, _custom?.end),
  };

  static String _day(DateTime date) =>
      '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';

  static String _describe(DateTime? from, DateTime? to) => switch ((from, to)) {
    (null, null) => 'All of your Last.fm history',
    (null, final to?) => 'Everything through ${formatDate(to)}',
    (final from?, null) => '${formatDate(from)} through today',
    (final from?, final to?) when from == to => formatDate(from),
    (final from?, final to?) => '${formatDate(from)} – ${formatDate(to)}',
  };

  void _pick(SyncRange range) => setState(() {
    _range = range;
    if (range == SyncRange.custom) {
      _custom ??= DateTimeRange(
        start: _today.subtract(const Duration(days: 6)),
        end: _today,
      );
    }
  });

  // One date at a time: the single-date picker can jump to a year, where the
  // range picker only scrolls month by month.
  Future<void> _pickDay({required bool start}) async {
    final range = _custom!;
    final picked = await showDatePicker(
      context: context,
      initialDate: start ? range.start : range.end,
      firstDate: start ? DateTime(2002) : range.start,
      lastDate: start ? range.end : _today,
      helpText: start ? 'Sync from' : 'Sync through',
    );
    if (picked == null || !mounted) return;
    setState(
      () => _custom = start
          ? DateTimeRange(start: picked, end: range.end)
          : DateTimeRange(start: range.start, end: picked),
    );
  }

  Future<void> _sync() async {
    final (from, to) = _days;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await _controller.api.request('POST', '/sync/scrobbles/', {
        'time_from': from == null ? null : _day(from),
        'time_to': to == null ? null : _day(to),
      });
      await _controller.refresh();
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not start the sync. Please try again.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final status = _status;
    final running = status?.running == true;
    final databaseAvailable = _controller.state?.databaseAvailable == true;
    final (from, to) = _days;
    return ListView(
      padding: AppSpacing.page,
      children: [
        const PageHeading(
          title: 'Sync from Last.fm',
          subtitle:
              'Scrobbles made outside this app, like on your phone, go straight to Last.fm. Sync them into your history so your library counts include them. Scrobbles already saved are skipped.',
        ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final range in SyncRange.values)
              ChoiceChip(
                label: Text(range.label),
                selected: _range == range,
                onSelected: running ? null : (_) => _pick(range),
              ),
          ],
        ),
        if (_range == SyncRange.custom) ...[
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                onPressed: running ? null : () => _pickDay(start: true),
                icon: const Icon(Icons.calendar_today_rounded, size: 16),
                label: Text('From ${formatDate(_custom!.start)}'),
              ),
              OutlinedButton.icon(
                onPressed: running ? null : () => _pickDay(start: false),
                icon: const Icon(Icons.calendar_today_rounded, size: 16),
                label: Text('To ${formatDate(_custom!.end)}'),
              ),
            ],
          ),
        ],
        const SizedBox(height: 16),
        Text(_describe(from, to)),
        if (_range == SyncRange.all)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'A full sync reads every scrobble you’ve made, so a long history can take several minutes.',
              style: TextStyle(color: ScrobblerColors.of(context).textMuted),
            ),
          ),
        const SizedBox(height: 20),
        FilledButton.icon(
          onPressed: databaseAvailable && !running && !_busy ? _sync : null,
          icon: const Icon(Icons.sync_rounded),
          label: const Text('Sync now'),
        ),
        if (!databaseAvailable)
          const Padding(
            padding: EdgeInsets.only(top: 16),
            child: Text(
              'Syncing needs your history database. Connect it and restart the app.',
            ),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 16),
            child: Text(
              _error!,
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        if (running) ...[
          const SizedBox(height: 24),
          const LinearProgressIndicator(),
          const SizedBox(height: 8),
          Text(
            '${_describe(status!.timeFrom, status.timeTo)} · '
            'checked ${formatCount(status.fetched)} scrobbles, ${formatCount(status.saved)} new so far…',
          ),
        ] else if (status != null && status.id > 0) ...[
          const SizedBox(height: 24),
          Text('Last sync', style: theme.textTheme.titleSmall),
          const SizedBox(height: 4),
          Text(
            '${_describe(status.timeFrom, status.timeTo)} · '
            'checked ${formatCount(status.fetched)} scrobbles, saved ${formatCount(status.saved)} new.',
          ),
          if (status.error != null)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                '${status.error} Scrobbles saved before it stopped are kept; sync again to finish.',
                style: TextStyle(color: theme.colorScheme.error),
              ),
            ),
        ],
      ],
    );
  }
}
