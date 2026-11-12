import 'pose_result.dart';
import 'recommendation.dart';

export 'pose_result.dart';
export 'recommendation.dart';

enum AnalysisStatus {
  pending,
  processing,
  completed,
  failed;

  bool get isFinal => this == completed || this == failed;

  static AnalysisStatus parse(String value) =>
      AnalysisStatus.values.firstWhere((s) => s.name == value, orElse: () => AnalysisStatus.pending);
}

class QualityIssue {
  const QualityIssue(this.code, this.message);

  final String code;
  final String message;
}

class Analysis {
  const Analysis({
    required this.id,
    required this.status,
    this.pollAfterSeconds,
    this.errorCode,
    this.errorMessage,
    this.retryable = false,
    this.issues = const [],
    this.sharpness,
    this.createdAt,
    this.profile,
    this.recommendationCount = 0,
    this.imageWidth,
    this.imageHeight,
    this.typeGuess,
    this.pose,
    this.figureCount = 0,
    this.recommendations = const [],
    this.typeOnly = false,
    this.moreRecommendations = false,
    this.aiVisualsAvailable = false,
  });

  final String id;
  final AnalysisStatus status;
  final int? pollAfterSeconds;
  final String? errorCode;
  final String? errorMessage;
  final bool retryable;
  final List<QualityIssue> issues;
  final double? sharpness;
  final DateTime? createdAt;
  final String? profile;
  final int recommendationCount;
  final int? imageWidth;
  final int? imageHeight;
  final FigureTypeGuess? typeGuess;
  final PoseResult? pose;
  final int figureCount;
  final List<PoseRecommendation> recommendations;

  /// The figure's pose couldn't be read, so recommendations are poses for its type, not matches.
  final bool typeOnly;
  final bool moreRecommendations;
  final bool aiVisualsAvailable;

  factory Analysis.fromJson(Map<String, dynamic> json) {
    final error = json['error'] as Map<String, dynamic>?;
    final quality = json['quality'] as Map<String, dynamic>?;
    return Analysis(
      id: json['analysis_id'] as String,
      status: AnalysisStatus.parse(json['status'] as String),
      pollAfterSeconds: json['poll_after_seconds'] as int?,
      errorCode: error?['code'] as String?,
      errorMessage: error?['message'] as String?,
      retryable: error?['retryable'] as bool? ?? false,
      sharpness: (quality?['sharpness'] as num?)?.toDouble(),
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      profile: json['profile'] as String?,
      recommendationCount: (json['recommendations'] as List?)?.length ?? 0,
      imageWidth: (json['image'] as Map?)?['width'] as int?,
      imageHeight: (json['image'] as Map?)?['height'] as int?,
      typeGuess: json['classification'] is Map ? FigureTypeGuess.fromJson(json['classification'] as Map<String, dynamic>) : null,
      pose: json['pose'] is Map ? PoseResult.fromJson(json['pose'] as Map<String, dynamic>) : null,
      figureCount: (json['figures'] as List?)?.length ?? 0,
      recommendations: [
        for (final r in (json['recommendations'] as List? ?? const []))
          PoseRecommendation.fromJson(r as Map<String, dynamic>),
      ],
      typeOnly: json['recommendation_basis'] == 'type_only',
      moreRecommendations: json['more_recommendations'] as bool? ?? false,
      aiVisualsAvailable: json['ai_visuals_available'] as bool? ?? false,
      issues: [
        for (final i in (quality?['issues'] as List? ?? const []))
          QualityIssue((i as Map)['code'] as String, i['message'] as String),
      ],
    );
  }
}
