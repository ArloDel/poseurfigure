import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/state_panels.dart';
import '../application/pose_providers.dart';
import 'widgets/pose_card.dart';

/// Pose gallery (PRD 6.1 "Pose Gallery"): browse the catalog by type, category and name.
class DiscoverScreen extends ConsumerStatefulWidget {
  const DiscoverScreen({super.key});

  static const profiles = [('humanoid_v1', 'Humanoid'), ('anime_v1', 'Anime'), ('mecha_v1', 'Mecha')];
  static const categories = [(null, 'All'), ('action', 'Action'), ('cinematic', 'Cinematic'), ('display', 'Display'), ('calm', 'Calm')];

  @override
  ConsumerState<DiscoverScreen> createState() => _DiscoverScreenState();
}

class _DiscoverScreenState extends ConsumerState<DiscoverScreen> {
  late final _search = TextEditingController(text: ref.read(poseQueryProvider).text);
  Timer? _debounce;

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _onSearch(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () => ref.read(poseQueryProvider.notifier).setText(value));
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final query = ref.watch(poseQueryProvider);
    final poses = ref.watch(posesProvider);
    final controller = ref.read(poseQueryProvider.notifier);

    return RefreshIndicator(
      color: AppColors.yellow,
      onRefresh: () => ref.refresh(posesProvider.future),
      child: CustomScrollView(
        slivers: [
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 0),
            sliver: SliverList.list(children: [
              Text('Pose gallery', style: text.headlineMedium),
              const SizedBox(height: 4),
              Text(
                poses.hasValue ? '${poses.value!.length} poses, each with joint steps.' : 'Poses, each with joint steps.',
                style: text.bodyLarge?.copyWith(color: AppColors.mute),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _search,
                onChanged: _onSearch,
                textInputAction: TextInputAction.search,
                decoration: const InputDecoration(
                  hintText: 'Search poses, like "lunge"',
                  prefixIcon: Icon(Icons.search_rounded, color: AppColors.mute),
                ),
              ),
              const SizedBox(height: 14),
              GlassPanel(
                padding: const EdgeInsets.all(4),
                radius: 16,
                child: Row(children: [
                  for (final (id, label) in DiscoverScreen.profiles)
                    Expanded(child: _Segment(label: label, selected: query.profile == id, onTap: () => controller.toggleProfile(id))),
                ]),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 36,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (final (id, label) in DiscoverScreen.categories)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: _Chip(label: label, selected: query.category == id, onTap: () => controller.setCategory(id)),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
            ]),
          ),
          ...switch (poses) {
            AsyncData(:final value) when value.isEmpty => [
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.symmetric(horizontal: 18),
                    child: EmptyState(
                      icon: Icons.search_off_rounded,
                      title: 'No poses match',
                      message: 'Try another category or figure type, or clear the search.',
                    ),
                  ),
                ),
              ],
            AsyncData(:final value) => [
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(18, 0, 18, 120),
                  sliver: SliverGrid.builder(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      mainAxisSpacing: 16,
                      crossAxisSpacing: 14,
                      childAspectRatio: .74,
                    ),
                    itemCount: value.length,
                    itemBuilder: (context, i) =>
                        PoseCard(pose: value[i], onTap: () => context.push('/poses/${value[i].id}')),
                  ),
                ),
              ],
            AsyncError(:final error) => [
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: 18),
                  sliver: SliverToBoxAdapter(
                    child: ErrorPanel(message: '$error', onRetry: () => ref.invalidate(posesProvider)),
                  ),
                ),
              ],
            _ => [const SliverToBoxAdapter(child: LoadingPanel())],
          },
        ],
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  const _Segment({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          height: 38,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppColors.chalk : Colors.transparent,
            borderRadius: BorderRadius.circular(11),
            border: Border.all(color: selected ? AppColors.line : Colors.transparent, width: 2),
          ),
          child: Text(label,
              style: TextStyle(fontWeight: FontWeight.w700, color: selected ? AppColors.line : AppColors.chalk)),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.selected, required this.onTap});

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: selected ? AppColors.chalk : Colors.white.withValues(alpha: .14),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: AppColors.line, width: 2),
          ),
          child: Text(label,
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: selected ? AppColors.line : AppColors.chalk)),
        ),
      ),
    );
  }
}
