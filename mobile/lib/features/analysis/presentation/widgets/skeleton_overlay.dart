import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../domain/pose_result.dart';

/// The user's photo with the detected skeleton drawn on top.
/// The figure's left side is cyan and its right side orange, so a swapped side is easy to spot.
class SkeletonOverlay extends StatelessWidget {
  const SkeletonOverlay({super.key, required this.photo, required this.pose, required this.aspectRatio});

  final Uint8List photo;
  final PoseResult pose;
  final double aspectRatio;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      image: true,
      label: 'Your photo with ${pose.visibleCount} detected joints',
      child: AspectRatio(
        aspectRatio: aspectRatio,
        child: Stack(fit: StackFit.expand, children: [
          Image.memory(photo, fit: BoxFit.fill),
          CustomPaint(painter: _SkeletonPainter(pose)),
        ]),
      ),
    );
  }
}

class _SkeletonPainter extends CustomPainter {
  _SkeletonPainter(this.pose);

  final PoseResult pose;

  static Color _side(String name) => name.startsWith('left')
      ? AppColors.cyan
      : name.startsWith('right')
          ? const Color(0xFFFF9F43)
          : AppColors.yellow;

  @override
  void paint(Canvas canvas, Size size) {
    Offset at(DetectedJoint j) => Offset(j.x! * size.width, j.y! * size.height);
    final outline = Paint()
      ..color = AppColors.line
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;

    for (final (a, b) in skeletonBones) {
      final ja = pose.joints[a], jb = pose.joints[b];
      if (ja == null || jb == null || !ja.hasPosition || !jb.hasPosition) continue;
      final dashed = !ja.isVisible || !jb.isVisible;
      final line = Paint()
        ..color = _side(b == 'neck' ? a : b).withValues(alpha: dashed ? .55 : 1)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round;
      canvas.drawLine(at(ja), at(jb), outline);
      canvas.drawLine(at(ja), at(jb), line);
    }
    for (final j in pose.joints.values) {
      if (!j.hasPosition) continue;
      canvas.drawCircle(at(j), 6, Paint()..color = AppColors.line);
      canvas.drawCircle(
        at(j),
        4,
        Paint()
          ..color = j.isVisible ? _side(j.name) : Colors.white
          ..style = j.isVisible ? PaintingStyle.fill : PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _SkeletonPainter old) => old.pose != pose;
}
