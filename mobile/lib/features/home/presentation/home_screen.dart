import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/comic_panel.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../analysis/data/analysis_repository.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _uploading = false;

  Future<void> _pick(ImageSource source) async {
    final photo = await ImagePicker().pickImage(source: source, maxWidth: 4000, imageQuality: 92);
    if (photo == null || !mounted) return;

    setState(() => _uploading = true);
    try {
      final id = await ref.read(analysisRepositoryProvider).start(photo);
      if (mounted) context.go('/analysis/$id');
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;

    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 120),
      children: [
        Text('Good evening, collector', style: text.bodySmall),
        const SizedBox(height: 2),
        Text('Ready to pose?', style: text.headlineMedium),
        const SizedBox(height: 16),
        SizedBox(
          height: 330,
          child: ComicPanel(
            child: Stack(
              fit: StackFit.expand,
              children: [
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: _CollagePhoto('assets/images/optimus-stance.jpg')),
                    _Divider(),
                    Expanded(flex: 6, child: _CollagePhoto('assets/images/rider-stance.jpg', alignment: Alignment(0, -.4))),
                    _Divider(),
                    Expanded(child: _CollagePhoto('assets/images/claymore-draw.jpg')),
                  ],
                ),
                Positioned(
                  left: 12,
                  right: 12,
                  bottom: 12,
                  child: GlassPanel(
                    overPhoto: true,
                    shadowOffset: 3,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Analyze a figure', style: text.titleLarge),
                        const SizedBox(height: 4),
                        const Text('Get 3 to 5 poses with step-by-step joint guidance.'),
                        const SizedBox(height: 12),
                        Row(children: [
                          Expanded(
                            child: ComicButton(
                              label: 'Camera',
                              icon: Icons.photo_camera_rounded,
                              busy: _uploading,
                              onPressed: () => _pick(ImageSource.camera),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: ComicButton(
                              label: 'Gallery',
                              icon: Icons.photo_library_rounded,
                              style: ComicButtonStyle.ghost,
                              onPressed: _uploading ? null : () => _pick(ImageSource.gallery),
                            ),
                          ),
                        ]),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 22),
        const _ServerStatus(),
      ],
    );
  }
}

class _CollagePhoto extends StatelessWidget {
  const _CollagePhoto(this.asset, {this.alignment = Alignment.center});

  final String asset;
  final Alignment alignment;

  @override
  Widget build(BuildContext context) =>
      Image.asset(asset, fit: BoxFit.cover, alignment: alignment, errorBuilder: (_, _, _) => const SizedBox());
}

class _Divider extends StatelessWidget {
  const _Divider();

  @override
  Widget build(BuildContext context) => const ColoredBox(color: AppColors.line, child: SizedBox(width: 3));
}

class _ServerStatus extends ConsumerWidget {
  const _ServerStatus();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final health = ref.watch(serverHealthProvider);
    final (color, label) = switch (health) {
      AsyncData(value: true) => (AppColors.green, 'Server connected'),
      AsyncData() || AsyncError() => (AppColors.red, "Can't reach the server"),
      _ => (AppColors.yellow, 'Checking server'),
    };
    return GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle, border: Border.all(color: AppColors.line, width: 2)),
        ),
        const SizedBox(width: 10),
        Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700))),
        TextButton(onPressed: () => ref.invalidate(serverHealthProvider), child: const Text('Retry')),
      ]),
    );
  }
}
