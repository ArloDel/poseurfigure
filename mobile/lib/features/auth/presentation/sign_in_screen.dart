import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/api_client.dart';
import '../../../core/theme/app_colors.dart';
import '../../../shared/widgets/comic_backdrop.dart';
import '../../../shared/widgets/comic_button.dart';
import '../../../shared/widgets/glass_panel.dart';
import '../application/session_controller.dart';

enum SignInMode { signIn, register }

/// One screen for both signing in and creating an account (AUTH-01, AUTH-02).
class SignInScreen extends ConsumerStatefulWidget {
  const SignInScreen({super.key, this.initialMode = SignInMode.signIn});

  final SignInMode initialMode;

  @override
  ConsumerState<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends ConsumerState<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  late SignInMode _mode = widget.initialMode;
  bool _busy = false;
  bool _showPassword = false;
  String? _error;

  bool get _register => _mode == SignInMode.register;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    final session = ref.read(sessionProvider.notifier);
    try {
      final result = _register
          ? await session.register(name: _name.text.trim(), email: _email.text.trim(), password: _password.text)
          : await session.signIn(email: _email.text.trim(), password: _password.text);
      if (!mounted) return;
      final moved = result.claimedAnalyses;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(moved > 0
            ? '${_register ? 'Account created' : 'Signed in'}. $moved ${moved == 1 ? 'analysis' : 'analyses'} moved to your account.'
            : _register
                ? 'Account created'
                : 'Signed in'),
      ));
      context.canPop() ? context.pop() : context.go('/profile');
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
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
                  onPressed: () => context.canPop() ? context.pop() : context.go('/profile'),
                  icon: const Icon(Icons.arrow_back_rounded),
                  tooltip: 'Back',
                ),
              ),
              const SizedBox(height: 16),
              Text(_register ? 'Create your account' : 'Welcome back', style: text.headlineMedium),
              const SizedBox(height: 8),
              Text(
                _register
                    ? 'Keep favorites and history on every device. Analyses you made as a guest come with you.'
                    : 'Sign in to see your favorites and history.',
                style: text.bodyLarge?.copyWith(color: AppColors.mute),
              ),
              const SizedBox(height: 20),
              GlassPanel(
                child: Form(
                  key: _form,
                  child: AutofillGroup(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (_register) ...[
                          TextFormField(
                            controller: _name,
                            decoration: const InputDecoration(labelText: 'Name'),
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.name],
                            validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter your name.' : null,
                          ),
                          const SizedBox(height: 14),
                        ],
                        TextFormField(
                          controller: _email,
                          decoration: const InputDecoration(labelText: 'Email'),
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          autofillHints: const [AutofillHints.email],
                          validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email.' : null,
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _password,
                          decoration: InputDecoration(
                            labelText: 'Password',
                            helperText: _register ? 'At least 8 characters' : null,
                            suffixIcon: IconButton(
                              tooltip: _showPassword ? 'Hide password' : 'Show password',
                              icon: Icon(_showPassword ? Icons.visibility_off_rounded : Icons.visibility_rounded),
                              onPressed: () => setState(() => _showPassword = !_showPassword),
                            ),
                          ),
                          obscureText: !_showPassword,
                          autofillHints: [_register ? AutofillHints.newPassword : AutofillHints.password],
                          onFieldSubmitted: (_) => _submit(),
                          validator: (v) {
                            if (v == null || v.isEmpty) return 'Enter your password.';
                            if (_register && v.length < 8) return 'Use at least 8 characters.';
                            return null;
                          },
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 14),
                          Text(_error!, style: const TextStyle(color: AppColors.red, fontWeight: FontWeight.w700)),
                        ],
                        const SizedBox(height: 18),
                        ComicButton(
                          label: _register ? 'Create account' : 'Sign in',
                          busy: _busy,
                          expand: true,
                          onPressed: _submit,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() {
                            _mode = _register ? SignInMode.signIn : SignInMode.register;
                            _error = null;
                          }),
                  child: Text(_register ? 'I already have an account' : 'Create an account instead'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
