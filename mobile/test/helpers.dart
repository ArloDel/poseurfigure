import 'package:figurepose/core/network/api_client.dart';
import 'package:figurepose/features/analysis/data/analysis_repository.dart';
import 'package:figurepose/features/analysis/domain/analysis.dart';
import 'package:figurepose/features/auth/data/auth_repository.dart';
import 'package:figurepose/features/auth/domain/app_user.dart';
import 'package:figurepose/features/favorites/data/favorites_repository.dart';
import 'package:figurepose/features/poses/data/pose_repository.dart';
import 'package:figurepose/features/poses/domain/pose.dart';
import 'package:figurepose/main.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart' show Override;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';

final samplePoses = [
  Pose.fromJson({
    'id': 1,
    'slug': 'rider-ready-stance',
    'name': 'Rider ready stance',
    'category': 'action',
    'difficulty': 'medium',
    'profile': 'humanoid_v1',
    'description': 'A low, wide fighting stance.',
    'image_credit': {'title': 'Ichigo', 'creator': 'Fuyoh!', 'license': 'CC BY 2.0'},
    'instructions': [
      {'step': 2, 'body_part': 'right_knee', 'movement': 'bend', 'target_angle': 120, 'priority': 'high'},
      {'step': 1, 'body_part': 'torso', 'movement': 'twist', 'target_angle': 25, 'priority': 'high'},
      {'step': 3, 'body_part': 'right_elbow', 'movement': 'bend', 'target_angle': 95, 'priority': 'high'},
    ],
    'constraints': {
      'right_knee': {'target': 120, 'warn_above_profile_max': true},
    },
  }),
  Pose.fromJson({
    'id': 2,
    'slug': 'rifle-aim',
    'name': 'Rifle aim',
    'category': 'cinematic',
    'difficulty': 'medium',
    'profile': 'mecha_v1',
    'instructions': [
      {'step': 1, 'body_part': 'right_shoulder', 'movement': 'raise', 'target_angle': 85},
    ],
  }),
];

class FakePoseRepository implements PoseRepository {
  final queries = <PoseQuery>[];

  @override
  Future<List<Pose>> list([PoseQuery query = const PoseQuery()]) async {
    queries.add(query);
    return samplePoses
        .where((p) =>
            (query.profile == null || p.profile == query.profile) &&
            (query.category == null || p.category == query.category) &&
            p.name.toLowerCase().contains(query.text.toLowerCase()))
        .toList();
  }

  @override
  Future<Pose> detail(int id) async => samplePoses.firstWhere((p) => p.id == id);
}

class FakeAuthRepository implements AuthRepository {
  static const email = 'rina@example.com';
  static const password = 'figure-shelf-42';
  AppUser? current;

  @override
  Future<AuthResult> login({required String email, required String password}) async {
    if (email != FakeAuthRepository.email || password != FakeAuthRepository.password) {
      throw ApiException("That email and password don't match.", statusCode: 422);
    }
    current = const AppUser(id: 7, name: 'Rina Collector', email: FakeAuthRepository.email);
    return AuthResult(token: 'token-7', user: current!, claimedAnalyses: 2);
  }

  @override
  Future<AuthResult> register({required String name, required String email, required String password}) async {
    current = AppUser(id: 8, name: name, email: email);
    return AuthResult(token: 'token-8', user: current!);
  }

  @override
  Future<AppUser> me() async => current ?? (throw ApiException('Unauthenticated.', statusCode: 401));

  @override
  Future<void> logout() async => current = null;
}

class FakeFavoritesRepository implements FavoritesRepository {
  final items = <FavoriteItem>[];
  int _nextId = 1;

  @override
  Future<List<FavoriteItem>> list() async => List.of(items);

  @override
  Future<FavoriteItem> add(int poseId) async {
    final item = FavoriteItem(id: _nextId++, pose: samplePoses.firstWhere((p) => p.id == poseId));
    items.add(item);
    return item;
  }

  @override
  Future<void> remove(int favoriteId) async => items.removeWhere((f) => f.id == favoriteId);
}

