import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/comic_button.dart';
import '../../../../shared/widgets/comic_panel.dart';
import '../../../../shared/widgets/glass_panel.dart';
import '../../../../shared/widgets/pose_photo.dart';
import '../../domain/analysis.dart';

/// "Poses for your figure": ranked suggestions with why each is there (PRD 4.5, 6.1 Recommendations).
class RecommendationList extends StatelessWidget {
  const RecommendationList({
    super.key,
    required this.analysis,
    required this.onShowDifferent,
    this.busy = false,
  });

  final Analysis analysis;
  final VoidCallback onShowDifferent;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final recs = analysis.recommendations;
    final typeName = (profileNames[analysis.profile] ?? 'this').toLowerCase();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Poses for your figure', style: text.titleLarge),
        const SizedBox(height: 10),
        if (analysis.typeOnly)
          Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: GlassPanel(
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                const Icon(Icons.info_outline_rounded, color: AppColors.yellow),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    "We couldn't read enough of your figure's joints to compare poses, so these are poses that suit a "
                    '$typeName figure. A clearer, full-body photo gives closer matches.',
                  ),
                ),
              ]),
            ),
          ),
        if (recs.isEmpty)
          GlassPanel(child: Text('No poses for a $typeName figure in the catalog yet.', style: text.bodyLarge))
        else
          for (final r in recs)
            Padding(padding: const EdgeInsets.only(bottom: 18), child: _RecommendationCard(rec: r, typeOnly: analysis.typeOnly)),
        if (recs.isNotEmpty)
          analysis.moreRecommendations
              ? ComicButton(
                  label: 'Show different poses',
                  icon: Icons.refresh_rounded,
                  style: ComicButtonStyle.ghost,
                  busy: busy,
                  expand: true,
                  onPressed: onShowDifferent,
                )
              : Text("That's every pose we have for this figure type so far.",
                  style: text.bodySmall, textAlign: TextAlign.center),
      ],
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.rec, required this.typeOnly});

  final PoseRecommendation rec;
  final bool typeOnly;

  @override
  Widget build(BuildContext context) {
    final pose = rec.pose;
    return Semantics(
      button: true,
      label: '${rec.rank}. ${pose.name}, ${pose.meta}${rec.mirrored ? ', mirror it' : ''}',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: () => context.push('/poses/${pose.id}${rec.mirrored ? '?mirrored=1' : ''}'),
        child: SizedBox(
          height: 330,
          child: ComicPanel(
            child: Stack(fit: StackFit.expand, children: [
              PosePhoto(url: pose.imageUrl),
              const Positioned(left: 10, top: 10, child: _CatalogBadge()),
              Positioned(
                right: 12,
                top: 4,
                child: Text('${rec.rank}',
                    style: const TextStyle(
                      fontFamily: 'BowlbyOne',
                      fontSize: 30,
                      color: Colors.white,
                      shadows: [Shadow(color: AppColors.line, offset: Offset(3, 3))],
                    )),
              ),
              Positioned(
                left: 8,
                right: 8,
                bottom: 8,
                child: GlassPanel(
                  overPhoto: true,
                  radius: 16,
                  shadowOffset: 3,
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    Text(pose.name, style: const TextStyle(fontFamily: 'BowlbyOne', fontSize: 20, height: 1.1)),
                    const SizedBox(height: 2),
                    Text('${pose.meta} difficulty', style: const TextStyle(fontSize: 13, color: Color(0xFFE2E5FF))),
                    const SizedBox(height: 10),
                    Row(children: [
                      if (!typeOnly) ...[
                        Expanded(child: _Meter(label: 'Match to your figure', value: rec.similarity, color: AppColors.cyan)),
                        const SizedBox(width: 12),
                      ],
                      Expanded(
                        child: _Meter(
                          label: 'Likely to hold',
                          value: rec.feasibility,
                          color: rec.feasibility < 0.8 ? AppColors.yellow : AppColors.green,
                        ),
                      ),
                    ]),
                    if (rec.reasons.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Wrap(spacing: 6, runSpacing: 6, children: [
                        for (final r in rec.reasons)
                          if (reasonLabels[r] != null) _ReasonChip(label: reasonLabels[r]!, warn: r == 'check_joints'),
                      ]),
                    ],
                  ]),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
  }
}

class _Meter extends StatelessWidget {
  const _Meter({required this.label, required this.value, required this.color});

  final String label;
  final double value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('${(value * 100).round()}%', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
      Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFFE2E5FF))),
      const SizedBox(height: 5),
      ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(value: value.clamp(0, 1), minHeight: 7, color: color, backgroundColor: Colors.white24),
      ),
    ]);
  }
}

class _ReasonChip extends StatelessWidget {
  const _ReasonChip({required this.label, this.warn = false});

  final String label;
  final bool warn;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: warn ? AppColors.red : Colors.white.withValues(alpha: .16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.line, width: 2),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        if (warn) ...[const Icon(Icons.warning_amber_rounded, size: 14, color: Colors.white), const SizedBox(width: 4)],
        Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      ]),
    );
  }
}

class _CatalogBadge extends StatelessWidget {
  const _CatalogBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.green,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line, width: 2),
      ),
      child: const Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.check_rounded, size: 14, color: AppColors.line),
        SizedBox(width: 4),
        Text('Catalog reference', style: TextStyle(color: AppColors.line, fontWeight: FontWeight.w800, fontSize: 12)),
      ]),
    );
  }
}
