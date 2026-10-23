import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/composition/composition.dart';
import 'package:bubeigongshi/ports/unsupported/unsupported_ports.dart';

import '../../fakes/composition_fakes.dart';

CompositionContext context({List<Installer> installers = const []}) =>
    CompositionContext(
      core: FakeCoreBinding(),
      ports: portsWith(installers: installers),
      apiBase: Uri.parse('https://api.invalid'),
      packBase: Uri.parse('https://pack.invalid'),
    );

// CORE36 is not implemented here. This consumer fixture demonstrates the
// FutureOr contract and atomic publication, not a production composeApp.
Future<FeatureRegistry> composeFixture(
  CompositionContext ctx,
  List<Installer> installers,
) async {
  for (final install in [...installers, ...ctx.ports.platformInstallers]) {
    await install(ctx);
  }
  return ctx.features;
}

void main() {
  test(
    'FeatureRegistry keyed by explicit type, duplicate and absent errors',
    () {
      final r = FeatureRegistry();
      expect(r.get<String>(), isNull);
      expect(() => r.require<String>(), throwsStateError);
      r.register<String>('value');
      expect(r.get<String>(), 'value');
      expect(r.require<String>(), 'value');
      expect(r.get<Object>(), isNull);
      r.register<Object>(7);
      expect(r.require<Object>(), 7);
      expect(() => r.register<String>('replacement'), throwsStateError);
      expect(r.require<String>(), 'value');
    },
  );
  test(
    'independent hook sequences sorted, duplicate rejected, snapshot immutable',
    () async {
      final c = context();
      final ran = <String>[];
      Future<void> a(FeatureRegistry r) async {
        ran.add('a');
      }

      Future<void> b(FeatureRegistry r) async {
        ran.add('b');
      }

      c.addStartupHook(20, 'b', b);
      c.addStartupHook(10, 'a', a);
      c.addFirstFrameHook(20, 'b', b);
      c.addFirstFrameHook(10, 'a', a);
      expect(c.startupHooks.map((h) => h.$1), [10, 20]);
      expect(c.firstFrameHooks.map((h) => h.$1), [10, 20]);
      expect(() => c.addStartupHook(10, 'other', b), throwsStateError);
      expect(() => c.addFirstFrameHook(10, 'other', b), throwsStateError);
      final snapshot = c.startupHooks;
      expect(() => snapshot.clear(), throwsUnsupportedError);
      c.addStartupHook(30, 'third', b);
      expect(snapshot, hasLength(2));
      expect(ran, isEmpty);
      for (final h in snapshot) {
        await h.$3(c.features);
      }
      expect(ran, ['a', 'b']);
      expect(identical(c.http, c.ports.http), isTrue);
      final replacement = UnsupportedHttpTransport();
      c.http = replacement;
      expect(identical(c.http, replacement), isTrue);
      expect(identical(c.ports.http, replacement), isFalse);
    },
  );
  test(
    'FutureOr A blocks B and platform installers; publishes after all',
    () async {
      final release = Completer<void>();
      final ran = <String>[];
      final platform = <Installer>[
        (c) {
          ran.add('platform');
          expect(c.features.require<int>(), 7);
        },
      ];
      final c = context(installers: platform);
      platform.clear();
      expect(c.ports.platformInstallers, hasLength(1));
      expect(() => c.ports.platformInstallers.clear(), throwsUnsupportedError);
      FeatureRegistry? published;
      final done =
          composeFixture(c, [
            (c) async {
              ran.add('A-start');
              await release.future;
              c.features.register<int>(7);
              ran.add('A-done');
            },
            (c) {
              ran.add('B');
              expect(c.features.require<int>(), 7);
            },
          ]).then((r) {
            published = r;
          });
      await Future<void>.delayed(Duration.zero);
      expect(ran, ['A-start']);
      expect(published, isNull);
      release.complete();
      await done;
      expect(ran, ['A-start', 'A-done', 'B', 'platform']);
      expect(published, same(c.features));
    },
  );
  test(
    'installer failure does not publish or run subsequent installers',
    () async {
      final release = Completer<void>();
      var next = false;
      FeatureRegistry? published;
      final c = context(
        installers: [
          (c) {
            next = true;
          },
        ],
      );
      final done =
          composeFixture(c, [
            (c) async {
              await release.future;
            },
            (c) {
              next = true;
            },
          ]).then((r) {
            published = r;
          });
      final failure = expectLater(done, throwsStateError);
      release.completeError(StateError('fixture'));
      await failure;
      expect(next, isFalse);
      expect(published, isNull);
    },
  );
  test('synchronous installers retain order', () async {
    final ran = <int>[];
    await composeFixture(context(), [
      (c) {
        ran.add(1);
      },
      (c) {
        ran.add(2);
      },
    ]);
    expect(ran, [1, 2]);
  });
}
