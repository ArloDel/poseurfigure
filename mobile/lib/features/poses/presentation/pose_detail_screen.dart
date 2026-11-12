import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/labels.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/pose_photo.dart';
import '../../../shared/widgets/state_panels.dart';
import '../../auth/application/session_controller.dart';
import '../../favorites/application/favorites_controller.dart';
import '../application/pose_providers.dart';
import '../domain/pose.dart';

/// Pose detail (PRD 4.6 / 13): photo, joint steps by body region, warnings, save.
class PoseDetailScreen extends ConsumerWidget {
  const PoseDetailScreen({super.key, required this.poseId, this.mirrored = false});

  final int poseId;

  /// Opened from a recommendation where the user's figure matches this pose mirrored.
  final bool mirrored;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final pose = ref.watch(poseDetailProvider(poseId));

    return Scaffold(
      body: ComicBackdrop(
        child: switch (pose) {
          AsyncData(:final value) => _Detail(pose: value, mirrored: mirrored),
          AsyncError(:final error) => SafeArea(
              child: ListView(padding: const EdgeInsets.all(18), children: [
                const _BackButton(),
                const SizedBox(height: 16),
                ErrorPanel(message: '$error', onRetry: () => ref.invalidate(poseDetailProvider(poseId))),
              ]),
            ),
          _ => const SafeArea(child: Column(children: [Padding(padding: EdgeInsets.all(18), child: _BackButton()), LoadingPanel()])),
        },
      ),
    );
  }
}

class _Detail extends StatelessWidget {
  const _Detail({required this.pose, this.mirrored = false});

  final Pose pose;
  final bool mirrored;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final topInset = MediaQuery.paddingOf(context).top;
    final groups = <BodyRegion, List<PoseInstruction>>{};
    for (final i in pose.instructions) {
      groups.putIfAbsent(i.region, () => []).add(i);
    }

    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.only(bottom: 120),
          children: [
            SizedBox(
              height: 400 + topInset,
              child: DecoratedBox(
                position: DecorationPosition.foreground,
                decoration: BoxDecoration(
                  border: const Border(bottom: BorderSide(color: AppColors.line, width: 3)),
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: const Alignment(0, -.4),
                    colors: [AppColors.ink.withValues(alpha: .75), AppColors.ink.withValues(alpha: 0)],
                  ),
                ),
                child: PosePhoto(url: pose.imageUrl, semanticLabel: pose.name),
              ),
            ),
            Transform.translate(
              offset: const Offset(0, -46),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 22),
                child: GlassPanel(
                  overPhoto: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(pose.name, style: text.headlineMedium),
                      const SizedBox(height: 10),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        _Tag(capitalize(pose.category)),
                        _Tag(capitalize(pose.difficulty)),
                        const _SourceBadge(),
                      ]),
                      if (pose.description != null) ...[
                        const SizedBox(height: 12),
                        Text(pose.description!, style: text.bodyLarge?.copyWith(color: const Color(0xFFE2E5FF))),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 0, 18, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text('How to pose it', style: text.titleLarge),
                  const SizedBox(height: 12),
                  if (mirrored)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 12),
                      child: _Note(
                        icon: Icons.flip_rounded,
                        tint: AppColors.violet,
                        title: 'Mirror it',
                        body: 'Your figure is already close to the mirror image of this pose. Swap left and right in every step below.',
                      ),
                    ),
                  for (final region in BodyRegion.values)
                    if (groups[region] case final steps?)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _StepGroup(title: _regionTitle(region), steps: steps),
                      ),
                  for (final w in pose.warnings)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _Note(
                        icon: Icons.warning_amber_rounded,
                        tint: AppColors.red,
                        title: '${humanize(w.joint)} may not bend this far',
                        body: '${w.targetAngle}° is past the usual range for many figures. Try it gently and stop if the joint resists.',
                      ),
                    ),
                  const _Note(
                    icon: Icons.info_outline_rounded,
                    tint: AppColors.blue,
                    title: 'Angles are estimates',
                    body: "They come from a 2D reference photo. Twist and depth can't be read exactly.",
                  ),
                  if (pose.credit != null) ...[
                    const SizedBox(height: 14),
                    Text('Photo: ${pose.credit}', style: text.bodySmall),
                  ],
                ],
              ),
            ),
          ],
        ),
        Positioned(top: topInset + 10, left: 18, child: const _BackButton(overPhoto: true)),
        Positioned(left: 14, right: 14, bottom: 22 + MediaQuery.paddingOf(context).bottom, child: _SaveBar(pose: pose)),
      ],
    );
  }

  static String _regionTitle(BodyRegion r) => switch (r) {
        BodyRegion.headAndTorso => 'Head and torso',
        BodyRegion.arms => 'Arms',
        BodyRegion.legs => 'Legs',
      };
}

