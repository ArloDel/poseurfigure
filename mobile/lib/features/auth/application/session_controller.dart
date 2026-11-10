import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/storage/token_store.dart';
import '../data/auth_repository.dart';
import '../domain/app_user.dart';

/// The signed-in user, or null for a guest. Favorites and history watch this,
/// so they reload when someone signs in or out.
class SessionController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    ref.watch(tokenRevisionProvider);
    final store = ref.read(tokenStoreProvider);
    if (await store.read() == null) return null;

    try {
      return await ref.read(authRepositoryProvider).me();
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        await store.clear();
        return null;
      }
      rethrow;
    }
  }

  /// Throws [ApiException] with a message the UI can show as-is.
  Future<AuthResult> signIn({required String email, required String password}) =>
      _start(() => ref.read(authRepositoryProvider).login(email: email, password: password));

  Future<AuthResult> register({required String name, required String email, required String password}) =>
      _start(() => ref.read(authRepositoryProvider).register(name: name, email: email, password: password));

  Future<void> signOut() async {
    try {
      await ref.read(authRepositoryProvider).logout();
    } catch (_) {
      // Signing out works offline too: the token is dropped locally either way.
    }
    await ref.read(tokenStoreProvider).clear();
    state = const AsyncData(null);
  }

  Future<AuthResult> _start(Future<AuthResult> Function() call) async {
    final result = await call();
    await ref.read(tokenStoreProvider).write(result.token);
    state = AsyncData(result.user);
    return result;
  }
}

final sessionProvider = AsyncNotifierProvider<SessionController, AppUser?>(SessionController.new);
