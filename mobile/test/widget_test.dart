import 'dart:math';

import 'package:figurepose/core/storage/guest_key.dart';
import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  testWidgets('launches on Home with the analyze actions and four tabs', (tester) async {
    await TestApp().pump(tester);

    expect(find.text('Ready to pose?'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Server connected'), findsOneWidget);
    for (final tab in ['Home', 'Discover', 'Favorites', 'Profile']) {
      expect(find.text(tab), findsWidgets);
    }
  });

  testWidgets('theme uses the comic display font for headlines', (tester) async {
    await TestApp().pump(tester);
    final ctx = tester.element(find.byType(Scaffold).first);
    expect(Theme.of(ctx).textTheme.headlineMedium?.fontFamily, 'BowlbyOne');
  });

  test('guest key is a valid UUID v4', () {
    final key = uuidV4(Random(1));
    expect(RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$').hasMatch(key), isTrue);
  });

  test('parses a failed analysis with its reason', () {
    final a = Analysis.fromJson({
      'analysis_id': 'abc',
      'status': 'failed',
      'created_at': '2026-11-08T10:31:14+00:00',
      'error': {'code': 'blurry', 'message': 'Too blurry.', 'retryable': false},
      'quality': {'ok': false, 'sharpness': 12.3, 'issues': [{'code': 'blurry', 'message': 'Too blurry.'}]},
    });
    expect(a.status, AnalysisStatus.failed);
    expect(a.status.isFinal, isTrue);
    expect(a.errorCode, 'blurry');
    expect(a.issues.single.code, 'blurry');
    expect(a.createdAt, DateTime.utc(2026, 11, 8, 10, 31, 14));
  });
}
