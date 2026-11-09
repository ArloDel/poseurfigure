import 'dart:ui';

import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Frosted glass with a comic ink outline and hard offset shadow.
/// [overPhoto] uses a darker tint so text stays readable on bright photos.
class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.radius = 20,
    this.overPhoto = false,
    this.shadowOffset = 4,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double radius;
  final bool overPhoto;
  final double shadowOffset;

  @override
  Widget build(BuildContext context) {
    final shape = BorderRadius.circular(radius);
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: shape,
        boxShadow: [BoxShadow(color: AppColors.line, offset: Offset(shadowOffset, shadowOffset))],
      ),
      child: ClipRRect(
        borderRadius: shape,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: overPhoto ? 14 : 20, sigmaY: overPhoto ? 14 : 20),
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: shape,
              border: Border.all(color: AppColors.line, width: 2.5),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: overPhoto
                    ? [const Color(0xFF343E96).withValues(alpha: .55), AppColors.ink.withValues(alpha: .7)]
                    : [Colors.white.withValues(alpha: .24), Colors.white.withValues(alpha: .07), AppColors.violet.withValues(alpha: .12)],
              ),
            ),
            child: CustomPaint(
              painter: _SheenPainter(radius),
              child: Padding(padding: padding, child: child),
            ),
          ),
        ),
      ),
    );
  }
}

/// Diagonal light streak + bright top edge: what makes glass read as glass.
class _SheenPainter extends CustomPainter {
  _SheenPainter(this.radius);

  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    canvas.drawRect(
      rect,
      Paint()
        ..shader = LinearGradient(
          begin: const Alignment(-1, -.6),
          end: const Alignment(1, .6),
          colors: [Colors.white.withValues(alpha: 0), Colors.white.withValues(alpha: .18), Colors.white.withValues(alpha: 0)],
          stops: const [.22, .30, .40],
        ).createShader(rect),
    );
    canvas.drawLine(
      Offset(radius * .6, 1.5),
      Offset(size.width - radius * .6, 1.5),
      Paint()
        ..color = Colors.white.withValues(alpha: .6)
        ..strokeWidth = 1.5,
    );
  }

  @override
  bool shouldRepaint(covariant _SheenPainter oldDelegate) => oldDelegate.radius != radius;
}
