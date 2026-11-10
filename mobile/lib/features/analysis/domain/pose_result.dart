import '../../../core/utils/labels.dart';

/// One joint from the AI service. Coordinates are normalized (0-1) to the uploaded photo.
class DetectedJoint {
  const DetectedJoint({required this.name, this.x, this.y, required this.visibility, this.confidence = 0});

  final String name;
  final double? x;
  final double? y;

  /// visible, uncertain, not_visible or not_estimated.
  final String visibility;
  final double confidence;

  bool get isVisible => visibility == 'visible' && x != null && y != null;
  bool get hasPosition => x != null && y != null;
}

class FigureTypeGuess {
  const FigureTypeGuess({required this.profile, required this.confidence, required this.needsConfirmation, required this.byUser});

  final String profile;
  final double confidence;
  final bool needsConfirmation;
  final bool byUser;

  factory FigureTypeGuess.fromJson(Map<String, dynamic> json) => FigureTypeGuess(
        profile: json['profile'] as String,
        confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
        needsConfirmation: json['needs_confirmation'] as bool? ?? false,
        byUser: json['source'] == 'user',
      );
}

class PoseResult {
  const PoseResult({
    required this.joints,
    required this.visibleCount,
    required this.hidden,
    required this.angles,
    required this.orientation,
  });

  final Map<String, DetectedJoint> joints;
  final int visibleCount;
  final List<String> hidden;
  final Map<String, double> angles;
  final String orientation;

  /// Joints this profile can estimate (mecha armor and backpack are not estimated yet).
  int get estimableCount => joints.values.where((j) => j.visibility != 'not_estimated').length;

  String get hiddenSummary => hidden.isEmpty ? 'All joints found' : '${hidden.map(humanize).join(', ')} hidden';

  factory PoseResult.fromJson(Map<String, dynamic> json) {
    final kps = (json['keypoints'] as Map? ?? const {}).cast<String, dynamic>();
    return PoseResult(
      joints: {
        for (final MapEntry(:key, :value) in kps.entries)
          key: DetectedJoint(
            name: key,
            x: ((value as Map)['x'] as num?)?.toDouble(),
            y: (value['y'] as num?)?.toDouble(),
            visibility: value['visibility'] as String? ?? 'not_visible',
            confidence: (value['confidence'] as num?)?.toDouble() ?? 0,
          ),
      },
      visibleCount: json['visible_count'] as int? ?? 0,
      hidden: [for (final h in (json['hidden'] as List? ?? const [])) h as String],
      angles: {
        for (final MapEntry(:key, :value) in (json['joint_angles'] as Map? ?? const {}).entries)
          key as String: (value as num).toDouble(),
      },
      orientation: json['orientation'] as String? ?? 'unknown',
    );
  }
}

/// Bones drawn on the photo. Joints a profile doesn't have are skipped.
const skeletonBones = [
  ('head', 'neck'), ('neck', 'chest'), ('chest', 'waist'),
  ('neck', 'left_shoulder'), ('neck', 'right_shoulder'),
  ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
  ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
  ('waist', 'left_hip'), ('waist', 'right_hip'), ('left_hip', 'right_hip'),
  ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
  ('right_hip', 'right_knee'), ('right_knee', 'right_ankle'),
];

const profileNames = {'humanoid_v1': 'Humanoid', 'anime_v1': 'Anime-style', 'mecha_v1': 'Mecha / robot'};
