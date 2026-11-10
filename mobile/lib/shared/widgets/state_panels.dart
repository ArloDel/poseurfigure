import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'comic_button.dart';
import 'glass_panel.dart';

/// Something went wrong: say what, and offer the way out.
class ErrorPanel extends StatelessWidget {
  const ErrorPanel({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.warning_amber_rounded, color: AppColors.red),
            const SizedBox(width: 10),
            Expanded(child: Text(message, style: const TextStyle(fontWeight: FontWeight.w700))),
          ]),
          if (onRetry != null) ...[
            const SizedBox(height: 14),
            ComicButton(label: 'Try again', icon: Icons.refresh_rounded, style: ComicButtonStyle.ghost, onPressed: onRetry),
          ],
        ],
      ),
    );
  }
}

/// Nothing here yet: an invitation to act, not a mood.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.title, required this.message, this.action});

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        children: [
          Transform.rotate(
            angle: -.05,
            child: Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                color: AppColors.violet,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppColors.line, width: 3),
                boxShadow: const [BoxShadow(color: AppColors.line, offset: Offset(5, 5))],
              ),
              child: Icon(icon, size: 44, color: Colors.white),
            ),
          ),
          const SizedBox(height: 22),
          Text(title, style: text.titleLarge, textAlign: TextAlign.center),
          const SizedBox(height: 8),
          Text(message, style: text.bodyLarge?.copyWith(color: AppColors.mute), textAlign: TextAlign.center),
          if (action != null) ...[const SizedBox(height: 20), action!],
        ],
      ),
    );
  }
}

class LoadingPanel extends StatelessWidget {
  const LoadingPanel({super.key});

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator(color: AppColors.yellow)),
      );
}
