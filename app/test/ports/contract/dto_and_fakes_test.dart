import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';
import 'package:bubeigongshi/binding/core_binding.dart';
import 'package:bubeigongshi/binding/errors.dart';

import '../../fakes/platform_fakes.dart';

Matcher code(String code) =>
    throwsA(isA<FmlException>().having((e) => e.code, 'code', code));
HttpRequestDto request({
  Uint8List? body,
  Map<String, String> headers = const {},
  Duration timeout = const Duration(seconds: 30),
  File? saveTo,
  int? rangeStart,
}) => HttpRequestDto(
  method: HttpMethod.get,
  url: Uri.parse('http://outside.invalid/'),
  purpose: RequestPurpose.cloudRecognition,
  body: body,
  headers: headers,
  timeout: timeout,
  saveTo: saveTo,
  rangeStart: rangeStart,
);
RuntimeSnapshot snapshot({
  String os = 'windows',
  String osVersion = '10',
  String locale = 'zh-CN',
  int memory = 0,
  double dpi = 1,
  String abi = 'x64',
}) => RuntimeSnapshot(
  os: os,
  osVersion: osVersion,
  locale: locale,
  availMemBytes: memory,
  dpiScale: dpi,
  abi: abi,
  gpuAvailable: false,
);
void main() {
  test('LocalTime rejects all four edges with ArgumentError', () {
    for (final t in [(-1, 0), (24, 0), (0, -1), (0, 60)]) {
      expect(() => LocalTime(t.$1, t.$2), throwsArgumentError);
    }
    expect(LocalTime(0, 0).hour, 0);
    expect(LocalTime(23, 59).minute, 59);
  });
  test('RuntimeSnapshot invalid pure-data inputs', () {
    for (final build in [
      () => snapshot(os: 'linux'),
      () => snapshot(osVersion: ''),
      () => snapshot(locale: 'zh_CN'),
      () => snapshot(memory: -1),
      () => snapshot(dpi: 0),
      () => snapshot(dpi: -1),
      () => snapshot(dpi: double.nan),
      () => snapshot(dpi: double.infinity),
      () => snapshot(abi: 'invalid'),
    ]) {
      expect(build, throwsArgumentError);
    }
    expect(snapshot().availMemBytes, 0);
    expect(snapshot(locale: 'x-private').locale, 'x-private');
    expect(snapshot(locale: 'i-klingon').locale, 'i-klingon');
    expect(snapshot(os: 'android', abi: 'arm64-v8a').os, 'android');
  });
  test('HttpRequest limits, defaults, copies and policy stays outside DTO', () {
    final bytes = Uint8List.fromList([1]);
    final headers = {'Cookie': 'do-not-enforce-here'};
    final r = request(body: bytes, headers: headers);
    bytes[0] = 9;
    headers.clear();
    expect(r.body, [1]);
    expect(r.headers.containsKey('Cookie'), isTrue);
    expect(r.url.scheme, 'http');
    expect(r.consentToken, isNull);
    expect(r.timeout, const Duration(seconds: 30));
    expect(() => r.headers.clear(), throwsUnsupportedError);
    expect(() => r.body![0] = 8, throwsUnsupportedError);
    expect(
      request(body: Uint8List(16 * 1024 * 1024)).body!.length,
      16 * 1024 * 1024,
    );
    expect(
      () => request(body: Uint8List(16 * 1024 * 1024 + 1)),
      throwsArgumentError,
    );
    expect(() => request(timeout: Duration.zero), throwsArgumentError);
    expect(
      () => request(timeout: const Duration(seconds: -1)),
      throwsArgumentError,
    );
    expect(() => request(rangeStart: 0), throwsArgumentError);
    expect(
      () => request(saveTo: File('not-accessed'), rangeStart: -1),
      throwsArgumentError,
    );
    expect(request(saveTo: File('not-accessed'), rangeStart: 0).rangeStart, 0);
  });
  test('HttpResult normalizes and snapshots; rejects invalid values', () {
    final b = Uint8List.fromList([4]);
    final h = {'X-A': 'v'};
    final r = HttpResult(status: 404, headers: h, body: b, receivedBytes: 1);
    b[0] = 9;
    h.clear();
    expect(r.body, [4]);
    expect(r.headers, {'x-a': 'v'});
    expect(() => r.body[0] = 9, throwsUnsupportedError);
    expect(() => r.headers.clear(), throwsUnsupportedError);
    for (final status in [99, 600]) {
      expect(
        () => HttpResult(
          status: status,
          headers: {},
          body: Uint8List(0),
          receivedBytes: 0,
        ),
        throwsArgumentError,
      );
    }
    expect(
      () => HttpResult(
        status: 200,
        headers: {'X': 'a', 'x': 'b'},
        body: Uint8List(0),
        receivedBytes: 0,
      ),
      throwsArgumentError,
    );
    expect(
      () => HttpResult(
        status: 200,
        headers: {},
        body: Uint8List(0),
        receivedBytes: -1,
      ),
      throwsArgumentError,
    );
    expect(
      () =>
          PickedDocument(file: File('none'), displayName: 'x', byteLength: -1),
      throwsArgumentError,
    );
  });
  test('image exact expiry, defensive reads and size ceiling', () async {
    var now = DateTime.utc(2026);
    final bytes = Uint8List.fromList([1, 2]);
    final image = FakeImportedImage(bytes, now: () => now);
    bytes[0] = 9;
    final first = await image.readBytes();
    first[0] = 8;
    expect(await image.readBytes(), [1, 2]);
    expect(image.expiresAt.difference(now), const Duration(hours: 1));
    now = image.expiresAt;
    await expectLater(image.readBytes(), code('PLATFORM_IO'));
    final max = FakeImportedImage(Uint8List(20 * 1024 * 1024));
    expect((await max.readBytes()).length, 20 * 1024 * 1024);
    await expectLater(
      FakeImportedImage(Uint8List(20 * 1024 * 1024 + 1)).readBytes(),
      code('PLATFORM_FILE_TOO_LARGE'),
    );
  });
  test(
    'cancel starts new batch; adapters remain independent; copies survive',
    () async {
      final template = FakeImportedImage(Uint8List.fromList([7]));
      final picker = FakeImagePicker()..images = [template];
      final camera = FakeCameraController()..image = template;
      final clipboard = FakeClipboardAdapter()..image = template;
      final a = (await picker.pick(maxCount: 1)).single;
      final b = await camera.capture();
      final c = await clipboard.readImage();
      final copy = await a.readBytes();
      picker.images = [];
      expect(await picker.pick(maxCount: 1), isEmpty);
      await expectLater(a.readBytes(), code('PLATFORM_IO'));
      expect(await b!.readBytes(), [7]);
      expect(await c!.readBytes(), [7]);
      camera.image = null;
      expect(await camera.capture(), isNull);
      await expectLater(b.readBytes(), code('PLATFORM_IO'));
      clipboard.image = null;
      expect(await clipboard.readImage(), isNull);
      await expectLater(c.readBytes(), code('PLATFORM_IO'));
      expect(copy, [7]);
    },
  );
  test('key invalidation and alias separation', () async {
    final p = FakeSecureKeyValueStore();
    final wrapped = await p.wrap('a', Uint8List.fromList([1]));
    await expectLater(p.unwrap('b', wrapped), code('PLATFORM_KEY_UNAVAILABLE'));
    p.invalidAliases.add('a');
    await expectLater(p.unwrap('a', wrapped), code('PLATFORM_KEY_UNAVAILABLE'));
    await expectLater(
      p.wrap('a', Uint8List(0)),
      code('PLATFORM_KEY_UNAVAILABLE'),
    );
    await expectLater(p.securityLevel('a'), code('PLATFORM_KEY_UNAVAILABLE'));
  });
  test(
    'notification replacement, permission, broadcast, cold tap once',
    () async {
      final p = FakeNotificationScheduler();
      addTearDown(p.dispose);
      p.simulateTap();
      var a = 0;
      var b = 0;
      final sa = p.taps().listen((_) {
        a++;
      });
      await Future<void>.delayed(Duration.zero);
      final sb = p.taps().listen((_) {
        b++;
      });
      await Future<void>.delayed(Duration.zero);
      expect((a, b), (1, 0));
      p.simulateTap();
      await Future<void>.delayed(Duration.zero);
      expect((a, b), (2, 1));
      await sa.cancel();
      await sb.cancel();
      await p.scheduleDailyReminder(LocalTime(8, 1), '3');
      await p.scheduleDailyReminder(LocalTime(9, 2), '4');
      expect(
        (p.reminder!.$1.hour, p.reminder!.$1.minute, p.reminder!.$2),
        (9, 2, '4'),
      );
      await p.cancelAll();
      expect(p.reminder, isNull);
      p.permission = false;
      expect(await p.requestPermission(), isFalse);
      await expectLater(
        p.scheduleDailyReminder(LocalTime(1, 0), '1'),
        code('PLATFORM_PERMISSION_DENIED'),
      );
    },
  );
  test('lifecycle broadcasts ordered events to both observers', () async {
    final p = FakeAppLifecycle();
    addTearDown(p.dispose);
    final a = <LifecycleEvent>[];
    final b = <LifecycleEvent>[];
    final sa = p.events().listen(a.add);
    final sb = p.events().listen(b.add);
    for (final e in LifecycleEvent.values) {
      p.emit(e);
    }
    await Future<void>.delayed(Duration.zero);
    expect(a, LifecycleEvent.values);
    expect(b, a);
    await sa.cancel();
    await sb.cancel();
  });
  test(
    'HTTP fixture miss is StateError, errors and cancellation audit preserved',
    () async {
      final p = FakeHttpTransport();
      final r = request();
      await expectLater(p.send(r), throwsStateError);
      expect(p.requests, [r]);
      p.fixtures[(r.method, r.url)] = 'NET_OFFLINE';
      await expectLater(p.send(r), code('NET_OFFLINE'));
      final token = CancelToken()..cancel();
      await expectLater(p.send(r, cancel: token), throwsA(isA<FfiCancelled>()));
      expect(p.requests, hasLength(3));
      expect(p.cancellations.last, same(token));
      final dir = await Directory.systemTemp.createTemp('core04-http-');
      addTearDown(() => dir.delete(recursive: true));
      final f = File.fromUri(dir.uri.resolve('part'));
      final ranged = request(saveTo: f, rangeStart: 3);
      await expectLater(p.send(ranged), throwsArgumentError);
      await f.writeAsBytes([1]);
      await expectLater(p.send(ranged), throwsArgumentError);
      expect(await f.readAsBytes(), [1]);
    },
  );
  test('export cancellation does not consume stream; success copies and stream errors propagate', () async {
    final p = FakeFileExporter()..cancelled = true;
    var read = false;
    Stream<List<int>> bytes() async* {
      read = true;
      yield [1, 2];
    }

    expect(await p.saveAs('x', bytes()), isFalse);
    expect(read, isFalse);
    expect(p.savedBytes, isNull);
    p.cancelled = false;
    expect(await p.saveAs('x', bytes()), isTrue);
    expect(p.savedBytes, [1, 2]);
    expect(p.suggestedName, 'x');
    await expectLater(
      p.saveAs('x', Stream.error(StateError('fixture'))),
      throwsStateError,
    );
  });
  test('document cancellation and input errors', () async {
    final p = FakeDocumentPicker();
    expect(await p.pick(extensions: ['txt'], maxBytes: 0), isNull);
    for (final extensions in [
      <String>[],
      ['TXT'],
      ['.txt'],
      ['t/xt'],
    ]) {
      await expectLater(
        p.pick(extensions: extensions, maxBytes: 1),
        throwsArgumentError,
      );
    }
    await expectLater(
      p.pick(extensions: ['txt'], maxBytes: -1),
      throwsArgumentError,
    );
  });
}
