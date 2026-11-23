import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/comic_button.dart';
import '../../../../shared/widgets/comic_panel.dart';
import '../../../../shared/widgets/glass_panel.dart';
import '../../../../shared/widgets/pose_photo.dart';
import '../../../favorites/application/favorites_controller.dart';
import '../../../favorites/presentation/favorite_actions.dart';
import '../../../poses/domain/pose.dart';
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
    if (recs.any((r) => r.group != null)) return _ideas(context);

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
            Padding(padding: const EdgeInsets.only(bottom: 18), child: _RecommendationCard(
                rec: r,
                typeOnly: analysis.typeOnly,
                analysisId: analysis.id,
              ),
            ),
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

extension on RecommendationList {
  /// Pose ideas as a grid, grouped: the same character first, then figures that look like this one.
  Widget _ideas(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final recs = analysis.recommendations;
    final character = analysis.characterName;
    final hasSame = recs.any((r) => r.group == 'same_character');
    final hasSimilar = recs.any((r) => r.group == 'similar_look');

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Text('Pose ideas for your figure', style: text.titleLarge),
      if (character != null && !hasSame) ...[
        const SizedBox(height: 6),
        Text(
            hasSimilar
                ? 'No $character poses in our collection yet. These figures look like yours.'
                : 'No $character poses in our collection yet, and no figures that look much like it. Here are other poses to try.',
            style: text.bodyMedium),
      ],
      if (analysis.references case final refs?) ...[
        const SizedBox(height: 12),
        _ReferenceProgress(progress: refs, character: character ?? 'this character'),
      ],
      for (final MapEntry(key: group, value: title) in ideaGroups.entries)
        if (recs.where((r) => (r.group ?? 'more') == group).toList() case final items when items.isNotEmpty) ...[
          const SizedBox(height: 16),
          Semantics(
            header: true,
            child: Text(title,
                style: const TextStyle(
                  fontFamily: 'BowlbyOne',
                  fontSize: 16,
                  color: AppColors.yellow,
                  shadows: [Shadow(color: AppColors.line, offset: Offset(1.5, 1.5))],
                )),
          ),
          const SizedBox(height: 10),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 14,
            crossAxisSpacing: 12,
            childAspectRatio: 0.62,
            children: [for (final r in items) _IdeaTile(rec: r, analysisId: analysis.id)],
          ),
        ],
      const SizedBox(height: 18),
      if (analysis.moreRecommendations)
        ComicButton(
          label: 'Show different poses',
          icon: Icons.refresh_rounded,
          style: ComicButtonStyle.ghost,
          busy: busy,
          expand: true,
          onPressed: onShowDifferent,
        )
      else
        Text("That's every pose we have for this figure type so far.", style: text.bodySmall, textAlign: TextAlign.center),
    ]);
  }
}

/// One pose idea in the grid: photo, name, why it's here. Tap for the steps from your figure.
class _IdeaTile extends StatelessWidget {
  const _IdeaTile({required this.rec, required this.analysisId});

  final PoseRecommendation rec;
  final String analysisId;

  @override
  Widget build(BuildContext context) {
    final pose = rec.pose;
    final why = [for (final r in rec.reasons) if (reasonLabels[r] != null && r != 'check_joints') reasonLabels[r]!];
    return Stack(children: [
      Semantics(
        button: true,
        label: '${pose.name}, ${pose.meta}${why.isEmpty ? '' : ', ${why.join(', ')}'}',
        excludeSemantics: true,
        child: GestureDetector(
          onTap: () => context.push(pose.isReference
              ? Uri(path: '/references/${pose.id}', queryParameters: {'analysis': analysisId}).toString()
              : Uri(path: '/poses/${pose.id}', queryParameters: {
                  if (rec.mirrored) 'mirrored': '1',
                  'analysis': analysisId,
                }).toString()),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(
              child: ComicPanel(
                child: Stack(fit: StackFit.expand, children: [
                  PosePhoto(url: pose.imageUrl),
                  if (pose.isReference) const Positioned(left: 6, top: 6, child: _PinterestBadge()),
                ]),
              ),
            ),
            const SizedBox(height: 8),
            Text(pose.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
            const SizedBox(height: 4),
            Wrap(spacing: 4, runSpacing: 4, children: [
              for (final w in why.take(2)) _ReasonChip(label: w),
              if (rec.reasons.contains('check_joints')) const _ReasonChip(label: 'Check joints', warn: true),
            ]),
          ]),
        ),
      ),
      Positioned(right: 6, top: 6, child: _SaveHeart(pose: pose)),
    ]);
  }
}

