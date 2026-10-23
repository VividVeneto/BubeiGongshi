// ignore_for_file: public_member_api_docs
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runLocalFileStoreContract(LocalFileStore Function() create) {
  test('LocalFileStore private containment, stable staging and adopted files', () async {
    final p = create();
    final staging = await p.root(StoreArea.staging);
    expect(staging.isAbsolute, isTrue);
    expect(await staging.exists(), isTrue);
    final adopted = File.fromUri(staging.uri.resolve('adopted.bin'));
    await adopted.writeAsBytes([8, 9]);
    expect((await p.root(StoreArea.staging)).path, staging.path);
    expect(await adopted.readAsBytes(), [8, 9]);
    await p.excludeFromSystemBackup(staging);
    for (final area in StoreArea.values) {
      expect(await (await p.root(area)).exists(), isTrue);
    }
    expect(await p.freeBytes(), greaterThanOrEqualTo(0));
    final sibling = await staging.parent.parent.createTemp('core04-sibling-');
    final sentinel = File.fromUri(sibling.uri.resolve('keep.txt'));
    await sentinel.writeAsString('unchanged');
    addTearDown(() async {
      await sibling.delete(recursive: true);
    });
    await expectLater(p.excludeFromSystemBackup(sibling), throwsArgumentError);
    final traversal = Directory.fromUri(staging.uri.resolve('../..'));
    await expectLater(
      p.excludeFromSystemBackup(traversal),
      throwsArgumentError,
    );
    final link = Link.fromUri(staging.uri.resolve('external'));
    var supported = true;
    try {
      await link.create(sibling.path);
    } on FileSystemException {
      supported = false;
    }
    if (supported) {
      try {
        await expectLater(
          p.excludeFromSystemBackup(Directory(link.path)),
          throwsArgumentError,
        );
      } finally {
        await link.delete();
      }
    } else {
      // Capability-dependent clause, not a claim that symlink containment ran.
      print('CORE04 symlink case pending: host cannot create symbolic links');
    }
    expect(await sentinel.readAsString(), 'unchanged');
    expect(await adopted.readAsBytes(), [8, 9]);
  });
}
