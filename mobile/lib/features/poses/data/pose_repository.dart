import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/pose.dart';

class PoseQuery {
  const PoseQuery({this.profile, this.category, this.text = ''});

  final String? profile;
  final String? category;
  final String text;

  PoseQuery withProfile(String? value) => PoseQuery(profile: value, category: category, text: text);
  PoseQuery withCategory(String? value) => PoseQuery(profile: profile, category: value, text: text);
  PoseQuery withText(String value) => PoseQuery(profile: profile, category: category, text: value);

  Map<String, dynamic> toQuery() => {
        'profile': ?profile,
        'category': ?category,
        if (text.trim().isNotEmpty) 'q': text.trim(),
      };

  @override
  bool operator ==(Object other) =>
      other is PoseQuery && other.profile == profile && other.category == category && other.text == text;

  @override
  int get hashCode => Object.hash(profile, category, text);
}

class PoseRepository {
  PoseRepository(this._dio);

  final Dio _dio;

  Future<List<Pose>> list([PoseQuery query = const PoseQuery()]) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/poses', queryParameters: query.toQuery());
      return [for (final p in res.data!['data'] as List) Pose.fromJson(p as Map<String, dynamic>)];
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<Pose> detail(int id) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/poses/$id');
      return Pose.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final poseRepositoryProvider = Provider((ref) => PoseRepository(ref.watch(dioProvider)));
