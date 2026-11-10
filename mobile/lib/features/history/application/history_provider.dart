import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../analysis/data/analysis_repository.dart';
import '../../analysis/domain/analysis.dart';
import '../../auth/application/session_controller.dart';

/// Reloads when the session changes: signing in shows the account's history,
/// which now includes what this device analyzed as a guest.
final historyProvider = FutureProvider.autoDispose<List<Analysis>>((ref) async {
  await ref.watch(sessionProvider.future);
  return ref.watch(analysisRepositoryProvider).history();
});
