// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runClipboardAdapterContract(ClipboardAdapter Function() create) {
  test('ClipboardAdapter text roundtrip and empty image', () async {
    final p = create();
    await p.writeText('公式 α = β');
    expect(await p.readText(), '公式 α = β');
    await p.writeText('');
    expect(await p.readText(), '');
    // Host fixture starts with no image in the clipboard.
    expect(await p.readImage(), isNull);
  });
}
