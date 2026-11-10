import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/dates.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/state_panels.dart';
import '../../analysis/data/analysis_repository.dart';
import '../../analysis/domain/analysis.dart';
import '../application/history_provider.dart';

/// Previous analyses, with delete (HIST-01..03).
class HistoryScreen extends ConsumerWidget {
  const HistoryScreen({super.key});

  Future<void> _delete(BuildContext context, WidgetRef ref, Analysis a) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.ink,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: const BorderSide(color: AppColors.line, width: 2.5),
        ),
        title: const Text('Delete this analysis?', style: TextStyle(fontFamily: 'BowlbyOne')),
        content: const Text('The analysis and your photo are deleted from the server. This can\'t be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete', style: TextStyle(color: AppColors.red, fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(analysisRepositoryProvider).delete(a.id);
      ref.invalidate(historyProvider);
      messenger.showSnackBar(const SnackBar(content: Text('Analysis and photo deleted')));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final history = ref.watch(historyProvider);

    return Scaffold(
      body: ComicBackdrop(
        child: SafeArea(
          child: RefreshIndicator(
            color: AppColors.yellow,
            onRefresh: () => ref.refresh(historyProvider.future),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
              children: [
                Row(children: [
                  IconButton.filledTonal(
                    onPressed: () => context.canPop() ? context.pop() : context.go('/'),
                    icon: const Icon(Icons.arrow_back_rounded),
                    tooltip: 'Back',
                  ),
                  const SizedBox(width: 12),
                  Text('History', style: text.headlineMedium),
                ]),
                const SizedBox(height: 18),
                ...switch (history) {
                  AsyncData(:final value) when value.isEmpty => [
                      EmptyState(
                        icon: Icons.photo_camera_back_rounded,
                        title: 'No analyses yet',
                        message: 'Photos you analyze show up here, newest first.',
                        action: ComicButton(label: 'Analyze a figure', icon: Icons.photo_camera_rounded, onPressed: () => context.go('/')),
                      ),
                    ],
                  AsyncData(:final value) => [
                      for (final a in value)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _HistoryRow(analysis: a, onDelete: () => _delete(context, ref, a)),
                        ),
                      Text('Original photos are deleted after 30 days.', style: text.bodySmall, textAlign: TextAlign.center),
                    ],
                  AsyncError(:final error) => [ErrorPanel(message: '$error', onRetry: () => ref.invalidate(historyProvider))],
                  _ => [const LoadingPanel()],
                },
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.analysis, required this.onDelete});

  final Analysis analysis;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final a = analysis;
    final (label, color, icon) = switch (a.status) {
      AnalysisStatus.completed => (
          a.recommendationCount > 0 ? 'Completed, ${a.recommendationCount} poses' : 'Completed, photo checked',
          AppColors.green,
          Icons.check_rounded,
        ),
      AnalysisStatus.failed => ('Failed, ${_shortReason(a)}', AppColors.red, Icons.close_rounded),
      _ => ('Processing', AppColors.yellow, Icons.hourglass_top_rounded),
    };

    return GlassPanel(
      padding: const EdgeInsets.all(10),
      child: Row(children: [
        Container(
          width: 56,
          height: 64,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppColors.line, width: 2.5),
            boxShadow: const [BoxShadow(color: AppColors.line, offset: Offset(3, 3))],
          ),
          child: Icon(icon, color: AppColors.line, size: 28),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: InkWell(
            onTap: () => context.push('/analysis/${a.id}'),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(a.createdAt != null ? friendlyDate(a.createdAt!) : 'Analysis',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15.5)),
              const SizedBox(height: 3),
              Text(label, style: const TextStyle(fontSize: 13, color: AppColors.mute)),
            ]),
          ),
        ),
        IconButton(onPressed: onDelete, icon: const Icon(Icons.delete_outline_rounded), tooltip: 'Delete analysis and photo'),
      ]),
    );
  }

  static String _shortReason(Analysis a) => switch (a.errorCode) {
        'blurry' => 'photo too blurry',
        'too_dark' => 'photo too dark',
        'too_bright' => 'photo too bright',
        'too_small' => 'photo too small',
        'ai_unavailable' => 'try again later',
        _ => 'photo not usable',
      };
}
