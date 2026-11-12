import '../../../core/utils/labels.dart';
import '../../poses/domain/pose.dart';

class JointLimitWarning {
  const JointLimitWarning({required this.joint, required this.target, required this.limit});

  final String joint;
  final num target;
  final num limit;

  String get label => '${humanize(joint)} $target° (limit about $limit°)';
}

/// One suggested pose for the analyzed figure (REC-01..06).
class PoseRecommendation {
  const PoseRecommendation({
    required this.rank,
    required this.pose,
    required this.similarity,
    required this.feasibility,
    this.mirrored = false,
    this.reasons = const [],
    this.warnings = const [],
  });

  final int rank;
  final Pose pose;
  final double similarity;
  final double feasibility;

  /// The figure's pose matches this one with left and right swapped: "mirror it".
  final bool mirrored;

  /// close_to_current, few_changes, new_direction, mirror, different_category, check_joints.
  final List<String> reasons;
  final List<JointLimitWarning> warnings;

  factory PoseRecommendation.fromJson(Map<String, dynamic> json) => PoseRecommendation(
        rank: json['rank'] as int? ?? 0,
        pose: Pose.fromJson(json['pose'] as Map<String, dynamic>),
        similarity: (json['similarity_score'] as num?)?.toDouble() ?? 0,
        feasibility: (json['feasibility_score'] as num?)?.toDouble() ?? 0,
        mirrored: json['mirrored'] as bool? ?? false,
        reasons: [for (final r in (json['reasons'] as List? ?? const [])) r as String],
        warnings: [
          for (final w in (json['warnings'] as List? ?? const []))
            JointLimitWarning(joint: (w as Map)['joint'] as String, target: w['target'] as num, limit: w['limit'] as num),
        ],
      );
}

/// Short labels for the reason chips on a recommendation card.
const reasonLabels = {
  'close_to_current': 'Close to your pose',
  'few_changes': 'A few changes',
  'new_direction': 'New direction',
  'mirror': 'Mirror it',
  'different_category': 'Something different',
  'check_joints': 'Check joints',
};
