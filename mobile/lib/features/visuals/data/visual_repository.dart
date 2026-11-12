import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/ai_visual.dart';

class VisualRepository {
  VisualRepository(this._dio);

  final Dio _dio;

  /// Asks for an AI visual. Only call after the user agreed to send their photo to the image service.
  Future<AiVisual> request({required int poseId, required String analysisId, bool mirrored = false}) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/poses/$poseId/generate',
          data: {'analysis_id': analysisId, 'consent': true, 'mirrored': mirrored});
      return AiVisual.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<AiVisual> fetch(int id) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/generated-images/$id');
      return AiVisual.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final visualRepositoryProvider = Provider((ref) => VisualRepository(ref.watch(dioProvider)));
