// CORE-67 阶段2：真实消费 app/lib/binding/dto/types.g.dart 里由 CORE-100
// 类型图播种出的共享根类型（Uuid、NodePath、Envelope、PullResponse、
// PushItemResult）。
//
// 这份测试不复制任何 DTO 定义，只 import 生成物，因此它同时证明三件事：
// 1. 生成物能被消费者真的 import 并构造，而不是“文件里有这个名字”；
// 2. wire JSON 往返无损（toJson → fromJson 得到相等值）；
// 3. 非法分支按契约抛 [FormatException]，不静默降级成 null 或默认值。
//
// 生成物由 `python tools/ci/gen_dto.py --write` 产出，禁止手改。

import 'package:bubeigongshi/binding/dto/types.g.dart';
import 'package:flutter_test/flutter_test.dart';

/// 合法 Envelope wire JSON：键集合与 contracts 类型图的 16 个字段一致。
Map<String, Object?> envelopeJson({Object? revisionId = 'rev-1'}) {
  return <String, Object?>{
    'aad_version': 1,
    'account_epoch': 7,
    'ciphertext': 'Y2lwaGVy',
    'ciphertext_hash': 'sha256:abc',
    'device_id': 'dev-1',
    'device_seq': 12,
    'entity_id': 'ent-1',
    'entity_type': 'formula',
    'envelope_version': 2,
    'key_version': 3,
    'kind': 'user_data',
    'nonce': 'bm9uY2U=',
    'op_id': 'op-1',
    'purpose': 'study_data',
    'revision_id': revisionId,
    'schema_version': 4,
  };
}

/// 由 [envelopeJson] 构造一个值对象，供 PullResponse 用。
Envelope sampleEnvelope() => Envelope.fromJson(envelopeJson());

/// 合法 Diagnostic wire JSON：键集合与 CORE-02 §诊断模型一致（必填 code/
/// severity/args/needs_confirm，其余可选）。
Map<String, Object?> diagnosticJson() {
  return <String, Object?>{
    'args': <String, Object?>{'actual': 'String', 'expected': 'int'},
    'code': 'E_FORMULA_PARSE',
    'input_range': <Object?>[3, 9],
    'needs_confirm': true,
    'node_path': 'root.children[0]',
    'recovery': 'retry',
    'severity': 'warning',
  };
}

/// 由 [diagnosticJson] 构造一个值对象。
Diagnostic sampleDiagnostic() => Diagnostic.fromJson(diagnosticJson());

/// 消费者侧别名：证明生成的 Diagnostic 可被 `typedef DiagnosticDto = Diagnostic;`
/// 直接消费，也证明生成文件里没有第二个 Diagnostic 类（重复定义会编译失败）。
typedef DiagnosticDto = Diagnostic;