class FakeAnalysisRepository implements AnalysisRepository {
  FakeAnalysisRepository([List<Analysis>? history]) : items = history ?? [];

  final List<Analysis> items;
  final deleted = <String>[];

  @override
  Future<List<Analysis>> history() async => List.of(items);

  @override
  Future<void> delete(String id) async {
    deleted.add(id);
    items.removeWhere((a) => a.id == id);
  }

  @override
  Future<Analysis> fetch(String id) async => items.firstWhere((a) => a.id == id);

  @override
  Future<String> start(XFile photo, {int? profileId}) async => 'new-analysis';

  @override
  Future<bool> serverHealthy() async => true;

  final confirmed = <(String, int)>[];

  @override
  Future<Map<String, int>> profileIds() async => {'humanoid_v1': 1, 'anime_v1': 2, 'mecha_v1': 3};

  @override
  Future<void> confirmProfile(String id, int profileId) async {
    confirmed.add((id, profileId));
    // The server re-analyzes with the chosen type; the next fetch returns that result.
    final i = items.indexWhere((a) => a.id == id);
    if (i >= 0) items[i] = analysisResult(id, profile: {1: 'humanoid_v1', 2: 'anime_v1', 3: 'mecha_v1'}[profileId]!, byUser: true);
  }
}

/// A completed analysis as the API returns it.
Analysis analysisResult(String id, {String profile = 'humanoid_v1', double confidence = 0.9, bool needsConfirmation = false, bool byUser = false}) {
  Map<String, dynamic> kp(double x, double y, [String vis = 'visible']) => {'x': x, 'y': y, 'confidence': 0.9, 'visibility': vis};
  return Analysis.fromJson({
    'analysis_id': id,
    'status': 'completed',
    'profile': profile,
    'created_at': DateTime.now().toIso8601String(),
    'image': {'width': 900, 'height': 1200},
    'figures': [{'bbox': [0.2, 0.1, 0.8, 0.95], 'score': 0.7}],
    'classification': {'profile': profile, 'confidence': byUser ? 1.0 : confidence, 'needs_confirmation': needsConfirmation,
      'source': byUser ? 'user' : 'model'},
    'pose': {
      'visible_count': 15,
      'hidden': ['left_wrist'],
      'orientation': 'front',
      'joint_angles': {'right_elbow': 95.4, 'left_knee': 171.0},
      'keypoints': {
        for (final (i, n) in const [
          'head', 'neck', 'chest', 'waist', 'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
          'left_wrist', 'right_wrist', 'left_hip', 'right_hip', 'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
        ].indexed)
          n: n == 'left_wrist'
              ? {'x': null, 'y': null, 'confidence': 0.1, 'visibility': 'not_visible'}
              : kp(0.3 + 0.02 * i, 0.1 + 0.05 * i),
      },
    },
  });
}

class TestApp {
  TestApp({List<Analysis>? history}) : analyses = FakeAnalysisRepository(history);

  final poses = FakePoseRepository();
  final auth = FakeAuthRepository();
  final favorites = FakeFavoritesRepository();
  final FakeAnalysisRepository analyses;

  List<Override> get overrides => [
        poseRepositoryProvider.overrideWithValue(poses),
        authRepositoryProvider.overrideWithValue(auth),
        favoritesRepositoryProvider.overrideWithValue(favorites),
        analysisRepositoryProvider.overrideWithValue(analyses),
      ];

  /// Pumps the real app on a phone-sized screen with fake repositories and an empty keychain.
  Future<void> pump(WidgetTester tester) async {
    FlutterSecureStorage.setMockInitialValues({});
    tester.view.physicalSize = const Size(1170, 2532);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(ProviderScope(
      overrides: overrides,
      retry: (_, _) => null,
      child: const FigurePoseApp(),
    ));
    await tester.pumpAndSettle();
  }
}

Future<void> openTab(WidgetTester tester, String label) async {
  await tester.tap(find.descendant(of: find.byType(Semantics), matching: find.text(label)).last);
  await tester.pumpAndSettle();
}
