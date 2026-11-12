/// An AI-generated picture of the user's figure in a catalog pose (REC-08..10).
/// Always labelled as AI-generated; `validation` says whether the pose in it was checked.
class AiVisual {
  const AiVisual({
    required this.id,
    required this.status,
    required this.validation,
    this.imageUrl,
    this.provider,
    this.note,
    this.errorMessage,
    this.pollAfterSeconds,
  });

  final int id;

  /// pending, generated or failed.
  final String status;

  /// unvalidated, validated or rejected.
  final String validation;
  final String? imageUrl;
  final String? provider;
  final String? note;
  final String? errorMessage;
  final int? pollAfterSeconds;

  bool get isPending => status == 'pending';
  bool get isReady => status == 'generated' && imageUrl != null;
  bool get failed => status == 'failed';

  /// The development stand-in returns the original photo, not a generated image.
  bool get isStub => provider == 'stub';

  String get validationLabel => switch (validation) {
        'validated' => 'Pose checked',
        'rejected' => 'Pose check failed',
        _ => 'Pose not checked',
      };

  factory AiVisual.fromJson(Map<String, dynamic> json) => AiVisual(
        id: json['id'] as int,
        status: json['status'] as String,
        validation: json['validation_status'] as String? ?? 'unvalidated',
        imageUrl: json['image_url'] as String?,
        provider: json['provider'] as String?,
        note: json['validation_note'] as String?,
        errorMessage: (json['error'] as Map?)?['message'] as String?,
        pollAfterSeconds: json['poll_after_seconds'] as int?,
      );
}
