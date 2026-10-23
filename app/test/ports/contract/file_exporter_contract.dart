// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runFileExporterContract(FileExporter Function() create) {
  test('FileExporter consumes stream after host confirms save', () async {
    var consumed = false;
    Stream<List<int>> bytes() async* {
      consumed = true;
      yield [1];
      yield [2, 3];
    }

    expect(await create().saveAs('contract.txt', bytes()), isTrue);
    expect(consumed, isTrue);
  });
}