class _StepGroup extends StatelessWidget {
  const _StepGroup({required this.title, required this.steps});

  final String title;
  final List<PoseInstruction> steps;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                fontFamily: 'BowlbyOne',
                fontSize: 15,
                color: AppColors.yellow,
                shadows: [Shadow(color: AppColors.line, offset: Offset(1.5, 1.5))],
              )),
          for (final (i, s) in steps.indexed) ...[
            if (i > 0) Divider(height: 1, color: Colors.white.withValues(alpha: .16)),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 26,
                  height: 26,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.chalk,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.line, width: 2),
                  ),
                  child: Text('${s.step}',
                      style: const TextStyle(color: AppColors.line, fontWeight: FontWeight.w800, fontSize: 13)),
                ),
                const SizedBox(width: 12),
                Expanded(child: Text(s.title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5))),
                if (s.targetAngle != null)
                  Text('${s.targetAngle}°', style: const TextStyle(fontFamily: 'BowlbyOne', fontSize: 16)),
              ]),
            ),
          ],
        ],
      ),
    );
  }
}

class _SaveBar extends ConsumerStatefulWidget {
  const _SaveBar({required this.pose});

  final Pose pose;

  @override
  ConsumerState<_SaveBar> createState() => _SaveBarState();
}

class _SaveBarState extends ConsumerState<_SaveBar> {
  bool _busy = false;

  Future<void> _toggle() async {
    final messenger = ScaffoldMessenger.of(context);
    final user = ref.read(sessionProvider).value;
    if (user == null) {
      messenger.showSnackBar(SnackBar(
        content: const Text('Sign in to save poses to your favorites.'),
        action: SnackBarAction(label: 'Sign in', onPressed: () => context.push('/sign-in')),
      ));
      return;
    }
    final wasSaved = ref.read(favoritesProvider.notifier).contains(widget.pose.id);
    setState(() => _busy = true);
    try {
      await ref.read(favoritesProvider.notifier).toggle(widget.pose);
      messenger.showSnackBar(SnackBar(content: Text(wasSaved ? 'Removed from favorites' : 'Saved to favorites')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.watch(favoritesProvider);
    final saved = ref.read(favoritesProvider.notifier).contains(widget.pose.id);
    return GlassPanel(
      radius: 24,
      padding: const EdgeInsets.all(10),
      child: ComicButton(
        label: saved ? 'Saved to favorites' : 'Save to favorites',
        icon: saved ? Icons.favorite_rounded : Icons.favorite_border_rounded,
        style: saved ? ComicButtonStyle.ghost : ComicButtonStyle.pow,
        busy: _busy,
        expand: true,
        onPressed: _toggle,
      ),
    );
  }
}

class _BackButton extends StatelessWidget {
  const _BackButton({this.overPhoto = false});

  final bool overPhoto;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Back',
      child: GestureDetector(
        onTap: () => context.canPop() ? context.pop() : context.go('/discover'),
        child: GlassPanel(
          overPhoto: overPhoto,
          radius: 14,
          shadowOffset: 3,
          padding: const EdgeInsets.all(10),
          child: const Icon(Icons.arrow_back_rounded, size: 22),
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: .14),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.line, width: 2),
      ),
      child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
    );
  }
}

/// Catalog photos are curated references. AI-generated ones get their own, different badge (REC-09/10).
class _SourceBadge extends StatelessWidget {
  const _SourceBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
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

class _Note extends StatelessWidget {
  const _Note({required this.icon, required this.tint, required this.title, required this.body});

  final IconData icon;
  final Color tint;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        gradient: LinearGradient(colors: [tint.withValues(alpha: .45), tint.withValues(alpha: .14)]),
      ),
      child: GlassPanel(
        radius: 18,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(icon, color: Colors.white),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
              const SizedBox(height: 3),
              Text(body, style: const TextStyle(fontSize: 13.5, height: 1.4, color: Color(0xFFE4E6FF))),
            ]),
          ),
        ]),
      ),
    );
  }
}
