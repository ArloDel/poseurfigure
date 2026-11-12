import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../data/visual_repository.dart';
import '../domain/ai_visual.dart';

/// "Make AI visual" on a recommended pose: consent first, then the image with its AI and validation labels.
class AiVisualSection extends ConsumerStatefulWidget {
  const AiVisualSection({super.key, required this.poseId, required this.analysisId, this.mirrored = false});

  final int poseId;
  final String analysisId;
  final bool mirrored;

  @override
  ConsumerState<AiVisualSection> createState() => _AiVisualSectionState();
}

class _AiVisualSectionState extends ConsumerState<AiVisualSection> {
  AiVisual? _visual;
  String? _error;
  bool _busy = false;
  Timer? _timer;
  int _polls = 0;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _start() async {
    final agreed = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => const _ConsentSheet(),
    );
    if (agreed != true || !mounted) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final v = await ref.read(visualRepositoryProvider)
          .request(poseId: widget.poseId, analysisId: widget.analysisId, mirrored: widget.mirrored);
      if (!mounted) return;
      setState(() => _visual = v);
      _polls = 0;
      if (v.isPending) _schedule(v);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _schedule(AiVisual v) {
    if (_polls++ > 60) {
      setState(() => _error = 'This is taking longer than usual. Try again later.');
      return;
    }
    _timer = Timer(Duration(seconds: v.pollAfterSeconds ?? 2), () async {
      try {
        final next = await ref.read(visualRepositoryProvider).fetch(v.id);
        if (!mounted) return;
        setState(() => _visual = next);
        if (next.isPending) _schedule(next);
      } catch (e) {
        if (mounted) setState(() => _error = '$e');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final v = _visual;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('AI visual', style: text.titleLarge),
        const SizedBox(height: 6),
        Text('See your own figure in this pose. Optional, and separate from the catalog steps above.',
            style: text.bodySmall),
        const SizedBox(height: 12),
        if (v != null && v.isReady) _VisualCard(visual: v),
        if (v != null && v.isPending)
          const GlassPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Making your AI visual', style: TextStyle(fontWeight: FontWeight.w700)),
              SizedBox(height: 12),
              LinearProgressIndicator(color: AppColors.violet, backgroundColor: Colors.white24),
            ]),
          ),
        if (v != null && v.failed)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(v.errorMessage ?? "We couldn't make this visual.",
                style: const TextStyle(color: AppColors.red, fontWeight: FontWeight.w700)),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(_error!, style: const TextStyle(color: AppColors.red, fontWeight: FontWeight.w700)),
          ),
        if (v == null || v.failed)
          ComicButton(
            label: v == null ? 'Make AI visual' : 'Try again',
            icon: Icons.auto_awesome_rounded,
            style: ComicButtonStyle.ghost,
            busy: _busy,
            expand: true,
            onPressed: _start,
          ),
      ],
    );
  }
}

class _VisualCard extends StatelessWidget {
  const _VisualCard({required this.visual});

  final AiVisual visual;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (visual.validation) {
      'validated' => (AppColors.green, Icons.check_rounded),
      'rejected' => (AppColors.red, Icons.close_rounded),
      _ => (AppColors.yellow, Icons.help_outline_rounded),
    };
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      // Dashed-looking violet frame: visibly different from the solid comic panels of catalog photos.
      Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.violet, width: 3),
          boxShadow: const [BoxShadow(color: AppColors.line, offset: Offset(5, 5))],
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(children: [
          Image.network(visual.imageUrl!, fit: BoxFit.cover, width: double.infinity,
              semanticLabel: 'AI-generated picture of your figure in this pose',
              errorBuilder: (_, _, _) => const SizedBox(height: 160, child: Center(child: Icon(Icons.broken_image_outlined)))),
          const Positioned(left: 10, top: 10, child: _Badge(label: 'AI-generated', color: AppColors.violet, icon: Icons.auto_awesome_rounded, light: true)),
          Positioned(right: 10, top: 10, child: _Badge(label: visual.validationLabel, color: color, icon: icon)),
        ]),
      ),
      const SizedBox(height: 10),
      if (visual.isStub)
        const Padding(
          padding: EdgeInsets.only(bottom: 6),
          child: Text('Development preview: no image service is connected, so this is your original photo.',
              style: TextStyle(color: AppColors.yellow, fontWeight: FontWeight.w700, fontSize: 13)),
        ),
      if (visual.note != null) Text(visual.note!, style: const TextStyle(fontSize: 13.5, height: 1.4, color: AppColors.mute)),
    ]);
  }
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label, required this.color, required this.icon, this.light = false});

  final String label;
  final Color color;
  final IconData icon;
  final bool light;

  @override
  Widget build(BuildContext context) {
    final fg = light ? Colors.white : AppColors.line;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6), border: Border.all(color: AppColors.line, width: 2)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: fg),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(color: fg, fontWeight: FontWeight.w800, fontSize: 12)),
      ]),
    );
  }
}

/// PRD 15.1: say what is sent and where before anything leaves the device.
class _ConsentSheet extends StatelessWidget {
  const _ConsentSheet();

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: GlassPanel(
          overPhoto: true,
          radius: 28,
          padding: const EdgeInsets.fromLTRB(18, 22, 18, 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Send your photo for an AI visual?', style: TextStyle(fontFamily: 'BowlbyOne', fontSize: 21)),
            const SizedBox(height: 10),
            for (final line in const [
              'Your photo goes to an image service outside FigurePose.',
              "The result is labelled AI-generated. It isn't proof your figure can hold the pose.",
              'Deleting the analysis in History deletes the visual too.',
            ])
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Padding(padding: EdgeInsets.only(top: 6, right: 10), child: Icon(Icons.circle, size: 7, color: AppColors.yellow)),
                  Expanded(child: Text(line, style: const TextStyle(height: 1.4))),
                ]),
              ),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: ComicButton(label: 'Not now', style: ComicButtonStyle.ghost, onPressed: () => Navigator.pop(context, false)),
              ),
              const SizedBox(width: 10),
              Expanded(child: ComicButton(label: 'Send and make', onPressed: () => Navigator.pop(context, true))),
            ]),
          ]),
        ),
      ),
    );
  }
}
