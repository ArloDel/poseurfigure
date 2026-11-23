import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:figurepose/features/poses/domain/pose.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

Future<TestApp> open(WidgetTester tester, Analysis a) async {
  final app = TestApp(history: [a]);
  await app.pump(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/${a.id}');
  await tester.pumpAndSettle();
  return app;
}

Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 300, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Analysis withRefs({Map<String, dynamic>? progress}) => analysisResult('a1',
    character: 'Spider-Man (symbiote suit)', characterSource: 'ai',
    recommendations: [
      refJson(1, 7, changes: [
        {'joint': 'right_knee', 'action': 'bend', 'target': 90, 'current': 170, 'delta': -80, 'priority': 'high'},
      ]),
      recJson(2, 2, reasons: ['new_pose'], group: 'more'),
    ],
    references: progress ?? {'status': 'done', 'total': 20, 'checked': 20, 'found': 1});

void main() {
  test('a reference pose says where it is from', () {
    final p = Pose.fromJson(refJson(1, 7)['pose'] as Map<String, dynamic>);
    expect(p.isReference, isTrue);
    expect(p.meta, 'From Pinterest');
    expect(Pose.fromJson({'id': 1, 'slug': 's', 'name': 'n', 'category': 'action', 'difficulty': 'easy'}).isReference, isFalse);
  });

  testWidgets('a Pinterest idea is labelled and opens its own page with steps', (tester) async {
    await open(tester, withRefs());

    await scrollTo(tester, find.text('Pinterest'));
    expect(find.byTooltip('Save Spider-Man (symbiote suit) to favorites'), findsOneWidget);
    expect(find.byTooltip('Save Rifle aim to favorites'), findsOneWidget);
    expect(find.text('1 poses from Pinterest'), findsOneWidget);

    await tester.tap(find.text('Pinterest'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Found on Pinterest and kept for your own reference'), findsOneWidget);
    await scrollTo(tester, find.text('Bend the right knee about 80° more'));
    expect(find.text('From your figure'), findsOneWidget);
  });

  testWidgets('while the search runs, the app shows how far it is', (tester) async {
    // The spinner never settles, so pump fixed steps instead of pumpAndSettle.
    final app = TestApp(history: [withRefs(progress: {'status': 'running', 'total': 20, 'checked': 6, 'found': 2})]);
    await app.pump(tester);
    GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/a1');
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.scrollUntilVisible(find.text('Finding Spider-Man (symbiote suit) poses on Pinterest'), 300,
        scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('Checked 6 of 20 photos, 2 usable so far'), findsOneWidget);
    // It keeps refreshing while the search runs.
    final before = app.analyses.fetchCount;
    await tester.pump(const Duration(seconds: 6));
    expect(app.analyses.fetchCount, greaterThan(before));
    await tester.pumpWidget(const SizedBox()); // stop the refresh timer
  });

  testWidgets('a search that found nothing usable says so', (tester) async {
    await open(tester, withRefs(progress: {'status': 'done', 'total': 20, 'checked': 20, 'found': 0}));
    await scrollTo(tester, find.text('No usable Pinterest photos'));
  });

  testWidgets('a Pinterest pose is saved apart from a catalog pose with the same id, and opens from Favorites', (tester) async {
    // Reference 1 and catalog pose 1 share an id: saving one must not mark the other as saved.
    final app = TestApp(history: [analysisResult('a1', character: 'Spider-Man (symbiote suit)', characterSource: 'ai',
        recommendations: [refJson(1, 1), recJson(2, 1, reasons: ['new_pose'], group: 'more')])]);
    await app.pump(tester);
    await signIn(tester);
    GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/a1');
    await tester.pumpAndSettle();

    final refHeart = find.byTooltip('Save Spider-Man (symbiote suit) to favorites');
    await scrollTo(tester, refHeart);
    await tester.tap(refHeart);
    await tester.pumpAndSettle();
    expect(app.favorites.items.single.pose.isReference, isTrue);
    expect(find.byTooltip('Remove Spider-Man (symbiote suit) from favorites'), findsOneWidget);
    expect(find.byTooltip('Save Rider ready stance to favorites'), findsOneWidget); // the catalog pose 1 isn't saved

    GoRouter.of(tester.element(find.byType(Scaffold).first)).go('/favorites');
    await tester.pumpAndSettle();
    expect(find.text('Pinterest · 1'), findsOneWidget);
    await tester.tap(find.text('Spider-Man (symbiote suit)'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Found on Pinterest'), findsOneWidget);
    await scrollTo(tester, find.textContaining('Open this pose from an analysis'));
    expect(find.text('Saved to favorites'), findsOneWidget);
  });
}
