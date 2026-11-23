import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

Future<TestApp> openResults(WidgetTester tester, {bool signedIn = false}) async {
  final app = TestApp(history: [analysisResult('a1', recommendations: [recJson(1, 1), recJson(2, 2)])]);
  await app.pump(tester);
  if (signedIn) await signIn(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/a1');
  await tester.pumpAndSettle();
  return app;
}

Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 300, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

void main() {
  group('Saving from a recommendation card', () {
    testWidgets('guests are asked to sign in and nothing is saved', (tester) async {
      final app = await openResults(tester);
      final heart = find.byTooltip('Save Rider ready stance to favorites');
      await scrollTo(tester, heart);
      await tester.tap(heart);
      await tester.pump();

      expect(find.text('Sign in to save poses to your favorites.'), findsOneWidget);
      expect(app.favorites.items, isEmpty);
    });

    testWidgets('signed in, the heart saves the pose without opening it, and removes it again', (tester) async {
      final app = await openResults(tester, signedIn: true);
      final heart = find.byTooltip('Save Rifle aim to favorites');
      await scrollTo(tester, heart);
      await tester.tap(heart);
      await tester.pumpAndSettle();

      expect(app.favorites.items.single.pose.id, 2);
      expect(find.text('Poses for your figure'), findsOneWidget); // still on the results
      final saved = find.byTooltip('Remove Rifle aim from favorites');
      expect(saved, findsOneWidget);

      await tester.tap(saved);
      await tester.pumpAndSettle();
      expect(app.favorites.items, isEmpty);
    });
  });

  testWidgets('favorites are grouped by category, newest group first', (tester) async {
    final app = TestApp();
    await app.pump(tester);
    await app.favorites.add(samplePoses[0]); // action
    await app.favorites.add(samplePoses[1]); // cinematic, saved later
    await signIn(tester);
    await openTab(tester, 'Favorites');
    await tester.pumpAndSettle();

    expect(find.text('2 saved poses'), findsOneWidget);
    final cinematic = tester.getTopLeft(find.text('Cinematic · 1')).dy;
    final action = tester.getTopLeft(find.text('Action · 1')).dy;
    expect(cinematic, lessThan(action));
    expect(tester.getTopLeft(find.text('Rifle aim')).dy, lessThan(action));
    expect(tester.getTopLeft(find.text('Rider ready stance')).dy, greaterThan(action));
  });
}
