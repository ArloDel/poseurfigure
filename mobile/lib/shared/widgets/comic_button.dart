import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

enum ComicButtonStyle { pow, ghost }

/// Chunky outlined button that "presses" into its hard shadow.
class ComicButton extends StatefulWidget {
  const ComicButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.style = ComicButtonStyle.pow,
    this.expand = false,
    this.busy = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final ComicButtonStyle style;
  final bool expand;
  final bool busy;

  @override
  State<ComicButton> createState() => _ComicButtonState();
}

class _ComicButtonState extends State<ComicButton> {
  bool _down = false;

  @override
  Widget build(BuildContext context) {
    final enabled = widget.onPressed != null && !widget.busy;
    final pow = widget.style == ComicButtonStyle.pow;
    final fg = pow ? AppColors.line : AppColors.chalk;
    final offset = _down ? 1.0 : 4.0;

    return Semantics(
      button: true,
      enabled: enabled,
      label: widget.label,
      child: GestureDetector(
        onTapDown: enabled ? (_) => setState(() => _down = true) : null,
        onTapCancel: () => setState(() => _down = false),
        onTapUp: enabled ? (_) => setState(() => _down = false) : null,
        onTap: enabled ? widget.onPressed : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 70),
          transform: Matrix4.translationValues(4 - offset, 4 - offset, 0),
          height: 52,
          width: widget.expand ? double.infinity : null,
          padding: const EdgeInsets.symmetric(horizontal: 20),
          decoration: BoxDecoration(
            color: pow ? AppColors.yellow : Colors.white.withValues(alpha: .14),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppColors.line, width: 2.5),
            boxShadow: [BoxShadow(color: AppColors.line, offset: Offset(offset, offset))],
          ),
          child: Opacity(
            opacity: enabled ? 1 : .55,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (widget.busy)
                  SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.5, color: fg))
                else if (widget.icon != null)
                  Icon(widget.icon, size: 20, color: fg),
                if (widget.busy || widget.icon != null) const SizedBox(width: 8),
                Flexible(
                  child: Text(widget.label,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: fg, fontWeight: FontWeight.w800, fontSize: 16)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
