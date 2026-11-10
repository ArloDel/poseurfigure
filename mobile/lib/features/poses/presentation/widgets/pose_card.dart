import 'package:flutter/material.dart';

import '../../../../shared/widgets/comic_panel.dart';
import '../../../../shared/widgets/glass_panel.dart';
import '../../../../shared/widgets/pose_photo.dart';
import '../../domain/pose.dart';

/// Gallery card: the photo fills a comic panel, the name sits on glass over it.
class PoseCard extends StatelessWidget {
  const PoseCard({super.key, required this.pose, required this.onTap});

  final Pose pose;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '${pose.name}, ${pose.meta}',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: onTap,
        child: ComicPanel(
          child: Stack(
            fit: StackFit.expand,
            children: [
              PosePhoto(url: pose.imageUrl),
              Positioned(
                left: 6,
                right: 6,
                bottom: 6,
                child: GlassPanel(
                  overPhoto: true,
                  radius: 12,
                  shadowOffset: 3,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(pose.name,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, height: 1.2)),
                      const SizedBox(height: 2),
                      Text(pose.meta, style: const TextStyle(fontSize: 12, color: Color(0xFFE2E5FF))),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
