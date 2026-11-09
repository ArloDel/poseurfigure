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
  });

  final String id;
  final AnalysisStatus status;
  final int? pollAfterSeconds;
  final String? errorCode;
  final String? errorMessage;
  final bool retryable;
  final List<QualityIssue> issues;
  final double? sharpness;

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
      issues: [
        for (final i in (quality?['issues'] as List? ?? const []))
          QualityIssue((i as Map)['code'] as String, i['message'] as String),
      ],
    );
  }
}
