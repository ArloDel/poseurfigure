import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/network/api_client.dart';
import '../domain/analysis.dart';

class AnalysisRepository {
  AnalysisRepository(this._dio);

  final Dio _dio;

  /// POST /analyses. Returns as soon as the server has stored the photo (status `pending`).
  Future<String> start(XFile photo, {int? profileId}) async {
    try {
      final form = FormData.fromMap({
        'image': MultipartFile.fromBytes(await photo.readAsBytes(), filename: photo.name),
        'analysis_mode': profileId == null ? 'automatic' : 'manual',
        'figure_profile_id': ?profileId,
      });
      final res = await _dio.post<Map<String, dynamic>>('/analyses', data: form);
      return res.data!['data']['analysis_id'] as String;
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<Analysis> fetch(String id) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/analyses/$id');
      return Analysis.fromJson(res.data!['data'] as Map<String, dynamic>);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<bool> serverHealthy() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/health');
      return res.data?['success'] == true;
    } catch (_) {
      return false;
    }
  }
}

final analysisRepositoryProvider = Provider((ref) => AnalysisRepository(ref.watch(dioProvider)));

final serverHealthProvider = FutureProvider<bool>((ref) => ref.watch(analysisRepositoryProvider).serverHealthy());