void main() {
  group('共享别名 Uuid 与 NodePath', () {
    test('是 String 别名，可直接当 Map 键并保持相等', () {
      const Uuid id = '8a1f0f6e-0000-4000-8000-000000000001';
      const NodePath path = '/formula/children/0';
      final Map<Uuid, NodePath> table = <Uuid, NodePath>{id: path};
      expect(table['8a1f0f6e-0000-4000-8000-000000000001'], path);
      expect(id, isA<String>());
      expect(path, isA<String>());
    });

    test('可直接填入 Envelope 的 entity_id / revision_id 字段', () {
      const Uuid entityId = 'ent-typed';
      const Uuid revisionId = 'rev-typed';
      const NodePath path = '/formula/root';
      final Map<String, Object?> json = envelopeJson(revisionId: revisionId)
        ..['entity_id'] = entityId;
      final Envelope envelope = Envelope.fromJson(json);
      expect(envelope.entityId, entityId);
      expect(envelope.revisionId, revisionId);
      expect(path, '/formula/root');
    });
  });

  group('Envelope（同步信封）', () {
    test('构造后按 wire 键名编码全部 16 个字段', () {
      final Envelope envelope = sampleEnvelope();
      final Map<String, Object?> wire = envelope.toJson();
      expect(wire.keys.toSet(), <String>{
        'aad_version',
        'account_epoch',
        'ciphertext',
        'ciphertext_hash',
        'device_id',
        'device_seq',
        'entity_id',
        'entity_type',
        'envelope_version',
        'key_version',
        'kind',
        'nonce',
        'op_id',
        'purpose',
        'revision_id',
        'schema_version',
      });
      expect(wire['account_epoch'], 7);
      expect(wire['ciphertext'], 'Y2lwaGVy');
      expect(wire['purpose'], 'study_data');
      expect(envelope.purpose, EnvelopePurpose.studyData);
    });

    test('wire → 值对象 → wire 往返保持相等', () {
      final Map<String, Object?> json = envelopeJson();
      final Envelope envelope = Envelope.fromJson(json);
      expect(envelope.toJson(), json);
      expect(Envelope.fromJson(envelope.toJson()), envelope);
      expect(Envelope.fromJson(envelope.toJson()).hashCode, envelope.hashCode);
    });

    test('revision_id 缺省时解码为 null，编码仍写出 null 键', () {
      final Map<String, Object?> json = envelopeJson()..remove('revision_id');
      final Envelope envelope = Envelope.fromJson(json);
      expect(envelope.revisionId, isNull);
      expect(envelope.toJson().containsKey('revision_id'), isTrue);
      expect(envelope.toJson()['revision_id'], isNull);
    });

    test('未知键被忽略，不进入字段也不回写', () {
      final Map<String, Object?> json = envelopeJson()
        ..['future_field'] = 'ignored';
      final Envelope envelope = Envelope.fromJson(json);
      expect(envelope.toJson().containsKey('future_field'), isFalse);
      expect(envelope, Envelope.fromJson(envelopeJson()));
    });

    test('缺失必填键抛 FormatException', () {
      final Map<String, Object?> json = envelopeJson()..remove('op_id');
      expect(() => Envelope.fromJson(json), throwsFormatException);
    });

    test('字段类型不符抛 FormatException', () {
      final Map<String, Object?> json = envelopeJson()..['aad_version'] = '1';
      expect(() => Envelope.fromJson(json), throwsFormatException);
    });

    test('未知 purpose 判别抛 FormatException', () {
      final Map<String, Object?> json = envelopeJson()
        ..['purpose'] = 'not_a_purpose';
      expect(() => Envelope.fromJson(json), throwsFormatException);
    });
  });

  group('PullResponse（拉取响应）', () {
    test('envelopes 解码为不可变 List<Envelope>', () {
      final PullResponse response = PullResponse.fromJson(<String, Object?>{
        'account_epoch': 7,
        'envelopes': <Object?>[envelopeJson()],
        'has_more': true,
        'next_cursor': 'cursor-2',
      });
      expect(response.envelopes, hasLength(1));
      expect(response.envelopes.single, sampleEnvelope());
      expect(
        () => response.envelopes.add(sampleEnvelope()),
        throwsUnsupportedError,
      );
    });

    test('空 envelopes 与往返保持相等', () {
      final Map<String, Object?> json = <String, Object?>{
        'account_epoch': 0,
        'envelopes': <Object?>[],
        'has_more': false,
        'next_cursor': '',
      };
      final PullResponse response = PullResponse.fromJson(json);
      expect(response.envelopes, isEmpty);
      expect(response.toJson(), json);
      expect(PullResponse.fromJson(response.toJson()), response);
      expect(
        PullResponse.fromJson(response.toJson()).hashCode,
        response.hashCode,
      );
    });

    test('envelopes 元素不是对象时抛 FormatException', () {
      expect(
        () => PullResponse.fromJson(<String, Object?>{
          'account_epoch': 7,
          'envelopes': <Object?>[1],
          'has_more': false,
          'next_cursor': '',
        }),
        throwsFormatException,
      );
    });

    test('缺失 next_cursor 抛 FormatException', () {
      expect(
        () => PullResponse.fromJson(<String, Object?>{
          'account_epoch': 7,
          'envelopes': <Object?>[],
          'has_more': false,
        }),
        throwsFormatException,
      );
    });
  });

  group('PushItemResult（推结果联合）', () {
    test('status=ACK 分派到 PushItemResultACK，编码写回判别常量', () {
      final PushItemResult result = PushItemResult.fromJson(<String, Object?>{
        'status': 'ACK',
        'op_id': 'op-1',
        'server_seq': 42,
      });
      expect(result, isA<PushItemResultACK>());
      final Map<String, Object?> wire = result.toJson() as Map<String, Object?>;
      expect(wire, <String, Object?>{
        'status': 'ACK',
        'op_id': 'op-1',
        'server_seq': 42,
      });
      expect(result, const PushItemResultACK(opId: 'op-1', serverSeq: 42));
    });

    test('status=CONFLICT 分派到 PushItemResultCONFLICT', () {
      final PushItemResult result = PushItemResult.fromJson(<String, Object?>{
        'status': 'CONFLICT',
        'op_id': 'op-2',
      });
      expect(result, isA<PushItemResultCONFLICT>());
      expect(result.toJson(), <String, Object?>{
        'status': 'CONFLICT',
        'op_id': 'op-2',
      });
    });

    test('往返保持相等且判别键不被丢弃', () {
      const PushItemResult ack = PushItemResultACK(opId: 'op-1', serverSeq: 42);
      const PushItemResult conflict = PushItemResultCONFLICT(opId: 'op-2');
      expect(PushItemResult.fromJson(ack.toJson()), ack);
      expect(PushItemResult.fromJson(conflict.toJson()), conflict);
      expect(PushItemResult.fromJson(ack.toJson()).hashCode, ack.hashCode);
      expect(
        (PushItemResult.fromJson(ack.toJson()).toJson()
            as Map<String, Object?>)['status'],
        'ACK',
      );
    });

    test('sealed 分支可按类型穷尽分派', () {
      final List<PushItemResult> results = <PushItemResult>[
        const PushItemResultACK(opId: 'op-1', serverSeq: 1),
        const PushItemResultCONFLICT(opId: 'op-2'),
      ];
      final List<String> labels = <String>[
        for (final PushItemResult result in results)
          switch (result) {
            PushItemResultACK(:final int serverSeq) =>
              'ack:' + serverSeq.toString(),
            PushItemResultCONFLICT(:final String opId) => 'conflict:' + opId,
          },
      ];
      expect(labels, <String>['ack:1', 'conflict:op-2']);
    });

    test('未知 status 抛 FormatException', () {
      expect(
        () => PushItemResult.fromJson(<String, Object?>{
          'status': 'MAYBE',
          'op_id': 'op-1',
        }),
        throwsFormatException,
      );
    });

    test('非对象载荷抛 FormatException', () {
      expect(() => PushItemResult.fromJson('ACK'), throwsFormatException);
      expect(() => PushItemResult.fromJson(null), throwsFormatException);
    });

    test('ACK 缺 server_seq 抛 FormatException', () {
      expect(
        () => PushItemResult.fromJson(<String, Object?>{
          'status': 'ACK',
          'op_id': 'op-1',
        }),
        throwsFormatException,
      );
    });
  });

  group('Diagnostic（诊断模型）', () {
    test('构造后按 wire 键名编码七个字段', () {
      final Diagnostic diagnostic = sampleDiagnostic();
      expect(diagnostic.toJson().keys.toSet(), <String>{
        'args',
        'code',
        'input_range',
        'needs_confirm',
        'node_path',
        'recovery',
        'severity',
      });
      expect(diagnostic.toJson()['severity'], 'warning');
      expect(diagnostic.toJson()['input_range'], <Object?>[3, 9]);
      expect(diagnostic.toJson()['needs_confirm'], isTrue);
    });

    test('wire → 值对象 → wire 往返保持相等', () {
      final Diagnostic first = Diagnostic.fromJson(diagnosticJson());
      final Diagnostic second = Diagnostic.fromJson(first.toJson());
      expect(second, first);
      expect(second.hashCode, first.hashCode);
      expect(second.toJson(), first.toJson());
    });

    test('可选字段缺省为 null 但仍写出 null 键', () {
      final Map<String, Object?> json = diagnosticJson()
        ..remove('input_range')
        ..remove('node_path')
        ..remove('recovery');
      final Diagnostic diagnostic = Diagnostic.fromJson(json);
      expect(diagnostic.inputRange, isNull);
      expect(diagnostic.nodePath, isNull);
      expect(diagnostic.recovery, isNull);
      final Map<String, Object?> wire = diagnostic.toJson();
      expect(wire.containsKey('input_range'), isTrue);
      expect(wire['input_range'], isNull);
    });

    test('args 是不可修改视图且参与按值相等', () {
      final Diagnostic diagnostic = Diagnostic.fromJson(diagnosticJson());
      expect(diagnostic.args, <String, String>{
        'actual': 'String',
        'expected': 'int',
      });
      expect(() => diagnostic.args['x'] = 'y', throwsUnsupportedError);
      final Diagnostic same = Diagnostic.fromJson(
        diagnosticJson()
          ..['args'] = <String, Object?>{'expected': 'int', 'actual': 'String'},
      );
      expect(same, diagnostic);
      expect(same.hashCode, diagnostic.hashCode);
    });

    test('input_range 元素个数不符抛 FormatException', () {
      for (final List<Object?> bad in <List<Object?>>[
        <Object?>[1],
        <Object?>[1, 2, 3],
      ]) {
        expect(
          () => Diagnostic.fromJson(diagnosticJson()..['input_range'] = bad),
          throwsFormatException,
        );
      }
    });

    test('input_range 元素类型不符抛 FormatException', () {
      expect(
        () => Diagnostic.fromJson(
          diagnosticJson()..['input_range'] = <Object?>[1, 'x'],
        ),
        throwsFormatException,
      );
    });

    test('未知 severity wire 取值抛 FormatException', () {
      expect(
        () => Diagnostic.fromJson(diagnosticJson()..['severity'] = 'fatal'),
        throwsFormatException,
      );
    });

    test('缺 needs_confirm 或 args 抛 FormatException', () {
      expect(
        () => Diagnostic.fromJson(diagnosticJson()..remove('needs_confirm')),
        throwsFormatException,
      );
      expect(
        () => Diagnostic.fromJson(diagnosticJson()..remove('args')),
        throwsFormatException,
      );
    });

    test('typedef DiagnosticDto 指向同一个生成类', () {
      final DiagnosticDto dto = DiagnosticDto.fromJson(diagnosticJson());
      expect(dto.code, 'E_FORMULA_PARSE');
      expect(dto, isA<Diagnostic>());
    });
  });
}
