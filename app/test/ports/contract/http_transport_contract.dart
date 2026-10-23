// ignore_for_file: public_member_api_docs
import 'package:flutter_test/flutter_test.dart';
import 'package:bubeigongshi/ports/platform_ports.dart';

void runHttpTransportContract(HttpTransport Function() create) {
  test(
    'HttpTransport returns non2xx without throwing, lowercase headers',
    () async {
      final result = await create().send(
        HttpRequestDto(
          method: HttpMethod.get,
          url: Uri.parse(
            const String.fromEnvironment(
              'PORT_CONTRACT_HTTP_URL',
              defaultValue: 'https://example.invalid/core04',
            ),
          ),
          purpose: RequestPurpose.diagnostics,
        ),
      );
      // Scripted endpoint: status503, X-Contract: yes, body bytes 1,2,3.
      expect(result.status, 503);
      expect(result.headers['x-contract'], 'yes');
      expect(result.body, [1, 2, 3]);
      expect(result.receivedBytes, 3);
      expect(result.headers.keys.every((k) => k == k.toLowerCase()), isTrue);
    },
  );
}
