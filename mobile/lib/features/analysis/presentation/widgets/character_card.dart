import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/comic_button.dart';
import '../../../../shared/widgets/glass_panel.dart';
import '../../domain/analysis.dart';

/// Who the figure is. Pose ideas show that character first, so the user can let the recognition service
/// suggest it (their photo is sent: they agree first) or type it, and correct it any time.
class CharacterCard extends StatelessWidget {
  const CharacterCard({super.key, required this.analysis, required this.busy, required this.onRecognize, required this.onName});

  final Analysis analysis;
  final bool busy;

  /// Called after the user agreed to send their photo.
  final VoidCallback onRecognize;

  /// A typed name, or null to clear it.
  final ValueChanged<String?> onName;

  Future<void> _recognize(BuildContext context) async {
    final agreed = await showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => _ConsentSheet(provider: analysis.recognitionProvider),
    );
    if (agreed == true) onRecognize();
  }

  Future<void> _type(BuildContext context) async {
    final result = await showDialog<_NameResult>(
      context: context,
      builder: (_) => _NameDialog(initial: analysis.characterName ?? ''),
    );
    if (result == null) return;
    onName(result.name);
  }

  @override
  Widget build(BuildContext context) {
    final name = analysis.characterName;
    final known = name != null && name.isNotEmpty;
    final source = switch (analysis.characterSource) {
      'ai' => 'Suggested${analysis.recognitionProvider == null ? '' : ' by ${analysis.recognitionProvider}'}. It can be wrong.',
      'user' => 'Named by you.',
      _ => null,
    };

    return GlassPanel(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(known ? name : 'Who is this figure?', style: const TextStyle(fontFamily: 'BowlbyOne', fontSize: 19)),
        const SizedBox(height: 4),
        Text(
          known
              ? [?analysis.characterFranchise, ?source].join(' · ')
              : 'Name the character to see its poses first.',
          style: const TextStyle(color: AppColors.mute),
        ),
        const SizedBox(height: 12),
        Wrap(spacing: 10, runSpacing: 10, children: [
          if (!known && analysis.recognitionAvailable)
            ComicButton(
              label: 'Recognize it',
              icon: Icons.auto_awesome_rounded,
              busy: busy,
              onPressed: () => _recognize(context),
            ),
          ComicButton(
            label: known ? 'Change' : 'Type the name',
            icon: Icons.edit_rounded,
            style: ComicButtonStyle.ghost,
            onPressed: busy ? null : () => _type(context),
          ),
        ]),
      ]),
    );
  }
}

class _NameResult {
  const _NameResult(this.name);

  final String? name;
}

class _NameDialog extends StatefulWidget {
  const _NameDialog({required this.initial});

  final String initial;

  @override
  State<_NameDialog> createState() => _NameDialogState();
}

class _NameDialogState extends State<_NameDialog> {
  late final _field = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _field.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Which character is it?'),
      content: TextField(
        controller: _field,
        autofocus: true,
        maxLength: 120,
        textCapitalization: TextCapitalization.words,
        decoration: const InputDecoration(labelText: 'Character', hintText: 'e.g. Spider-Man (symbiote suit)'),
        onSubmitted: (v) => Navigator.pop(context, _NameResult(v.trim().isEmpty ? null : v.trim())),
      ),
      actions: [
        if (widget.initial.isNotEmpty)
          TextButton(onPressed: () => Navigator.pop(context, const _NameResult(null)), child: const Text('Clear')),
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
        FilledButton(
          onPressed: () => Navigator.pop(context, _NameResult(_field.text.trim().isEmpty ? null : _field.text.trim())),
          child: const Text('Save'),
        ),
      ],
    );
  }
}

/// Say what is sent and where before the photo leaves the device (PRD 15.1).
class _ConsentSheet extends StatelessWidget {
  const _ConsentSheet({this.provider});

  final String? provider;

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
            const Text('Send your photo to recognize the character?', style: TextStyle(fontFamily: 'BowlbyOne', fontSize: 20)),
            const SizedBox(height: 10),
            for (final line in [
              provider == null
                  ? 'Your photo goes to an image service outside FigurePose.'
                  : 'Your photo goes to $provider, an image service outside FigurePose.',
              "The name is a guess. You can change it if it's wrong.",
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
              Expanded(child: ComicButton(label: 'Not now', style: ComicButtonStyle.ghost, onPressed: () => Navigator.pop(context, false))),
              const SizedBox(width: 10),
              Expanded(child: ComicButton(label: 'Send', onPressed: () => Navigator.pop(context, true))),
            ]),
          ]),
        ),
      ),
    );
  }
}
