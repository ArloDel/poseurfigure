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
    this.aiVisualsProvider,
    this.characterName,
    this.characterSource,
    this.characterFranchise,
    this.recognitionAvailable = false,
    this.recognitionProvider,
    this.references,
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

  /// Who makes AI visuals ("OpenAI"), named before the user agrees to send their photo. Null: not named.
  final String? aiVisualsProvider;

  /// The character the figure shows ("Spider-Man (symbiote suit)"): pose ideas show that character first.
  final String? characterName;

  /// "ai" (suggested by the recognition service) or "user" (typed or corrected).
  final String? characterSource;
  final String? characterFranchise;

  /// Whether the server can suggest the character from the photo, and which service it uses.
  final bool recognitionAvailable;
  final String? recognitionProvider;

  /// Finding the character's poses on Pinterest (personal instances); null when off or not started.
  final ReferenceSearchProgress? references;

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
      aiVisualsProvider: json['ai_visuals_provider'] as String?,
      characterName: (json['character'] as Map?)?['name'] as String?,
      characterSource: (json['character'] as Map?)?['source'] as String?,
      characterFranchise: (json['character'] as Map?)?['franchise'] as String?,
      recognitionAvailable: (json['character_recognition'] as Map?)?['available'] as bool? ?? false,
      recognitionProvider: (json['character_recognition'] as Map?)?['provider'] as String?,
      references: json['references'] is Map ? ReferenceSearchProgress.fromJson(Map<String, dynamic>.from(json['references'] as Map)) : null,
      issues: [
        for (final i in (quality?['issues'] as List? ?? const []))
          QualityIssue((i as Map)['code'] as String, i['message'] as String),
      ],
    );
  }
}

/// How far the search for the character's poses on Pinterest has come.
class ReferenceSearchProgress {
  const ReferenceSearchProgress({required this.status, this.total = 0, this.checked = 0, this.found = 0, this.error});

  /// running, done or failed.
  final String status;
  final int total;
  final int checked;
  final int found;
  final String? error;

  bool get isRunning => status == 'running';

  factory ReferenceSearchProgress.fromJson(Map<String, dynamic> json) => ReferenceSearchProgress(
        status: json['status'] as String? ?? 'done',
        total: json['total'] as int? ?? 0,
        checked: json['checked'] as int? ?? 0,
        found: json['found'] as int? ?? 0,
        error: json['error'] as String?,
      );
}
