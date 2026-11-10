import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/comic_panel.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/pose_photo.dart';
import '../../../shared/widgets/state_panels.dart';
import '../../auth/application/session_controller.dart';
import '../application/favorites_controller.dart';
import '../data/favorites_repository.dart';

/// Saved poses (FAV-01..03). Needs an account so favorites follow the user across devices.
class FavoritesScreen extends ConsumerWidget {
  const FavoritesScreen({super.key});

  Future<void> _remove(BuildContext context, WidgetRef ref, FavoriteItem item) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(favoritesProvider.notifier).remove(item);
      messenger.showSnackBar(const SnackBar(content: Text('Removed from favorites')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final session = ref.watch(sessionProvider);
    final favorites = ref.watch(favoritesProvider);

    final body = switch ((session, favorites)) {
      (AsyncData(value: null), _) => [
          EmptyState(
            icon: Icons.favorite_rounded,
            title: 'Sign in to save poses',
            message: 'Favorites are kept in your account, so they follow you to any device.',
            action: ComicButton(label: 'Sign in', icon: Icons.login_rounded, onPressed: () => context.push('/sign-in')),
          ),
        ],
      (_, AsyncData(:final value)) when value.isEmpty => [
          EmptyState(
            icon: Icons.favorite_border_rounded,
            title: 'No saved poses yet',
            message: 'Tap Save to favorites on any pose to keep it here.',
            action: ComicButton(label: 'Browse poses', icon: Icons.explore_rounded, onPressed: () => context.go('/discover')),
          ),
        ],
      (_, AsyncData(:final value)) => [
          Text('${value.length} saved pose${value.length == 1 ? '' : 's'}',
              style: text.bodyLarge?.copyWith(color: AppColors.mute)),
          const SizedBox(height: 16),
          for (final f in value)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _FavoriteRow(item: f, onRemove: () => _remove(context, ref, f)),
            ),
        ],
      (_, AsyncError(:final error)) => [ErrorPanel(message: '$error', onRetry: () => ref.invalidate(favoritesProvider))],
      _ => [const LoadingPanel()],
    };

    return RefreshIndicator(
      color: AppColors.yellow,
      onRefresh: () => ref.refresh(favoritesProvider.future),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 120),
        children: [Text('Favorites', style: text.headlineMedium), const SizedBox(height: 4), ...body],
      ),
    );
  }
}

class _FavoriteRow extends StatelessWidget {
  const _FavoriteRow({required this.item, required this.onRemove});

  final FavoriteItem item;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final pose = item.pose;
    return GlassPanel(
      padding: const EdgeInsets.all(8),
      child: Row(children: [
        Expanded(
          child: InkWell(
            onTap: () => context.push('/poses/${pose.id}'),
            child: Row(children: [
              SizedBox(width: 84, height: 96, child: ComicPanel(child: PosePhoto(url: pose.imageUrl))),
              const SizedBox(width: 14),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(pose.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
                  const SizedBox(height: 3),
                  Text(pose.meta, style: const TextStyle(fontSize: 12.5, color: AppColors.mute)),
                ]),
              ),
            ]),
          ),
        ),
        IconButton(
          onPressed: onRemove,
          icon: const Icon(Icons.favorite_rounded, color: AppColors.red),
          tooltip: 'Remove ${pose.name} from favorites',
        ),
      ]),
    );
  }
}
