import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/analysis/presentation/analysis_screen.dart';
import '../../features/auth/presentation/sign_in_screen.dart';
import '../../features/favorites/presentation/favorites_screen.dart';
import '../../features/history/presentation/history_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/poses/presentation/discover_screen.dart';
import '../../features/poses/presentation/pose_detail_screen.dart';
import '../../features/profile/presentation/profile_screen.dart';
import '../../shared/widgets/app_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => AppShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [GoRoute(path: '/', builder: (_, _) => const HomeScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/discover', builder: (_, _) => const DiscoverScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/favorites', builder: (_, _) => const FavoritesScreen())]),
          StatefulShellBranch(routes: [GoRoute(path: '/profile', builder: (_, _) => const ProfileScreen())]),
        ],
      ),
      GoRoute(
        path: '/poses/:id',
        builder: (_, state) => PoseDetailScreen(poseId: int.parse(state.pathParameters['id']!)),
      ),
      GoRoute(path: '/history', builder: (_, _) => const HistoryScreen()),
      GoRoute(
        path: '/sign-in',
        builder: (_, state) => SignInScreen(
          initialMode: state.uri.queryParameters['mode'] == 'register' ? SignInMode.register : SignInMode.signIn,
        ),
      ),
      GoRoute(
        path: '/analysis/:id',
        builder: (_, state) => AnalysisScreen(
          analysisId: state.pathParameters['id']!,
          photo: state.extra is Uint8List ? state.extra as Uint8List : null,
        ),
      ),
    ],
  );
});
