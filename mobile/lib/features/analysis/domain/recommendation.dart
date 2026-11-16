import '../../../core/utils/labels.dart';
import '../../poses/domain/pose.dart';

class JointLimitWarning {
  const JointLimitWarning({required this.joint, required this.target, required this.limit});

  final String joint;
  final num target;
  final num limit;

  String get label => '${humanize(joint)} $target° (limit about $limit°)';
}

/// One joint's move from the figure's current pose to a recommended pose, in the figure's own left/right.
class JointChange {
  const JointChange({required this.joint, required this.action, this.target, this.current, this.delta, this.priority = 'low'});

  final String joint;

  /// keep, bend, straighten, raise, lower, lift_leg, lower_leg, unknown.
  final String action;
  final num? target;
  final num? current;

  /// Target minus current, in degrees.
  final num? delta;
  final String priority;

  bool get isMove => action != 'keep' && action != 'unknown';

  factory JointChange.fromJson(Map<String, dynamic> json) => JointChange(
        joint: json['joint'] as String,
        action: json['action'] as String,
        target: json['target'] as num?,
        current: json['current'] as num?,
        delta: json['delta'] as num?,
        priority: json['priority'] as String? ?? 'low',
      );

  /// Shoulders move the arm and hips move the leg, so that's what the user is told to hold.
  String get _part {
    final side = joint.startsWith('left_') ? 'left' : 'right';
    if (joint.endsWith('shoulder')) return '$side arm';
    if (joint.endsWith('_hip')) return '$side leg';
    return humanize(joint).toLowerCase();
  }

  /// Angles come from a 2D photo: steps of 5 degrees are as precise as they honestly get.
  int get roundedDegrees => (((delta ?? 0).abs() / 5).round() * 5).clamp(5, 180).toInt();

  /// `Bend the right knee about 40° more`.
  String get sentence => switch (action) {
        'bend' => 'Bend the $_part about $roundedDegrees° more',
        'straighten' => 'Straighten the $_part about $roundedDegrees°',
        'raise' => 'Raise the $_part about $roundedDegrees°',
        'lower' => 'Lower the $_part about $roundedDegrees°',
        'lift_leg' => 'Lift the $_part about $roundedDegrees°',
        'lower_leg' => 'Lower the $_part about $roundedDegrees°',
        _ => humanize(_part),
      };

  /// Joint name for the "already in place" and "not visible" lists.
  String get partLabel => humanize(_part);
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
    this.changes = const [],
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

  /// How to get from the figure's current pose to this one. Empty when ranked by figure type only.
  final List<JointChange> changes;

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
        changes: [
          for (final c in (json['changes'] as List? ?? const [])) JointChange.fromJson(Map<String, dynamic>.from(c as Map)),
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
