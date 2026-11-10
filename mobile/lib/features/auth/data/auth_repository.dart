import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/app_user.dart';

class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;
  static const _device = 'figurepose-app';

  Future<AuthResult> register({required String name, required String email, required String password}) =>
      _auth('/auth/register', {'name': name, 'email': email, 'password': password, 'device_name': _device});

  Future<AuthResult> login({required String email, required String password}) =>
      _auth('/auth/login', {'email': email, 'password': password, 'device_name': _device});

  Future<AppUser> me() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/auth/me');
      return AppUser.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<void> logout() async {
    try {
      await _dio.post<void>('/auth/logout');
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<AuthResult> _auth(String path, Map<String, dynamic> body) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>(path, data: body);
      return AuthResult.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final authRepositoryProvider = Provider((ref) => AuthRepository(ref.watch(dioProvider)));
