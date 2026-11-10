import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'guest_key.dart';

/// Keeps the Sanctum token in secure storage, with an in-memory copy so
/// every API request doesn't hit the keychain.
class TokenStore {
  TokenStore(this._storage);

  static const _key = 'figurepose.token';
  final FlutterSecureStorage _storage;
  String? _cached;
  bool _loaded = false;

  Future<String?> read() async {
    if (!_loaded) {
      _cached = await _storage.read(key: _key);
      _loaded = true;
    }
    return _cached;
  }

  Future<void> write(String token) async {
    await _storage.write(key: _key, value: token);
    _cached = token;
    _loaded = true;
  }

  Future<void> clear() async {
    await _storage.delete(key: _key);
    _cached = null;
    _loaded = true;
  }
}

final tokenStoreProvider = Provider<TokenStore>((ref) => TokenStore(ref.watch(secureStorageProvider)));

/// Bumped when the server rejects the stored token. The session watches it, so the app
/// drops back to guest mode without the network layer knowing about features.
class TokenRevision extends Notifier<int> {
  @override
  int build() => 0;

  void bump() => state++;
}

final tokenRevisionProvider = NotifierProvider<TokenRevision, int>(TokenRevision.new);
