import 'package:figurepose/core/utils/dates.dart';
import 'package:figurepose/core/utils/labels.dart';
import 'package:figurepose/features/poses/data/pose_repository.dart';
import 'package:figurepose/features/poses/domain/pose.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  group('Pose.fromJson', () {
    final pose = samplePoses.first;

    test('sorts steps and turns ids into readable titles', () {
      expect(pose.instructions.map((i) => i.step), [1, 2, 3]);
      expect(pose.instructions[1].title, 'Bend the right knee');
      expect(pose.meta, 'Action, medium');
      expect(pose.credit.toString(), '"Ichigo" by Fuyoh!, CC BY 2.0');
    });

    test('groups steps by body region', () {
      final regions = {for (final i in pose.instructions) i.bodyPart: i.region};
      expect(regions, {'torso': BodyRegion.headAndTorso, 'right_knee': BodyRegion.legs, 'right_elbow': BodyRegion.arms});
    });

    test('keeps only constraints flagged as past the usual range', () {
      expect(pose.warnings.single.joint, 'right_knee');
      expect(pose.warnings.single.targetAngle, 120);
      expect(samplePoses.last.warnings, isEmpty);
    });
  });

  test('PoseQuery sends only the filters that are set', () {
    expect(const PoseQuery().toQuery(), isEmpty);
    expect(const PoseQuery(profile: 'mecha_v1', text: '  aim ').toQuery(), {'profile': 'mecha_v1', 'q': 'aim'});
  });

  test('humanize and capitalize', () {
    expect(humanize('open_and_raise'), 'Open and raise');
    expect(capitalize('cinematic'), 'Cinematic');
  });

  test('friendlyDate', () {
    final now = DateTime(2026, 11, 10, 18);
    expect(friendlyDate(DateTime(2026, 11, 10, 9, 5), now: now), 'Today, 09:05');
    expect(friendlyDate(DateTime(2026, 11, 9, 20, 14), now: now), 'Yesterday, 20:14');
    expect(friendlyDate(DateTime(2026, 11, 2), now: now), '2 Nov');
    expect(friendlyDate(DateTime(2025, 12, 31), now: now), '31 Dec 2025');
  });
}
