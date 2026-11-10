import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// A catalog photo, or a halftone placeholder while it loads or when there is none.
class PosePhoto extends StatelessWidget {
  const PosePhoto({super.key, required this.url, this.alignment = const Alignment(0, -.3), this.semanticLabel});

  final String? url;
  final Alignment alignment;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final url = this.url;
    if (url == null || url.isEmpty) return const _Placeholder();
    return Semantics(
      image: true,
      label: semanticLabel,
      child: CachedNetworkImage(
        imageUrl: url,
        fit: BoxFit.cover,
        alignment: alignment,
        fadeInDuration: const Duration(milliseconds: 150),
        placeholder: (_, _) => const _Placeholder(),
        errorWidget: (_, _, _) => const _Placeholder(broken: true),
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({this.broken = false});

  final bool broken;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(color: Color(0xFF232A66)),
      child: CustomPaint(
        painter: const _Dots(),
        child: Center(
          child: Icon(broken ? Icons.broken_image_outlined : Icons.accessibility_new_rounded,
              size: 36, color: AppColors.mute.withValues(alpha: .6)),
        ),
      ),
    );
  }
}

class _Dots extends CustomPainter {
  const _Dots();

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withValues(alpha: .08);
    for (double y = 4; y < size.height; y += 9) {
      for (double x = 4; x < size.width; x += 9) {
        canvas.drawCircle(Offset(x, y), 1.5, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
