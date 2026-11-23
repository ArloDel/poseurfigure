import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../auth/application/session_controller.dart';
import '../../poses/domain/pose.dart';
import '../application/favorites_controller.dart';

/// Saves or removes [pose] and says what happened. Guests are asked to sign in instead (AUTH-06).
Future<void> toggleFavorite(BuildContext context, WidgetRef ref, Pose pose) async {
  final messenger = ScaffoldMessenger.of(context);
  final user = ref.read(sessionProvider).value;
  if (user == null) {
    messenger.showSnackBar(SnackBar(
      content: const Text('Sign in to save poses to your favorites.'),
      action: SnackBarAction(label: 'Sign in', onPressed: () => context.push('/sign-in')),
    ));
    return;
  }
  final wasSaved = ref.read(favoritesProvider.notifier).contains(pose);
  try {
    await ref.read(favoritesProvider.notifier).toggle(pose);
    messenger.showSnackBar(SnackBar(content: Text(wasSaved ? 'Removed from favorites' : 'Saved to favorites')));
  } catch (e) {
    messenger.showSnackBar(SnackBar(content: Text('$e')));
  }
}
