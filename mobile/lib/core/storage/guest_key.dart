import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// A random device id that lets guests use the app without an account (AUTH-05).
/// Sent as X-Guest-Key; the server only stores a hash of it.
class GuestKeyStore {
  GuestKeyStore(this._storage);

  static const _key = 'figurepose.guest_key';
  final FlutterSecureStorage _storage;

  Future<String> read() async {
    final existing = await _storage.read(key: _key);
    if (existing != null && existing.isNotEmpty) return existing;
    final created = uuidV4();
    await _storage.write(key: _key, value: created);
    return created;
  }
}

String uuidV4([Random? random]) {
  final r = random ?? Random.secure();
  final b = List<int>.generate(16, (_) => r.nextInt(256));
  b[6] = (b[6] & 0x0f) | 0x40; // version 4
  b[8] = (b[8] & 0x3f) | 0x80; // RFC 4122 variant
  final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
}

final secureStorageProvider = Provider<FlutterSecureStorage>((ref) => const FlutterSecureStorage());

final guestKeyProvider = FutureProvider<String>((ref) => GuestKeyStore(ref.watch(secureStorageProvider)).read());
