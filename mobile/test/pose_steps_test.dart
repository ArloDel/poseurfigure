import 'package:figurepose/features/analysis/domain/recommendation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

Map<String, dynamic> change(String joint, String action, {num? current, num? target, num? delta, String priority = 'low'}) =>
    {'joint': joint, 'action': action, 'current': current, 'target': target, 'delta': delta, 'priority': priority};

final steps = [
  change('right_shoulder', 'raise', current: 20, target: 110, delta: 90, priority: 'high'),
  change('left_elbow', 'keep', current: 150, target: 155, delta: 5),
  change('right_knee', 'bend', current: 170, target: 128, delta: -42, priority: 'medium'),
  change('left_knee', 'unknown', target: 120),
];

Future<void> open(WidgetTester tester, String location, {bool mirrored = false, List<Map<String, dynamic>>? changes}) async {
  final app = TestApp(history: [analysisResult('a1', recommendations: [recJson(1, 1, mirrored: mirrored, changes: changes ?? steps)])]);
  await app.pump(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push(location);
  await tester.pumpAndSettle();
}

void main() {
  test('a change reads as a sentence about the part that moves, in 5 degree steps', () {
    JointChange c(Map<String, dynamic> j) => JointChange.fromJson(j);
    expect(c(change('right_knee', 'bend', delta: -42)).sentence, 'Bend the right knee about 40° more');
    expect(c(change('left_elbow', 'straighten', delta: 33)).sentence, 'Straighten the left elbow about 35°');
    expect(c(change('right_shoulder', 'raise', delta: 90)).sentence, 'Raise the right arm about 90°');
    expect(c(change('left_hip', 'lift_leg', delta: -14)).sentence, 'Lift the left leg about 15°');
    expect(c(change('left_hip', 'lower_leg', delta: 2)).sentence, 'Lower the left leg about 5°');
    expect(c(change('left_knee', 'keep')).isMove, isFalse);
    expect(c(change('left_knee', 'unknown')).isMove, isFalse);
  });

  testWidgets('opened from an analysis, the moves come first and the rest is summed up', (tester) async {
    await open(tester, '/poses/1?analysis=a1');

    expect(find.text('From your figure'), findsOneWidget);
    expect(find.text('Raise the right arm about 90°'), findsOneWidget);
    expect(find.text('Now about 20°, target 110°'), findsOneWidget);
    expect(find.text('BIG MOVE'), findsOneWidget);
    expect(find.text('Bend the right knee about 40° more'), findsOneWidget);
    expect(find.text('Already in place: Left elbow'), findsOneWidget);
    expect(find.textContaining('Not visible in your photo: Left knee'), findsOneWidget);
    expect(find.text('Reference steps'), findsOneWidget);
    expect(find.text('How to pose it'), findsNothing);
  });

  testWidgets('a figure already in the pose is told so', (tester) async {
    await open(tester, '/poses/1?analysis=a1', changes: [change('left_elbow', 'keep', current: 150, target: 155, delta: 5)]);
    expect(find.textContaining('already in this pose'), findsOneWidget);
  });

  testWidgets('mirrored: the note says the personal steps already use the figure\'s sides', (tester) async {
    await open(tester, '/poses/1?analysis=a1&mirrored=1', mirrored: true);
    await tester.scrollUntilVisible(find.text('Mirror it'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('already use your figure\'s left and right'), findsOneWidget);
  });

  testWidgets('opened from the gallery, only the catalog steps show', (tester) async {
    await open(tester, '/poses/1');
    expect(find.text('From your figure'), findsNothing);
    expect(find.text('How to pose it'), findsOneWidget);
  });

  testWidgets('if the analysis is gone, the catalog steps still show', (tester) async {
    await open(tester, '/poses/1?analysis=deleted');
    expect(find.text('From your figure'), findsNothing);
    expect(find.text('How to pose it'), findsOneWidget);
  });
}