class _PinterestBadge extends StatelessWidget {
  const _PinterestBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: AppColors.red,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.line, width: 2),
      ),
      child: const Text('Pinterest', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: Colors.white)),
    );
  }
}

/// "Finding Spider-Man poses on Pinterest... 6/20". The grid fills in as images are read.
class _ReferenceProgress extends StatelessWidget {
  const _ReferenceProgress({required this.progress, required this.character});

  final ReferenceSearchProgress progress;
  final String character;

  @override
  Widget build(BuildContext context) {
    final p = progress;
    final (title, body) = switch (p.status) {
      'running' => (
          'Finding $character poses on Pinterest',
          p.total == 0
              ? 'Searching...'
              : 'Checked ${p.checked} of ${p.total} photos, ${p.found} usable so far. New ones appear below as they are read.',
        ),
      'failed' => ("Couldn't search Pinterest", p.error ?? 'Try again later.'),
      _ => p.found == 0
          ? ('No usable Pinterest photos', 'None of the photos found for $character showed a full, readable pose.')
          : ('${p.found} poses from Pinterest', 'Kept for your own reference.'),
    };
    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          if (p.isRunning)
            const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.5, color: AppColors.yellow))
          else
            const Icon(Icons.push_pin_rounded, size: 18, color: AppColors.red),
          const SizedBox(width: 10),
          Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Text(body, style: const TextStyle(fontSize: 13, color: AppColors.mute)),
        if (p.isRunning && p.total > 0) ...[
          const SizedBox(height: 10),
          LinearProgressIndicator(value: p.checked / p.total, color: AppColors.yellow, backgroundColor: Colors.white24),
        ],
      ]),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({required this.rec, required this.typeOnly, required this.analysisId});

  final PoseRecommendation rec;
  final bool typeOnly;

  /// The detail screen reads this recommendation's steps (and AI visual offer) from the analysis.
  final String analysisId;

  @override
  Widget build(BuildContext context) {
    final pose = rec.pose;
    // The save button sits outside the card's merged label, so screen readers can reach it on its own.
    return Stack(children: [
      _card(context, pose),
      Positioned(right: 8, top: 48, child: _SaveHeart(pose: pose)),
    ]);
  }

  Widget _card(BuildContext context, Pose pose) {
    return Semantics(
      button: true,
      label: '${rec.rank}. ${pose.name}, ${pose.meta}${rec.mirrored ? ', mirror it' : ''}',
      excludeSemantics: true,
      child: GestureDetector(
        onTap: () => context.push(Uri(path: '/poses/${pose.id}', queryParameters: {
          if (rec.mirrored) 'mirrored': '1',
          'analysis': analysisId,
        }).toString()),
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

/// Save a recommended pose straight from its card (FAV-01), without opening it.
class _SaveHeart extends ConsumerWidget {
  const _SaveHeart({required this.pose});

  final Pose pose;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(favoritesProvider);
    final saved = ref.read(favoritesProvider.notifier).contains(pose);
    return GlassPanel(
      overPhoto: true,
      radius: 14,
      shadowOffset: 3,
      padding: EdgeInsets.zero,
      child: IconButton(
        onPressed: () => toggleFavorite(context, ref, pose),
        tooltip: saved ? 'Remove ${pose.name} from favorites' : 'Save ${pose.name} to favorites',
        icon: Icon(saved ? Icons.favorite_rounded : Icons.favorite_border_rounded,
            color: saved ? AppColors.red : Colors.white),
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
        // Grid tiles are narrow: a long label shortens instead of overflowing.
        Flexible(
          child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
        ),
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
