import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:py_scrobbler_desktop/features/library/artist_detail_page.dart';
import 'package:py_scrobbler_desktop/features/library/library_api.dart';
import 'package:py_scrobbler_desktop/features/library/library_widgets.dart';
import 'package:py_scrobbler_desktop/features/library/listening_heatmap.dart';
import 'package:py_scrobbler_desktop/features/overview/overview_page.dart';
import 'package:py_scrobbler_desktop/services/scrobbler_api.dart';
import 'package:py_scrobbler_desktop/theme/app_theme.dart';
import 'package:py_scrobbler_desktop/theme/format.dart';

void main() {
  test('daily counts report listening days, streaks, and the busiest day', () {
    final daily = DailyCounts.fromWrapped({
      'year': 2026,
      'daily': [
        {'date': '2026-01-01', 'count': 3},
        {'date': '2026-01-02', 'count': 9},
        {'date': '2026-01-03', 'count': 1},
        {'date': '2026-02-10', 'count': 4},
        {'date': '2026-02-11', 'count': 0},
      ],
    });
    expect(daily.daysListened, 4);
    expect(daily.longestStreak, 3);
    expect(daily.busiestDay!.key, DateTime(2026, 1, 2));
    expect(daily[DateTime(2026, 2, 10, 23)], 4);
  });

  test('heatmap steps follow quartiles of listening days', () {
    final limits = ListeningHeatmap.thresholds([0, 1, 2, 3, 4, 5, 6, 7, 100]);
    expect(limits, [3, 5, 6]);
    expect(ListeningHeatmap.level(0, limits), 0);
    expect(ListeningHeatmap.level(1, limits), 1);
    expect(ListeningHeatmap.level(4, limits), 2);
    expect(ListeningHeatmap.level(6, limits), 3);
    expect(ListeningHeatmap.level(100, limits), 4);
    expect(ListeningHeatmap.thresholds(const []), [1, 1, 1]);
  });

  test('counts and on-this-day dates are formatted for display', () {
    expect(formatCount(8420), '8,420');
    expect(formatCount(1234567), '1,234,567');
    expect(formatCount(-1200), '-1,200');
    expect(formatCountText('—'), '—');
    expect(
      LibraryApi.onThisDayPath(DateTime(2026, 3, 7)),
      '/library/on-this-day/?date=2026-03-07',
    );
  });

  test('times read as a 12-hour clock and relative to now', () {
    expect(formatClock(DateTime(2026, 1, 1, 0, 5)), '12:05am');
    expect(formatClock(DateTime(2026, 1, 1, 12, 0)), '12:00pm');
    expect(formatClock(DateTime(2026, 1, 1, 18, 30)), '6:30pm');
    final now = DateTime(2026, 10, 17, 21, 30); // a Saturday
    String when(DateTime date) => formatWhen(date, now: now);
    expect(when(DateTime(2026, 10, 17, 21, 29, 40)), 'Just now');
    expect(when(DateTime(2026, 10, 17, 21, 6)), '24 min ago');
    expect(when(DateTime(2026, 10, 17, 18, 30)), 'Today 6:30pm');
    expect(when(DateTime(2026, 10, 16, 23, 59)), 'Yesterday 11:59pm');
    expect(when(DateTime(2026, 10, 13, 9, 0)), 'Tuesday 9:00am');
    expect(when(DateTime(2026, 10, 3, 18, 30)), 'Oct 3 · 6:30pm');
    expect(when(DateTime(2024, 10, 3, 18, 30)), 'Oct 3, 2024');
    expect(
      formatWhen(DateTime(2025, 12, 31, 22), now: DateTime(2026, 1, 1, 9)),
      'Yesterday 10:00pm',
    );
    expect(
      formatFullDate(DateTime(2026, 10, 17, 18, 30)),
      'Saturday, Oct 17, 2026 · 6:30pm',
    );
  });

  testWidgets('rank movement shows climbs, drops, holds, and new entries', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: const Scaffold(
          body: Column(
            children: [
              RankMovement(rank: 1, previousRank: 4),
              RankMovement(rank: 5, previousRank: 2),
              RankMovement(rank: 3, previousRank: 3),
              RankMovement(rank: 2),
            ],
          ),
        ),
      ),
    );
    expect(find.byIcon(Icons.arrow_upward_rounded), findsOneWidget);
    expect(find.byIcon(Icons.arrow_downward_rounded), findsOneWidget);
    expect(find.byIcon(Icons.remove_rounded), findsOneWidget);
    expect(find.text('3'), findsNWidgets(2)); // up three, down three
    expect(find.text('NEW'), findsOneWidget);
  });

  testWidgets('overview shows this year and earlier years on this day', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final now = DateTime.now();
    final paths = <String>[];
    final api = ScrobblerApi(
      baseUrl: Uri.parse('http://localhost:8000'),
      token: 'test',
      client: MockClient((request) async {
        paths.add(request.url.path);
        Object body = {};
        if (request.url.path == '/library/wrapped/${now.year}/') {
          body = {
            'year': now.year,
            'total_scrobbles': 4321,
            'daily': [
              {'date': '${now.year}-01-01', 'count': 5},
            ],
          };
        }
        if (request.url.path == '/library/on-this-day/') {
          body = {
            'date': request.url.queryParameters['date'],
            'years': [
              {
                'year': now.year - 2,
                'total_scrobbles': 12,
                'top_tracks': [
                  {
                    'name': 'Old favourite',
                    'artist': 'Band',
                    'album': null,
                    'count': 7,
                  },
                ],
              },
            ],
          };
        }
        return http.Response(jsonEncode(body), 200);
      }),
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark,
        home: Scaffold(body: OverviewPage(api: api, state: null)),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('4,321'), findsOneWidget);
    expect(find.text('2 YEARS AGO'), findsOneWidget);
    expect(find.text('Old favourite'), findsOneWidget);
    expect(find.text('×7'), findsOneWidget);
    expect(find.byType(ListeningHeatmap), findsOneWidget);
    expect(paths, contains('/library/on-this-day/'));
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    api.close();
  });

  testWidgets('artist page shows rank, first listen, years, and albums', (
    tester,
  ) async {
    for (final width in [1400.0, 700.0]) {
      tester.view.physicalSize = Size(width, 2400);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = ScrobblerApi(
        baseUrl: Uri.parse('http://localhost:8000'),
        token: 'test',
        client: MockClient((request) async {
          Object body = {};
          if (request.url.path == '/library/artists/') {
            body = {
              'artist': 'Band',
              'total_scrobbles': 400,
              'rank': 14,
              'first_scrobbled_at': '2011-03-04T20:00:00',
              'last_scrobbled_at': '2024-06-01T12:00:00',
              'first_track': {
                'name': 'Opening song',
                'album': 'Debut',
                'scrobbled_at': '2011-03-04T20:00:00',
              },
              'years': [
                {'year': 2011, 'count': 300},
                {'year': 2013, 'count': 100},
              ],
              'top_albums': [
                {'name': 'Debut', 'count': 200},
              ],
              'top_tracks': [
                {'name': 'Big single', 'album': 'Debut', 'count': 30},
              ],
            };
          }
          return http.Response(jsonEncode(body), 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark,
          home: ArtistDetailPage(api: api, artist: 'Band'),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('#14'), findsOneWidget);
      expect(find.text('Mar 2011'), findsOneWidget);
      expect(find.text('FIRST LISTEN'), findsOneWidget);
      expect(find.textContaining('Opening song'), findsOneWidget);
      expect(find.textContaining('Peak 2011'), findsOneWidget);
      // Years without listens still get a slot on the axis.
      expect(find.byTooltip('2012: 0 scrobbles'), findsOneWidget);
      expect(find.text('200 · 50%'), findsOneWidget);
      expect(find.text('Big single'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      api.close();
    }
  });
}
