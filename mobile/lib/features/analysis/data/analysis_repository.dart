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

  /// Supported figure types, for the "which type is it?" picker. Returns slug -> id.
  Future<Map<String, int>> profileIds() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/figures/profiles');
      return {for (final p in res.data!['data'] as List) (p as Map)['slug'] as String: p['id'] as int};
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  /// Re-analyzes the photo with the type the user picked (FIG-03). The analysis goes back to pending.
  Future<void> confirmProfile(String id, int profileId) async {
    try {
      await _dio.post<void>('/analyses/$id/profile', data: {'figure_profile_id': profileId});
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  /// "Show different poses" (REC-07). Returns the updated analysis and the server's message.
  Future<(Analysis, String)> showDifferent(String id) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>('/analyses/$id/recommendations');
      return (Analysis.fromJson(res.data!['data'] as Map<String, dynamic>), res.data!['message'] as String? ?? '');
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  /// Analyses of the signed-in user, or of this device for a guest, newest first.
  Future<List<Analysis>> history() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/analyses');
      return [for (final a in res.data!['data'] as List) Analysis.fromJson(a as Map<String, dynamic>)];
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  /// Deletes the analysis and the stored photo.
  Future<void> delete(String id) async {
    try {
      await _dio.delete<void>('/analyses/$id');
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
