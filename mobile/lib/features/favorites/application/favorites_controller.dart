import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/application/session_controller.dart';
import '../../poses/domain/pose.dart';
import '../data/favorites_repository.dart';

/// Saved poses of the signed-in user. Guests have none: favorites need an account (AUTH-06).
class FavoritesController extends AsyncNotifier<List<FavoriteItem>> {
  @override
  Future<List<FavoriteItem>> build() async {
    final user = await ref.watch(sessionProvider.future);
    if (user == null) return const [];
    return ref.read(favoritesRepositoryProvider).list();
  }

  bool contains(int poseId) => (state.value ?? const []).any((f) => f.pose.id == poseId);

  /// Saves or removes [pose]. Removal shows at once and is undone if the server refuses.
  Future<void> toggle(Pose pose) async {
    final current = state.value ?? const <FavoriteItem>[];
    final index = current.indexWhere((f) => f.pose.id == pose.id);
    if (index >= 0) {
      await remove(current[index]);
    } else {
      final added = await ref.read(favoritesRepositoryProvider).add(pose.id);
      state = AsyncData([added, ...current.where((f) => f.id != added.id)]);
    }
  }

  Future<void> remove(FavoriteItem item) async {
    final current = state.value ?? const <FavoriteItem>[];
    state = AsyncData([for (final f in current) if (f.id != item.id) f]);
    try {
      await ref.read(favoritesRepositoryProvider).remove(item.id);
    } catch (_) {
      state = AsyncData(current);
      rethrow;
    }
  }
}

final favoritesProvider = AsyncNotifierProvider<FavoritesController, List<FavoriteItem>>(FavoritesController.new);
