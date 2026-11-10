import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/utils/labels.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/comic_panel.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../data/analysis_repository.dart';
import '../domain/analysis.dart';
import 'widgets/skeleton_overlay.dart';

/// Polls GET /analyses/{id} every 2-3 s with backoff and a timeout (PRD 11.4), then shows
/// the detected figure type, the skeleton and hidden joints.
class AnalysisScreen extends ConsumerStatefulWidget {
  const AnalysisScreen({super.key, required this.analysisId, this.photo});

  final String analysisId;

  /// The photo just uploaded, if this screen was opened right after upload.
  /// From History there is none: original photos stay private on the server.
  final Uint8List? photo;

  @override
  ConsumerState<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends ConsumerState<AnalysisScreen> {
  static const _timeout = Duration(minutes: 2);

  Analysis? _analysis;
  String? _error;
  Timer? _timer;
  int _polls = 0;
  DateTime _started = DateTime.now();
  bool _confirming = false;

  @override
  void initState() {
    super.initState();
    _poll();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _poll() async {
    try {
      final a = await ref.read(analysisRepositoryProvider).fetch(widget.analysisId);
      if (!mounted) return;
      setState(() {
        _analysis = a;
        _error = null;
      });
      if (a.status.isFinal) return;
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    }
    if (DateTime.now().difference(_started) > _timeout) {
      setState(() => _error = 'This is taking longer than usual. Check History later.');
      return;
    }
    _polls++;
    final base = _analysis?.pollAfterSeconds ?? 2;
    final wait = Duration(seconds: (base + _polls ~/ 5).clamp(2, 8)); // gentle backoff
    _timer = Timer(wait, _poll);
  }

  Future<void> _confirmType(String slug) async {
    setState(() => _confirming = true);
    final repo = ref.read(analysisRepositoryProvider);
    try {
      final ids = await repo.profileIds();
      await repo.confirmProfile(widget.analysisId, ids[slug]!);
      if (!mounted) return;
      setState(() {
        _analysis = null;
        _polls = 0;
        _started = DateTime.now();
      });
      _poll();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _confirming = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final a = _analysis;
    final text = Theme.of(context).textTheme;
    final done = a?.status == AnalysisStatus.completed;

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
              Text(switch (a?.status) {
                AnalysisStatus.completed => 'Your figure',
                AnalysisStatus.failed => "Can't use this photo",
                _ => 'Analyzing',
              }, style: text.headlineMedium),
              const SizedBox(height: 16),
              if (done && a!.pose != null && widget.photo != null && a.imageWidth != null && a.imageHeight != null) ...[
                ComicPanel(
                  child: SkeletonOverlay(photo: widget.photo!, pose: a.pose!, aspectRatio: a.imageWidth! / a.imageHeight!),
                ),
                const SizedBox(height: 18),
              ],
              if (done && a!.typeGuess != null) ...[
                _TypeCard(guess: a.typeGuess!, busy: _confirming, onPick: _confirmType),
                const SizedBox(height: 14),
              ],
              if (done && a!.pose != null) ...[
                _JointsCard(pose: a.pose!),
                const SizedBox(height: 14),
                Text('Pose ideas based on these joints arrive in the next update.', style: text.bodySmall),
              ],
              if (a == null || !a.status.isFinal)
                GlassPanel(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_confirming ? 'Analyzing again with your figure type' : 'Finding the figure and its joints',
                        style: const TextStyle(fontWeight: FontWeight.w700)),
                    const SizedBox(height: 12),
                    const LinearProgressIndicator(color: AppColors.yellow, backgroundColor: Colors.white24),
                    const SizedBox(height: 8),
                    Text('Usually under 15 seconds.', style: text.bodySmall),
                  ]),
                ),
              if (a?.status == AnalysisStatus.failed)
                GlassPanel(child: Text(a!.errorMessage ?? 'This photo could not be analyzed.', style: text.titleMedium)),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: text.bodyLarge?.copyWith(color: AppColors.red)),
              ],
              const SizedBox(height: 24),
              if (a?.status.isFinal == true || _error != null)
                ComicButton(label: 'Try another photo', icon: Icons.photo_library_rounded, expand: true, onPressed: () => context.go('/')),
            ],
          ),
        ),
      ),
    );
  }
}

/// Figure type, with a picker when the model isn't sure (FIG-03).
class _TypeCard extends StatelessWidget {
  const _TypeCard({required this.guess, required this.busy, required this.onPick});

  final FigureTypeGuess guess;
  final bool busy;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    final name = profileNames[guess.profile] ?? humanize(guess.profile);
    final ask = guess.needsConfirmation && !guess.byUser;
    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(ask ? 'Is this a ${name.toLowerCase()} figure?' : '$name figure',
            style: const TextStyle(fontFamily: 'BowlbyOne', fontSize: 19)),
        const SizedBox(height: 4),
        Text(
          guess.byUser
              ? 'You picked this type.'
              : ask
                  ? "We're not sure (${(guess.confidence * 100).round()}%). Pick the type so we read the right joints."
                  : '${(guess.confidence * 100).round()}% sure. Wrong? Pick another type.',
          style: const TextStyle(color: AppColors.mute),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final MapEntry(key: slug, value: label) in profileNames.entries)
            ChoiceChip(
              label: Text(label),
              selected: slug == guess.profile && !ask,
              onSelected: busy || (slug == guess.profile && !ask) ? null : (_) => onPick(slug),
            ),
        ]),
      ]),
    );
  }
}

class _JointsCard extends StatelessWidget {
  const _JointsCard({required this.pose});

  final PoseResult pose;

  @override
  Widget build(BuildContext context) {
    final angles = pose.angles.entries.toList();
    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${pose.visibleCount} of ${pose.estimableCount} joints found',
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
        const SizedBox(height: 4),
        Text(pose.hiddenSummary, style: TextStyle(color: pose.hidden.isEmpty ? AppColors.green : AppColors.yellow)),
        if (pose.orientation != 'unknown') ...[
          const SizedBox(height: 4),
          Text('Seen from the ${pose.orientation}', style: const TextStyle(color: AppColors.mute)),
        ],
        if (angles.isNotEmpty) ...[
          const SizedBox(height: 12),
          for (final e in angles)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(children: [
                Expanded(child: Text(humanize(e.key))),
                Text('${e.value.round()}°', style: const TextStyle(fontFamily: 'BowlbyOne')),
              ]),
            ),
          const SizedBox(height: 6),
          const Text('Angles are 2D estimates from the photo, 180° = straight.', style: TextStyle(fontSize: 12, color: AppColors.mute)),
        ],
      ]),
    );
  }
}
