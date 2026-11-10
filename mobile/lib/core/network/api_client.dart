import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/env.dart';
import '../storage/guest_key.dart';
import '../storage/token_store.dart';

/// An error the UI can show as-is.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  factory ApiException.from(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      if (data is Map && data['errors'] is Map) {
        final first = (data['errors'] as Map).values.first;
        return ApiException(first is List ? '${first.first}' : '$first', statusCode: error.response?.statusCode);
      }
      if (data is Map && data['message'] is String) {
        return ApiException(data['message'] as String, statusCode: error.response?.statusCode);
      }
      if (error.type == DioExceptionType.connectionError || error.type == DioExceptionType.connectionTimeout) {
        return ApiException("Can't reach the FigurePose server. Check your connection.");
      }
      return ApiException('Something went wrong (${error.response?.statusCode ?? error.type.name}).',
          statusCode: error.response?.statusCode);
    }
    return ApiException('$error');
  }

  @override
  String toString() => message;
}

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(BaseOptions(
    baseUrl: Env.apiBaseUrl,
    connectTimeout: const Duration(seconds: 8),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Accept': 'application/json'},
  ));
  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      // Always send the guest key: on sign-in it lets the server move guest analyses to the account.
      options.headers['X-Guest-Key'] = await ref.read(guestKeyProvider.future);
      final token = await ref.read(tokenStoreProvider).read();
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    },
    onError: (error, handler) async {
      // The token was revoked or expired: forget it and fall back to guest mode.
      if (error.response?.statusCode == 401 && error.requestOptions.headers.containsKey('Authorization')) {
        await ref.read(tokenStoreProvider).clear();
        ref.read(tokenRevisionProvider.notifier).bump();
      }
      handler.next(error);
    },
  ));
  return dio;
});
