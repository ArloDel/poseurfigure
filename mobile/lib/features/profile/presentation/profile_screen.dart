import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../../../shared/widgets/state_panels.dart';
import '../../auth/application/session_controller.dart';
import '../../auth/domain/app_user.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final text = Theme.of(context).textTheme;
    final session = ref.watch(sessionProvider);

    return ListView(
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 120),
      children: [
        Text('Profile', style: text.headlineMedium),
        const SizedBox(height: 14),
        switch (session) {
          AsyncData(:final value?) => _AccountCard(user: value),
          AsyncData() => const _GuestCard(),
          AsyncError(:final error) => ErrorPanel(message: '$error', onRetry: () => ref.invalidate(sessionProvider)),
          _ => const LoadingPanel(),
        },
        const SizedBox(height: 22),
        Text('App', style: text.titleLarge),
        const SizedBox(height: 12),
        GlassPanel(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Column(children: [
            ListTile(
              leading: const Icon(Icons.history_rounded),
              title: const Text('Analysis history', style: TextStyle(fontWeight: FontWeight.w700)),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => context.push('/history'),
            ),
            Divider(height: 1, color: Colors.white.withValues(alpha: .16)),
            const ListTile(
              leading: Icon(Icons.info_outline_rounded),
              title: Text('About FigurePose', style: TextStyle(fontWeight: FontWeight.w700)),
              subtitle: Text('Version 0.1. Angles are 2D estimates, not measurements.'),
            ),
          ]),
        ),
      ],
    );
  }
}

class _GuestCard extends StatelessWidget {
  const _GuestCard();

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [
          _Avatar(icon: Icons.person_outline_rounded),
          SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Guest collector', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
              SizedBox(height: 3),
              Text('You can analyze figures without an account.', style: TextStyle(color: AppColors.mute, fontSize: 13)),
            ]),
          ),
        ]),
        const SizedBox(height: 14),
        const Text('Sign in to save favorites and keep your history on every device.'),
        const SizedBox(height: 14),
        Row(children: [
          Expanded(child: ComicButton(label: 'Create account', onPressed: () => context.push('/sign-in?mode=register'))),
          const SizedBox(width: 10),
          Expanded(
            child: ComicButton(label: 'Sign in', style: ComicButtonStyle.ghost, onPressed: () => context.push('/sign-in')),
          ),
        ]),
      ]),
    );
  }
}

class _AccountCard extends ConsumerStatefulWidget {
  const _AccountCard({required this.user});

  final AppUser user;

  @override
  ConsumerState<_AccountCard> createState() => _AccountCardState();
}

class _AccountCardState extends ConsumerState<_AccountCard> {
  bool _busy = false;

  Future<void> _signOut() async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _busy = true);
    await ref.read(sessionProvider.notifier).signOut();
    if (mounted) setState(() => _busy = false);
    messenger.showSnackBar(const SnackBar(content: Text('Signed out')));
  }

  @override
  Widget build(BuildContext context) {
    final u = widget.user;
    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const _Avatar(icon: Icons.person_rounded),
          const SizedBox(width: 14),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(u.name, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 17)),
              const SizedBox(height: 3),
              Text(u.email, style: const TextStyle(color: AppColors.mute, fontSize: 13)),
            ]),
          ),
        ]),
        const SizedBox(height: 16),
        ComicButton(label: 'Sign out', icon: Icons.logout_rounded, style: ComicButtonStyle.ghost, busy: _busy, expand: true, onPressed: _signOut),
      ]),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.icon});

  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 60,
      height: 60,
      decoration: BoxDecoration(
        color: AppColors.yellow,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.line, width: 2.5),
        boxShadow: const [BoxShadow(color: AppColors.line, offset: Offset(4, 4))],
      ),
      child: Icon(icon, size: 32, color: AppColors.line),
    );
  }
}
