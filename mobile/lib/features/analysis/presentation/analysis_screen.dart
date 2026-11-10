import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../data/analysis_repository.dart';
import '../domain/analysis.dart';

/// Polls GET /analyses/{id} every 2-3 s with backoff and a timeout (PRD 11.4).
class AnalysisScreen extends ConsumerStatefulWidget {
  const AnalysisScreen({super.key, required this.analysisId});

  final String analysisId;

  @override
  ConsumerState<AnalysisScreen> createState() => _AnalysisScreenState();
}

class _AnalysisScreenState extends ConsumerState<AnalysisScreen> {
  static const _timeout = Duration(minutes: 2);

  Analysis? _analysis;
  String? _error;
  Timer? _timer;
  int _polls = 0;
  final _started = DateTime.now();

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

  @override
  Widget build(BuildContext context) {
    final a = _analysis;
    final text = Theme.of(context).textTheme;

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
                AnalysisStatus.completed => 'Photo checked',
                AnalysisStatus.failed => "Can't use this photo",
                _ => 'Analyzing',
              }, style: text.headlineMedium),
              const SizedBox(height: 16),
              GlassPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _Row(label: 'Status', value: a?.status.name ?? 'connecting'),
                    if (a?.sharpness != null) _Row(label: 'Sharpness', value: a!.sharpness!.toStringAsFixed(0)),
                    _Row(label: 'Analysis id', value: widget.analysisId.substring(0, 8)),
                    if (a != null && !a.status.isFinal) ...[
                      const SizedBox(height: 12),
                      const LinearProgressIndicator(color: AppColors.yellow, backgroundColor: Colors.white24),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (a?.status == AnalysisStatus.failed)
                GlassPanel(
                  child: Text(a!.errorMessage ?? 'This photo could not be analyzed.', style: text.titleMedium),
                ),
              if (a?.status == AnalysisStatus.completed)
                Text(
                  'Your photo passed the quality check. Pose detection and recommendations arrive in a later sprint.',
                  style: text.bodyLarge,
                ),
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

class _Row extends StatelessWidget {
  const _Row({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Text(label, style: const TextStyle(color: AppColors.mute)),
        const Spacer(),
        Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
      ]),
    );
  }
}
