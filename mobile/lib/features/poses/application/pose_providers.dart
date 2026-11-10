import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/pose_repository.dart';
import '../domain/pose.dart';

/// Gallery filters: figure type, category and search text.
class PoseQueryController extends Notifier<PoseQuery> {
  @override
  PoseQuery build() => const PoseQuery();

  /// Tapping the selected type again clears it.
  void toggleProfile(String profile) => state = state.withProfile(state.profile == profile ? null : profile);

  void setCategory(String? category) => state = state.withCategory(category);

  void setText(String text) => state = state.withText(text);
}

final poseQueryProvider = NotifierProvider<PoseQueryController, PoseQuery>(PoseQueryController.new);

final posesProvider = FutureProvider<List<Pose>>(
  (ref) => ref.watch(poseRepositoryProvider).list(ref.watch(poseQueryProvider)),
);

final poseDetailProvider = FutureProvider.family<Pose, int>(
  (ref, id) => ref.watch(poseRepositoryProvider).detail(id),
);
