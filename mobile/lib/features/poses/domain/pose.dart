import '../../../core/utils/labels.dart';

class PhotoCredit {
  const PhotoCredit({required this.title, required this.creator, required this.license});

  final String title;
  final String creator;
  final String license;

  factory PhotoCredit.fromJson(Map<String, dynamic> json) => PhotoCredit(
        title: json['title'] as String? ?? '',
        creator: json['creator'] as String? ?? '',
        license: json['license'] as String? ?? '',
      );

  @override
  String toString() => '"$title" by $creator, $license';
}

enum BodyRegion { headAndTorso, arms, legs }

class PoseInstruction {
  const PoseInstruction({
    required this.step,
    required this.bodyPart,
    required this.movement,
    this.targetAngle,
    this.priority = 'medium',
  });

  final int step;
  final String bodyPart;
  final String movement;
  final num? targetAngle;
  final String priority;

  factory PoseInstruction.fromJson(Map<String, dynamic> json) => PoseInstruction(
        step: json['step'] as int? ?? 0,
        bodyPart: json['body_part'] as String,
        movement: json['movement'] as String,
        targetAngle: json['target_angle'] as num?,
        priority: json['priority'] as String? ?? 'medium',
      );

  /// `bend` + `right_knee` -> `Bend the right knee`.
  String get title => '${humanize(movement)} the ${humanize(bodyPart).toLowerCase()}';

  BodyRegion get region {
    if (RegExp(r'shoulder|elbow|wrist|arm|hand').hasMatch(bodyPart)) return BodyRegion.arms;
    if (RegExp(r'hip|knee|ankle|leg|foot').hasMatch(bodyPart)) return BodyRegion.legs;
    return BodyRegion.headAndTorso;
  }
}

/// A joint whose target angle may be past what many figures can do (PRD 8.5).
class JointWarning {
  const JointWarning({required this.joint, required this.targetAngle});

  final String joint;
  final num targetAngle;
}

class Pose {
  const Pose({
    required this.id,
    required this.slug,
    required this.name,
    required this.category,
    required this.difficulty,
    this.profile,
    this.imageUrl,
    this.credit,
    this.description,
    this.instructions = const [],
    this.warnings = const [],
  });

  final int id;
  final String slug;
  final String name;
  final String category;
  final String difficulty;
  final String? profile;
  final String? imageUrl;
  final PhotoCredit? credit;
  final String? description;
  final List<PoseInstruction> instructions;
  final List<JointWarning> warnings;

  String get meta => '${capitalize(category)}, $difficulty';

  factory Pose.fromJson(Map<String, dynamic> json) {
    final constraints = json['constraints'];
    return Pose(
      id: json['id'] as int,
      slug: json['slug'] as String,
      name: json['name'] as String,
      category: json['category'] as String,
      difficulty: json['difficulty'] as String,
      profile: json['profile'] as String?,
      imageUrl: json['image_url'] as String?,
      credit: json['image_credit'] is Map ? PhotoCredit.fromJson(json['image_credit'] as Map<String, dynamic>) : null,
      description: json['description'] as String?,
      instructions: [
        for (final i in (json['instructions'] as List? ?? const [])) PoseInstruction.fromJson(i as Map<String, dynamic>),
      ]..sort((a, b) => a.step.compareTo(b.step)),
      warnings: [
        if (constraints is Map)
          for (final MapEntry(:key, :value) in constraints.entries)
            if (value is Map && value['warn_above_profile_max'] == true && value['target'] is num)
              JointWarning(joint: key as String, targetAngle: value['target'] as num),
      ],
    );
  }
}
