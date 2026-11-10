import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

Future<void> signIn(WidgetTester tester, {String password = FakeAuthRepository.password}) async {
  await openTab(tester, 'Profile');
  await tester.tap(find.text('Sign in').last);
  await tester.pumpAndSettle();
  await tester.enterText(find.widgetWithText(TextFormField, 'Email'), FakeAuthRepository.email);
  await tester.enterText(find.widgetWithText(TextFormField, 'Password'), password);
  await tester.tap(find.text('Sign in').last);
  await tester.pumpAndSettle();
}

void main() {
  group('Pose gallery', () {
    testWidgets('lists poses and filters by category and figure type', (tester) async {
      final app = TestApp();
      await app.pump(tester);
      await openTab(tester, 'Discover');

      expect(find.text('Rider ready stance'), findsOneWidget);
      expect(find.text('Rifle aim'), findsOneWidget);
      expect(find.text('2 poses, each with joint steps.'), findsOneWidget);

      await tester.tap(find.text('Cinematic'));
      await tester.pumpAndSettle();
      expect(find.text('Rider ready stance'), findsNothing);
      expect(find.text('Rifle aim'), findsOneWidget);

      await tester.tap(find.text('Humanoid'));
      await tester.pumpAndSettle();
      expect(find.text('No poses match'), findsOneWidget);
      expect(app.poses.queries.last.profile, 'humanoid_v1');
      expect(app.poses.queries.last.category, 'cinematic');
    });

    testWidgets('pose detail shows steps by body region and joint warnings', (tester) async {
      await TestApp().pump(tester);
      await openTab(tester, 'Discover');
      await tester.tap(find.text('Rider ready stance'));
      await tester.pumpAndSettle();

      expect(find.text('Catalog reference'), findsOneWidget);
      final list = find.byType(Scrollable).first;
      await tester.scrollUntilVisible(find.text('Bend the right knee'), 200, scrollable: list);
      expect(find.text('Head and torso'), findsOneWidget);
      expect(find.text('Legs'), findsOneWidget);
      expect(find.text('120°'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('Right knee may not bend this far'), 200, scrollable: list);
      await tester.scrollUntilVisible(find.textContaining('Photo: "Ichigo"'), 200, scrollable: list);
    });

    testWidgets('guests are asked to sign in before saving a favorite', (tester) async {
      final app = TestApp();
      await app.pump(tester);
      await openTab(tester, 'Discover');
      await tester.tap(find.text('Rifle aim'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Save to favorites'));
      await tester.pump();

      expect(find.text('Sign in to save poses to your favorites.'), findsOneWidget);
      expect(app.favorites.items, isEmpty);
    });
  });

  group('Account', () {
    testWidgets('wrong password shows the server message', (tester) async {
      await TestApp().pump(tester);
      await signIn(tester, password: 'wrong-password');

      expect(find.text("That email and password don't match."), findsOneWidget);
      expect(find.text('Welcome back'), findsOneWidget);
    });

    testWidgets('signing in shows the account and moved analyses, signing out returns to guest', (tester) async {
      await TestApp().pump(tester);
      await signIn(tester);

      expect(find.text('Signed in. 2 analyses moved to your account.'), findsOneWidget);
      expect(find.text('Rina Collector'), findsOneWidget);

      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();
      expect(find.text('Guest collector'), findsOneWidget);
    });

    testWidgets('create account mode asks for a name and a longer password', (tester) async {
      await TestApp().pump(tester);
      await openTab(tester, 'Profile');
      await tester.tap(find.text('Create account'));
      await tester.pumpAndSettle();

      expect(find.text('Create your account'), findsOneWidget);
      await tester.enterText(find.widgetWithText(TextFormField, 'Email'), 'new@example.com');
      await tester.enterText(find.widgetWithText(TextFormField, 'Password'), 'short');
      await tester.tap(find.text('Create account').last);
      await tester.pumpAndSettle();

      expect(find.text('Enter your name.'), findsOneWidget);
      expect(find.text('Use at least 8 characters.'), findsOneWidget);
    });
  });

  group('Favorites', () {
    testWidgets('guests see a sign-in prompt', (tester) async {
      await TestApp().pump(tester);
      await openTab(tester, 'Favorites');

      expect(find.text('Sign in to save poses'), findsOneWidget);
    });

    testWidgets('signed-in user saves a pose, sees it in Favorites and removes it', (tester) async {
      final app = TestApp();
      await app.pump(tester);
      await signIn(tester);

      await openTab(tester, 'Favorites');
      expect(find.text('No saved poses yet'), findsOneWidget);

      await openTab(tester, 'Discover');
      await tester.tap(find.text('Rifle aim'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save to favorites'));
      await tester.pumpAndSettle();
      expect(find.text('Saved to favorites'), findsWidgets);
      expect(app.favorites.items.single.pose.id, 2);

      await tester.tap(find.byIcon(Icons.arrow_back_rounded));
      await tester.pumpAndSettle();
      await openTab(tester, 'Favorites');
      expect(find.text('1 saved pose'), findsOneWidget);
      expect(find.text('Rifle aim'), findsOneWidget);

      await tester.tap(find.byTooltip('Remove Rifle aim from favorites'));
      await tester.pumpAndSettle();
      expect(find.text('No saved poses yet'), findsOneWidget);
      expect(app.favorites.items, isEmpty);
    });
  });

  group('History', () {
    Analysis analysis(String id, AnalysisStatus status, {String? errorCode}) =>
        Analysis(id: id, status: status, errorCode: errorCode, createdAt: DateTime.now());

    testWidgets('lists analyses and deletes one after confirming', (tester) async {
      final app = TestApp(history: [
        analysis('a1', AnalysisStatus.completed),
        analysis('a2', AnalysisStatus.failed, errorCode: 'blurry'),
      ]);
      await app.pump(tester);
      await tester.tap(find.byTooltip('History'));
      await tester.pumpAndSettle();

      expect(find.text('Completed, photo checked'), findsOneWidget);
      expect(find.text('Failed, photo too blurry'), findsOneWidget);
      expect(find.textContaining('Today'), findsNWidgets(2));

      await tester.tap(find.byTooltip('Delete analysis and photo').last);
      await tester.pumpAndSettle();
      expect(find.text('Delete this analysis?'), findsOneWidget);
      await tester.tap(find.text('Cancel'));
      await tester.pumpAndSettle();
      expect(app.analyses.deleted, isEmpty);

      await tester.tap(find.byTooltip('Delete analysis and photo').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Delete'));
      await tester.pumpAndSettle();

      expect(app.analyses.deleted, ['a2']);
      expect(find.text('Failed, photo too blurry'), findsNothing);
      expect(find.text('Analysis and photo deleted'), findsOneWidget);
    });

    testWidgets('empty history invites a first analysis', (tester) async {
      await TestApp().pump(tester);
      await tester.tap(find.byTooltip('History'));
      await tester.pumpAndSettle();

      expect(find.text('No analyses yet'), findsOneWidget);
      expect(find.text('Analyze a figure'), findsOneWidget);
    });
  });
}
