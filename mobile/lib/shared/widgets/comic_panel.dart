import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// A comic panel: thick outline, tight radius, hard shadow. Frames photos.
class ComicPanel extends StatelessWidget {
  const ComicPanel({super.key, required this.child, this.radius = 8, this.color});

  final Widget child;
  final double radius;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color ?? const Color(0xFF1B2152),
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: AppColors.line, width: 3),
        boxShadow: const [BoxShadow(color: AppColors.line, offset: Offset(5, 5))],
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }
}
