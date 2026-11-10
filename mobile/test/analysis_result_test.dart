import 'dart:typed_data';

import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:figurepose/features/analysis/presentation/widgets/skeleton_overlay.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'helpers.dart';

// A 1x1 transparent PNG, standing in for the uploaded photo.
final _png = Uint8List.fromList([
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01,
  0x00, 0x00, 0x00, 0x01, 0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41,
  0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49,
  0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
]);

Future<FakeAnalysisRepository> openResult(WidgetTester tester, Analysis analysis, {Uint8List? photo}) async {
  final app = TestApp(history: [analysis]);
  await app.pump(tester);
  GoRouter.of(tester.element(find.byType(Scaffold).first)).push('/analysis/${analysis.id}', extra: photo);
  await tester.pumpAndSettle();
  return app.analyses;
}

void main() {
  test('parses type, pose and photo size from the API', () {
    final a = analysisResult('x', profile: 'mecha_v1', confidence: 0.45, needsConfirmation: true);
    expect(a.typeGuess!.profile, 'mecha_v1');
    expect(a.typeGuess!.needsConfirmation, isTrue);
    expect(a.pose!.visibleCount, 15);
    expect(a.pose!.joints['left_wrist']!.hasPosition, isFalse);
    expect(a.pose!.hiddenSummary, 'Left wrist hidden');
    expect(a.imageWidth! / a.imageHeight!, 0.75);
    expect(a.figureCount, 1);
  });

  testWidgets('shows the figure type, joints found, hidden joints and angles', (tester) async {
    await openResult(tester, analysisResult('a1'));

    expect(find.text('Your figure'), findsOneWidget);
    expect(find.text('Humanoid figure'), findsOneWidget);
    expect(find.text('90% sure. Wrong? Pick another type.'), findsOneWidget);
    expect(find.text('15 of 16 joints found'), findsOneWidget);
    expect(find.text('Left wrist hidden'), findsOneWidget);
    expect(find.text('Right elbow'), findsOneWidget);
    expect(find.text('95°'), findsOneWidget);
    // Opened without the local photo (as from History): no overlay.
    expect(find.byType(SkeletonOverlay), findsNothing);
  });

  testWidgets('draws the skeleton on the photo right after upload', (tester) async {
    await openResult(tester, analysisResult('a1'), photo: _png);

    expect(find.byType(SkeletonOverlay), findsOneWidget);
  });

  testWidgets('unsure type asks the user, and picking one re-runs the analysis', (tester) async {
    final repo = await openResult(tester, analysisResult('a2', profile: 'humanoid_v1', confidence: 0.45, needsConfirmation: true));

    expect(find.text('Is this a humanoid figure?'), findsOneWidget);
    expect(find.textContaining("We're not sure (45%)"), findsOneWidget);

    await tester.tap(find.text('Mecha / robot'));
    await tester.pumpAndSettle();

    expect(repo.confirmed, [('a2', 3)]);
    expect(find.text('Mecha / robot figure'), findsOneWidget);
    expect(find.text('You picked this type.'), findsOneWidget);
  });
}
