import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../models/scrobbler_state.dart';
import '../../services/scrobbler_api.dart';
import '../../theme/app_theme.dart';
import '../../theme/format.dart';
import '../../widgets/page_heading.dart';
import 'ipod_api.dart';

class IpodPage extends StatefulWidget {
  const IpodPage({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  State<IpodPage> createState() => _IpodPageState();
}

class _IpodPageState extends State<IpodPage> {
  late final _api = IpodApi(widget.controller.api);
  List<IpodPlay>? _plays;
  // Plays are checked by default, so track the exceptions; reloads keep them.
  final Set<int> _unchecked = {};
  bool _loading = false, _busy = false;
  String? _error, _notice;
  int? _seenCaptureId;
  bool _seenJobRunning = false;

  IpodStatus? get _status => widget.controller.state?.ipod;
  List<int> get _selected => [
    for (final play in _plays ?? const <IpodPlay>[])
      if (!_unchecked.contains(play.id)) play.id,
  ];

  @override
  void initState() {
    super.initState();
    _seenCaptureId = _status?.captureId;
    _seenJobRunning = _status?.jobRunning ?? false;
    widget.controller.addListener(_onStateChanged);
    _load();
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onStateChanged);
    super.dispose();
  }

  // Reload after a new capture or when a scrobble job finishes.
  void _onStateChanged() {
    final status = _status;
    if (status == null || !mounted) return;
    final captured = status.captureId != _seenCaptureId;
    final jobFinished = _seenJobRunning && !status.jobRunning;
    _seenCaptureId = status.captureId;
    _seenJobRunning = status.jobRunning;
    if (captured || jobFinished) {
      _load();
    } else {
      setState(() {});
    }
  }

  String _message(Object error, String fallback) =>
      error is ApiException ? error.message : fallback;

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final plays = await _api.plays();
      if (!mounted) return;
      setState(() {
        _plays = plays;
        _unchecked.retainAll(plays.map((play) => play.id));
      });
    } catch (error) {
      if (mounted) {
        setState(() => _error = _message(error, 'Could not load iPod plays.'));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _run(Future<String> Function() action, String fallback) async {
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      final message = await action();
      if (mounted) setState(() => _notice = message);
      await widget.controller.refresh();
    } catch (error) {
      if (mounted) setState(() => _error = _message(error, fallback));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _scrobble() {
    // A short job can finish between polls, so reload on the next state
    // even if it is never seen running.
    _seenJobRunning = true;
    return _run(
      () => _api.scrobble(_selected),
      'Could not start scrobbling. Please try again.',
    );
  }

  Future<void> _discard() async {
    final count = _selected.length;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Discard $count iPod plays?'),
        content: const Text(
          'Discarded plays are never scrobbled and won’t be shown again.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Discard'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    await _run(
      () => _api.discard(_selected),
      'Could not discard plays. Please try again.',
    );
    if (mounted) await _load();
  }

  // A rescan bumps captureId, which reloads the list via _onStateChanged.
  Future<void> _rescan() =>
      _run(_api.rescan, 'Could not read the iPod. Please try again.');

  static final _weekdays = 'Mon Tue Wed Thu Fri Sat Sun'.split(' ');
  static final _months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'
      .split(' ');
  String _date(DateTime time) =>
      '${_weekdays[time.weekday - 1]} ${_months[time.month - 1]} ${time.day} · ${formatClock(time)}';

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final status = _status;
    final connected = status?.connected == true;
    final databaseAvailable =
        widget.controller.state?.databaseAvailable == true;
    final jobRunning = status?.jobRunning == true;
    final plays = _plays ?? const <IpodPlay>[];
    final selected = _selected;
    final locked = _busy || jobRunning;
    return ListView(
      padding: AppSpacing.page,
      children: [
        const PageHeading(
          title: 'iPod plays',
          subtitle:
              'Plays from your iPod are saved as soon as it connects, before Apple Music can clear them. Review them here, then scrobble or discard.',
        ),
        Wrap(
          spacing: 16,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.circle,
                  size: 8,
                  color: connected
                      ? theme.colorScheme.secondary
                      : theme.colorScheme.outline,
                ),
                const SizedBox(width: 8),
                Text(
                  connected
                      ? '${status!.name ?? 'iPod'} connected'
                      : 'No iPod connected',
                ),
              ],
            ),
            OutlinedButton.icon(
              onPressed: connected && databaseAvailable && !locked
                  ? _rescan
                  : null,
              icon: const Icon(Icons.refresh),
              label: const Text('Read iPod again'),
            ),
          ],
        ),
        if (!databaseAvailable)
          const Padding(
            padding: EdgeInsets.only(top: 16),
            child: Text(
              'iPod plays need your history database. Connect it and restart the app; plays stay on the iPod until it syncs with Apple Music.',
            ),
          ),
        if (jobRunning) ...[
          const SizedBox(height: 24),
          LinearProgressIndicator(
            value: status!.jobTotal == 0
                ? null
                : (status.jobScrobbled + status.jobFailed) / status.jobTotal,
          ),
          const SizedBox(height: 8),
          Text(
            'Scrobbling ${status.jobScrobbled + status.jobFailed} of ${status.jobTotal}…',
          ),
        ],
        if (_loading || _busy)
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
        if (_plays != null && plays.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Text(
              'No iPod plays to review. Connect your iPod to capture what you’ve played since it last synced.',
            ),
          ),
        if (plays.isNotEmpty) ...[
          const SizedBox(height: 24),
          Wrap(
            spacing: 16,
            runSpacing: 12,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Checkbox(
                    tristate: true,
                    value: selected.length == plays.length
                        ? true
                        : selected.isEmpty
                        ? false
                        : null,
                    onChanged: locked
                        ? null
                        : (_) => setState(() {
                            if (selected.isEmpty) {
                              _unchecked.clear();
                            } else {
                              _unchecked.addAll(plays.map((play) => play.id));
                            }
                          }),
                  ),
                  Text('${selected.length} of ${plays.length} selected'),
                ],
              ),
              FilledButton.icon(
                onPressed: locked || selected.isEmpty ? null : _scrobble,
                icon: const Icon(Icons.upload_rounded),
                label: const Text('Scrobble selected'),
              ),
              OutlinedButton.icon(
                onPressed: locked || selected.isEmpty ? null : _discard,
                icon: const Icon(Icons.delete_outline),
                label: const Text('Discard selected'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (final play in plays)
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: !_unchecked.contains(play.id),
              onChanged: locked
                  ? null
                  : (checked) => setState(
                      () => checked == true
                          ? _unchecked.remove(play.id)
                          : _unchecked.add(play.id),
                    ),
              title: Text(play.track),
              subtitle: Text([play.artist, ?play.album].join(' · ')),
              secondary: Text(
                '${play.estimated ? '~ ' : ''}${_date(play.playedAt)}',
                style: AppFonts.numeric(theme.textTheme.bodySmall),
              ),
            ),
          const SizedBox(height: 16),
          const Text(
            'Times marked ~ are estimated: the iPod only records when a track’s latest play finished. Plays older than 14 days can’t be scrobbled to Last.fm and aren’t listed. Unselected plays stay here for later.',
          ),
        ],
      ],
    );
  }
}
