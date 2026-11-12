import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

Future<FakeAnalysisRepository> open(WidgetTester tester, Analysis a) async {
  final app = TestApp(history: [a]);
  await app.pump(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/${a.id}');
  await tester.pumpAndSettle();
  return app.analyses;
}

/// Scrolls until [f] is built, then fully on screen (scrollUntilVisible alone can stop with it below the edge).
Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 300, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

void main() {
  test('parses recommendations, reasons and basis', () {
    final a = analysisResult('x', typeOnly: true, recommendations: [
      recJson(1, 1, mirrored: true, reasons: ['mirror', 'check_joints'], warn: true),
    ]);
    final r = a.recommendations.single;
    expect(a.typeOnly, isTrue);
    expect(r.pose.name, 'Rider ready stance');
    expect(r.mirrored, isTrue);
    expect(r.reasons, ['mirror', 'check_joints']);
    expect(r.warnings.single.label, 'Left elbow 20° (limit about 35°)');
  });

  testWidgets('shows ranked poses with match, hold and reason chips', (tester) async {
    await open(tester, analysisResult('a1', recommendations: [
      recJson(1, 1, reasons: ['close_to_current']),
      recJson(2, 2, mirrored: true, reasons: ['mirror', 'different_category', 'check_joints'], warn: true),
    ]));

    await scrollTo(tester, find.text('Poses for your figure'));
    await scrollTo(tester, find.text('Rider ready stance'));
    expect(find.text('Close to your pose'), findsOneWidget);
    expect(find.text('Match to your figure'), findsWidgets);
    await scrollTo(tester, find.text('Rifle aim'));
    expect(find.text('Mirror it'), findsOneWidget);
    expect(find.text('Something different'), findsOneWidget);
    expect(find.text('Check joints'), findsOneWidget);
    expect(find.text('70%'), findsOneWidget);
  });

  testWidgets('an unreadable pose says so instead of showing match scores', (tester) async {
    await open(tester, analysisResult('a2', typeOnly: true, recommendations: [recJson(1, 1)]));

    await scrollTo(tester, find.textContaining("We couldn't read enough of your figure's joints"));
    await scrollTo(tester, find.text('Rider ready stance'));
    expect(find.text('Match to your figure'), findsNothing);
    expect(find.text('Likely to hold'), findsOneWidget);
  });

  testWidgets('a mirrored pick opens the detail with a mirror note', (tester) async {
    await open(tester, analysisResult('a3', recommendations: [recJson(1, 1, mirrored: true, reasons: ['mirror'])]));

    await scrollTo(tester, find.text('Rider ready stance'));
    await tester.tap(find.text('Rider ready stance'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.textContaining('Swap left and right'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Mirror it'), findsOneWidget);
  });

  testWidgets('show different poses replaces the list, then says when there are no more', (tester) async {
    final repo = await open(tester, analysisResult('a4', recommendations: [recJson(1, 1)]));
    repo.nextRecommendations = [recJson(1, 2, reasons: ['new_direction'])];

    await scrollTo(tester, find.text('Show different poses'));
    await tester.tap(find.text('Show different poses'));
    await tester.pumpAndSettle();

    expect(repo.showDifferentCalls, ['a4']);
    expect(find.text('Here are different poses'), findsOneWidget);
    await scrollTo(tester, find.text('Rifle aim'));
    expect(find.text('Rider ready stance'), findsNothing);
    await scrollTo(tester, find.textContaining("That's every pose we have"));
  });
}
