import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

Future<TestApp> openPose(WidgetTester tester, String location) async {
  final app = TestApp();
  await app.pump(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push(location);
  await tester.pumpAndSettle();
  return app;
}

Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 300, scrollable: find.byType(Scrollable).first);
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

Future<void> agree(WidgetTester tester) async {
  await scrollTo(tester, find.text('Make AI visual'));
  await tester.tap(find.text('Make AI visual'));
  await tester.pumpAndSettle();
  expect(find.text('Send your photo for an AI visual?'), findsOneWidget);
  await tester.tap(find.text('Send and make'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400)); // sheet closes
}

void main() {
  test('parses status, validation and the stub flag', () {
    final v = FakeVisualRepository.visual('generated', 'rejected');
    expect(v.isReady, isTrue);
    expect(v.validationLabel, 'Pose check failed');
    expect(v.isStub, isTrue);
    expect(FakeVisualRepository.visual('pending', 'unvalidated').isPending, isTrue);
  });

  testWidgets('a pose opened from the gallery has no AI visual section', (tester) async {
    await openPose(tester, '/poses/1');
    await scrollTo(tester, find.textContaining('Photo: "Ichigo"'));
    expect(find.text('Make AI visual'), findsNothing);
  });

  testWidgets('nothing is sent unless the user agrees', (tester) async {
    final app = await openPose(tester, '/poses/1?analysis=a1');
    await scrollTo(tester, find.text('Make AI visual'));
    await tester.tap(find.text('Make AI visual'));
    await tester.pumpAndSettle();

    expect(find.text('Your photo goes to an image service outside FigurePose.'), findsOneWidget);
    await tester.tap(find.text('Not now'));
    await tester.pumpAndSettle();

    expect(app.visuals.requests, isEmpty);
    expect(find.text('Make AI visual'), findsOneWidget);
  });

  testWidgets('after agreeing, the visual is labelled AI-generated with its pose check', (tester) async {
    final app = await openPose(tester, '/poses/1?analysis=a1&mirrored=1');
    await agree(tester);
    await tester.pumpAndSettle();

    expect(app.visuals.requests.single, (poseId: 1, analysisId: 'a1', mirrored: true));
    await scrollTo(tester, find.text('AI-generated'));
    expect(find.text('Pose checked'), findsOneWidget);
    expect(find.textContaining('It is not proof your figure can hold it'), findsOneWidget);
    expect(find.textContaining('Development preview'), findsOneWidget);
    expect(find.text('Make AI visual'), findsNothing);
  });

  testWidgets('a pending visual is polled until it is ready, and a rejected one says so', (tester) async {
    final app = TestApp();
    app.visuals.first = FakeVisualRepository.visual('pending', 'unvalidated');
    app.visuals.later.add(FakeVisualRepository.visual('generated', 'rejected', provider: 'real'));
    await app.pump(tester);
    GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/poses/1?analysis=a1');
    await tester.pumpAndSettle();
    await agree(tester);

    expect(find.text('Making your AI visual'), findsOneWidget);
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();

    await scrollTo(tester, find.text('Pose check failed'));
    expect(find.textContaining("doesn't show the target pose reliably"), findsOneWidget);
    expect(find.textContaining('Development preview'), findsNothing);
  });

  testWidgets('a failed visual explains and offers another try', (tester) async {
    final app = TestApp();
    app.visuals.first = FakeVisualRepository.visual('failed', 'unvalidated', error: "We couldn't make this visual. Try again in a few minutes.");
    await app.pump(tester);
    GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/poses/1?analysis=a1');
    await tester.pumpAndSettle();
    await agree(tester);
    await tester.pumpAndSettle();

    await scrollTo(tester, find.text('Try again'));
    expect(find.textContaining("We couldn't make this visual"), findsOneWidget);
    expect(find.text('AI-generated'), findsNothing);
  });
}
