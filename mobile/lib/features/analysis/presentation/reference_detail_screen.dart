import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_panel.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/pose_photo.dart';
import '../../../shared/widgets/state_panels.dart';
import '../../poses/presentation/widgets/your_steps.dart';
import '../data/analysis_repository.dart';

/// A pose found on Pinterest for the figure's character: the photo and the steps from the user's figure.
/// The photo belongs to whoever posted it; the app keeps it for the user's own reference only.
class ReferenceDetailScreen extends ConsumerWidget {
  const ReferenceDetailScreen({super.key, required this.referenceId, required this.analysisId});

  final int referenceId;
  final String analysisId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final analysis = ref.watch(analysisResultProvider(analysisId));
    final rec = analysis.value?.recommendations
        .where((r) => r.pose.isReference && r.pose.id == referenceId)
        .firstOrNull;

    return Scaffold(
      body: ComicBackdrop(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: IconButton.filledTonal(
                  onPressed: () => context.canPop() ? context.pop() : context.go('/'),
                  icon: const Icon(Icons.arrow_back_rounded),
                  tooltip: 'Back',
                ),
              ),
              const SizedBox(height: 12),
              ...switch ((analysis, rec)) {
                (AsyncData(), final rec?) => [
                    AspectRatio(
                      aspectRatio: 3 / 4,
                      child: ComicPanel(child: PosePhoto(url: rec.pose.imageUrl, semanticLabel: rec.pose.name)),
                    ),
                    const SizedBox(height: 16),
                    Text(rec.pose.name, style: text.headlineMedium),
                    const SizedBox(height: 8),
                    const _PinterestNote(),
                    const SizedBox(height: 22),
                    if (rec.changes.isNotEmpty) ...[
                      Text('From your figure', style: text.titleLarge),
                      const SizedBox(height: 12),
                      YourSteps(changes: rec.changes),
                    ] else
                      GlassPanel(child: Text("We couldn't compare this pose with your figure's.", style: text.bodyLarge)),
                  ],
                (AsyncError(:final error), _) => [
                    ErrorPanel(message: '$error', onRetry: () => ref.invalidate(analysisResultProvider(analysisId))),
                  ],
                (AsyncData(), null) => [
                    GlassPanel(child: Text("This reference isn't in this analysis' ideas anymore.", style: text.bodyLarge)),
                  ],
                _ => [const LoadingPanel()],
              },
            ],
          ),
        ),
      ),
    );
  }
}

class _PinterestNote extends StatelessWidget {
  const _PinterestNote();

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: const [
        Icon(Icons.push_pin_rounded, color: AppColors.red),
        SizedBox(width: 10),
        Expanded(
          child: Text(
            'Found on Pinterest and kept for your own reference. The photo belongs to whoever posted it; '
            "don't share it as yours.",
            style: TextStyle(height: 1.4),
          ),
        ),
      ]),
    );
  }
}
