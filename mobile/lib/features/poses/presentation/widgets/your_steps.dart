import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/glass_panel.dart';
import '../../../analysis/domain/recommendation.dart';

/// Steps from the figure's current pose (PRD 4.6): only the joints that need to move, biggest moves
/// flagged, then which joints are already right and which the photo didn't show.
class YourSteps extends StatelessWidget {
  const YourSteps({super.key, required this.changes});

  final List<JointChange> changes;

  @override
  Widget build(BuildContext context) {
    final moves = changes.where((c) => c.isMove).toList();
    final kept = changes.where((c) => c.action == 'keep').map((c) => c.partLabel).toList();
    final unknown = changes.where((c) => c.action == 'unknown').map((c) => c.partLabel).toList();

    return GlassPanel(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (moves.isEmpty)
          const Text('Your figure is already in this pose. Fine-tune it with the reference photo.',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5))
        else
          for (final (i, c) in moves.indexed) ...[
            if (i > 0) Divider(height: 1, color: Colors.white.withValues(alpha: .16)),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 26,
                  height: 26,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: c.priority == 'high' ? AppColors.yellow : AppColors.chalk,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.line, width: 2),
                  ),
                  child: Text('${i + 1}', style: const TextStyle(color: AppColors.line, fontWeight: FontWeight.w800, fontSize: 13)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(c.sentence, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5)),
                    if (c.current != null && c.target != null)
                      Text('Now about ${c.current}°, target ${c.target}°',
                          style: const TextStyle(fontSize: 12.5, color: AppColors.mute)),
                  ]),
                ),
                if (c.priority == 'high')
                  const Padding(
                    padding: EdgeInsets.only(left: 8, top: 2),
                    child: Text('BIG MOVE', style: TextStyle(fontFamily: 'BowlbyOne', fontSize: 11, color: AppColors.yellow)),
                  ),
              ]),
            ),
          ],
        if (kept.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('Already in place: ${kept.join(', ')}', style: const TextStyle(fontSize: 13, color: Color(0xFFE2E5FF))),
        ],
        if (unknown.isNotEmpty) ...[
          const SizedBox(height: 6),
          Text('Not visible in your photo: ${unknown.join(', ')}. Use the reference steps for these.',
              style: const TextStyle(fontSize: 13, color: Color(0xFFE2E5FF))),
        ],
      ]),
    );
  }
}
