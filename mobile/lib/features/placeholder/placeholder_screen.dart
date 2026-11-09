import 'package:flutter/material.dart';

import '../../shared/widgets/glass_panel.dart';

/// Discover, Favorites and Profile are built in later sprints; the tabs exist so navigation is final.
class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen({super.key, required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 120),
      children: [
        Text(title, style: text.headlineMedium),
        const SizedBox(height: 16),
        GlassPanel(child: Text(message, style: text.bodyLarge)),
      ],
    );
  }
}
