import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:py_scrobbler_desktop/features/listening/listening_timeline.dart';

void main() {
  testWidgets('timeline fills gaps and exposes exact counts and peak ties', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ListeningTimeline(
            currentYear: 2026,
            track: [
              {'year': 2023, 'count': 4},
              {'year': 2025, 'count': 4},
            ],
            album: null,
            artist: [
              {'year': 2023, 'count': 30},
              {'year': 2026, 'count': 20},
            ],
          ),
        ),
      ),
    );
    expect(find.text('2024'), findsOneWidget);
    expect(find.byTooltip('Track · 2024: 0 scrobbles'), findsOneWidget);
    expect(find.byTooltip('Artist · 2026: 20 scrobbles'), findsOneWidget);
    expect(find.text('2 peak years'), findsOneWidget);
    expect(find.text('Peak 2023'), findsOneWidget);
    expect(find.text('Album'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('long timelines fit narrow windows without overflow', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 320,
            child: ListeningTimeline(
              currentYear: 2026,
              track: const [],
              album: const [],
              artist: [
                for (var year = 2000; year <= 2026; year++)
                  {'year': year, 'count': year - 1999},
              ],
            ),
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    await tester.drag(
      find.byType(SingleChildScrollView),
      const Offset(-1600, 0),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
