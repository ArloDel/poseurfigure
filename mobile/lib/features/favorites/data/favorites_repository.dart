import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../poses/domain/pose.dart';

class FavoriteItem {
  const FavoriteItem({required this.id, required this.pose});

  final int id;
  final Pose pose;

  factory FavoriteItem.fromJson(Map<String, dynamic> json) =>
      FavoriteItem(id: json['id'] as int, pose: Pose.fromJson(json['pose'] as Map<String, dynamic>));
}

class FavoritesRepository {
  FavoritesRepository(this._dio);

  final Dio _dio;

  Future<List<FavoriteItem>> list() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/favorites');
      return [for (final f in res.data!['data'] as List) FavoriteItem.fromJson(f as Map<String, dynamic>)];
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<FavoriteItem> add(int poseId) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/favorites', data: {'pose_id': poseId});
      return FavoriteItem.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<void> remove(int favoriteId) async {
    try {
      await _dio.delete<void>('/favorites/$favoriteId');
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final favoritesRepositoryProvider = Provider((ref) => FavoritesRepository(ref.watch(dioProvider)));
