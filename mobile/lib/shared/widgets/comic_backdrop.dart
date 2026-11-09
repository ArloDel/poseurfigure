import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

/// Coloured blobs + halftone dots behind every screen, so glass has something to bend.
class ComicBackdrop extends StatelessWidget {
  const ComicBackdrop({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        const ColoredBox(color: AppColors.ink),
        const _Blob(alignment: Alignment(-1.1, -1.0), color: AppColors.blue, size: 360),
        const _Blob(alignment: Alignment(1.3, -0.35), color: AppColors.pink, size: 300, opacity: .6),
        const _Blob(alignment: Alignment(0.9, 0.45), color: AppColors.violet, size: 380),
        const _Blob(alignment: Alignment(-1.2, 0.9), color: AppColors.cyan, size: 300, opacity: .5),
        const Positioned.fill(child: CustomPaint(painter: _HalftonePainter())),
        child,
      ],
    );
  }
}

class _Blob extends StatelessWidget {
  const _Blob({required this.alignment, required this.color, required this.size, this.opacity = .85});

  final Alignment alignment;
  final Color color;
  final double size;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: alignment,
      child: IgnorePointer(
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [color.withValues(alpha: opacity), color.withValues(alpha: 0)]),
          ),
        ),
      ),
    );
  }
}

class _HalftonePainter extends CustomPainter {
  const _HalftonePainter();

  @override
  void paint(Canvas canvas, Size size) {
    const step = 7.0;
    final paint = Paint()..color = AppColors.line.withValues(alpha: .45);
    for (double y = 0; y < size.height; y += step) {
      // Dots fade out toward the middle of the screen, like the prototype's mask.
      final t = (y / size.height - .5).abs() * 2;
      if (t < .25) continue;
      final r = 1.4 * ((t - .25) / .75).clamp(0.0, 1.0);
      for (double x = 0; x < size.width; x += step) {
        canvas.drawCircle(Offset(x, y), r, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
