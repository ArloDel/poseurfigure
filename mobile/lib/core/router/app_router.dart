import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/analysis/presentation/analysis_screen.dart';
import '../../features/home/presentation/home_screen.dart';
import '../../features/placeholder/placeholder_screen.dart';
import '../../shared/widgets/app_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => AppShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [GoRoute(path: '/', builder: (_, _) => const HomeScreen())]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/discover', builder: (_, _) => const PlaceholderScreen(
              title: 'Pose gallery', message: 'Browse 3 profiles worth of poses here. Coming in Sprint 3.')),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/favorites', builder: (_, _) => const PlaceholderScreen(
              title: 'Favorites', message: 'Tap the heart on any pose to keep it here.')),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, _) => const PlaceholderScreen(
              title: 'Profile', message: "You're using FigurePose as a guest. Accounts arrive in Sprint 2.")),
          ]),
        ],
      ),
      GoRoute(
        path: '/analysis/:id',
        builder: (_, state) => AnalysisScreen(analysisId: state.pathParameters['id']!),
      ),
    ],
  );
});
