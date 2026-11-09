import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_colors.dart';
import 'comic_backdrop.dart';
import 'glass_panel.dart';

/// Four primary destinations in a floating glass bar (PRD 6.2 / 12.3).
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.shell});

  final StatefulNavigationShell shell;

  static const _tabs = [
    (Icons.home_rounded, 'Home'),
    (Icons.explore_rounded, 'Discover'),
    (Icons.favorite_rounded, 'Favorites'),
    (Icons.person_rounded, 'Profile'),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: ComicBackdrop(
        child: SafeArea(
          bottom: false,
          child: Stack(
            children: [
              Positioned.fill(child: shell),
              Positioned(
                left: 14,
                right: 14,
                bottom: 22 + MediaQuery.paddingOf(context).bottom,
                child: GlassPanel(
                  radius: 24,
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8),
                  child: Row(
                    children: [
                      for (var i = 0; i < _tabs.length; i++)
                        Expanded(child: _NavItem(icon: _tabs[i].$1, label: _tabs[i].$2, selected: shell.currentIndex == i,
                            onTap: () => shell.goBranch(i, initialLocation: i == shell.currentIndex))),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.label, required this.selected, required this.onTap});

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      label: label,
      child: InkResponse(
        onTap: onTap,
        radius: 36,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              width: 52,
              height: 32,
              decoration: BoxDecoration(
                color: selected ? AppColors.yellow : Colors.transparent,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: selected ? AppColors.line : Colors.transparent, width: 2),
                boxShadow: selected ? const [BoxShadow(color: AppColors.line, offset: Offset(2, 2))] : null,
              ),
              child: Icon(icon, size: 22, color: selected ? AppColors.line : AppColors.chalk),
            ),
            const SizedBox(height: 3),
            Text(label, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}
