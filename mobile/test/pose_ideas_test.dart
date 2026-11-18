import 'package:figurepose/features/analysis/domain/analysis.dart';
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

void main() {
  test('parses the character, recognition and idea groups', () {
    final a = analysisResult('x', recommendations: ideaRecs(same: true), character: 'Spider-Man', characterSource: 'ai', recognition: true);
    expect(a.characterName, 'Spider-Man');
    expect(a.characterSource, 'ai');
    expect(a.recognitionAvailable, isTrue);
    expect(a.recognitionProvider, 'OpenAI');
    expect(a.recommendations.map((r) => r.group), ['same_character', 'more']);
  });

  testWidgets('ideas are shown as a grid grouped by why they are there', (tester) async {
    await open(tester, analysisResult('a1', recommendations: ideaRecs(same: true), character: 'Spider-Man', characterSource: 'user'));

    await scrollTo(tester, find.text('Pose ideas for your figure'));
    expect(find.text('Same character'), findsWidgets); // section title and the tile's chip
    await scrollTo(tester, find.text('More ideas'));
    expect(find.text('Rider ready stance'), findsOneWidget);
    expect(find.text('Rifle aim'), findsOneWidget);
    expect(find.text('Match to your figure'), findsNothing); // the old, pose-matched cards are gone
  });

  testWidgets('without poses of the character, the app says so', (tester) async {
    await open(tester, analysisResult('a1', recommendations: ideaRecs(), character: 'Spider-Man', characterSource: 'user'));
    await scrollTo(tester, find.textContaining('No Spider-Man poses in our collection yet'));
    expect(find.text('Figures that look like yours'), findsOneWidget);
  });

  testWidgets('recognizing the character asks first, then shows that character first', (tester) async {
    final app = await open(tester, analysisResult('a1', recommendations: ideaRecs(), recognition: true));

    await scrollTo(tester, find.text('Who is this figure?'));
    await tester.tap(find.text('Recognize it'));
    await tester.pumpAndSettle();
    expect(find.text('Your photo goes to OpenAI, an image service outside FigurePose.'), findsOneWidget);
    await tester.tap(find.text('Not now'));
    await tester.pumpAndSettle();
    expect(app.analyses.characterCalls, isEmpty);

    await tester.tap(find.text('Recognize it'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Send'));
    await tester.pumpAndSettle();

    expect(app.analyses.characterCalls.single, ('a1', 'recognize'));
    expect(find.text('Spider-Man (symbiote suit)'), findsOneWidget);
    expect(find.textContaining('Suggested by OpenAI. It can be wrong.'), findsOneWidget);
  });

  testWidgets('without recognition the user types the name, and can change it', (tester) async {
    final app = await open(tester, analysisResult('a1', recommendations: ideaRecs()));

    await scrollTo(tester, find.text('Who is this figure?'));
    expect(find.text('Recognize it'), findsNothing);
    await tester.tap(find.text('Type the name'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '  Spider-Man ');
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();

    expect(app.analyses.characterCalls.single, ('a1', 'Spider-Man'));
    expect(find.text('Spider-Man'), findsOneWidget);
    expect(find.textContaining('Named by you.'), findsOneWidget);

    await tester.tap(find.text('Change'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Clear'));
    await tester.pumpAndSettle();
    expect(app.analyses.characterCalls.last, ('a1', null));
    expect(find.text('Who is this figure?'), findsOneWidget);
  });
}
