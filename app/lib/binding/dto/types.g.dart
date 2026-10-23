// GENERATED CODE - DO NOT MODIFY BY HAND.
// generator: CORE-67 v1
// source: manifest=manifest.json; schemas=types.schema.json
// dart format off

/// 枚举 AccountState：wire 取值为 [wire]。
enum AccountState {
  /// wire 取值 uninitialized。
  uninitialized('uninitialized'),
  /// wire 取值 guest_unlocked。
  guestUnlocked('guest_unlocked'),
  /// wire 取值 registered_unlocked。
  registeredUnlocked('registered_unlocked'),
  /// wire 取值 registered_locked。
  registeredLocked('registered_locked'),
  /// wire 取值 upgrading_guest。
  upgradingGuest('upgrading_guest');

  const AccountState(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, AccountState> byWire = <String, AccountState>{
    'uninitialized': AccountState.uninitialized,
    'guest_unlocked': AccountState.guestUnlocked,
    'registered_unlocked': AccountState.registeredUnlocked,
    'registered_locked': AccountState.registeredLocked,
    'upgrading_guest': AccountState.upgradingGuest,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static AccountState fromWire(String wire) {
    final AccountState? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 AccountState wire 取值: $wire');
    }
    return found;
  }
}

/// Assignment：不可变值对象；wire 键见各字段。
final class Assignment {
  /// 由 wire 字段构造。
  const Assignment({
    required this.symbol,
    this.uncertainty,
    required this.unit,
    required this.value,
  });

  /// wire 键 symbol。
  final int symbol;

  /// wire 键 uncertainty。
  final String? uncertainty;

  /// wire 键 unit。
  final String unit;

  /// wire 键 value。
  final String value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Assignment.fromJson(Map<String, Object?> json) {
    return Assignment(
      symbol: readInt(json, 'symbol'),
      uncertainty: readStringOrNull(json, 'uncertainty'),
      unit: readString(json, 'unit'),
      value: readString(json, 'value'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'symbol': symbol,
      'uncertainty': uncertainty,
      'unit': unit,
      'value': value,
    };
  }

  @override
  String toString() {
    return 'Assignment(symbol: $symbol, uncertainty: $uncertainty, unit: $unit, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Assignment &&
        dtoEquals(symbol, other.symbol) &&
        dtoEquals(uncertainty, other.uncertainty) &&
        dtoEquals(unit, other.unit) &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(symbol),
    dtoHash(uncertainty),
    dtoHash(unit),
    dtoHash(value),
  ]);
}

/// CalcResult：不可变值对象；wire 键见各字段。
final class CalcResult {
  /// 由 wire 字段构造。
  const CalcResult({
    required this.branches,
    required this.constantsUsed,
    required this.diagnostics,
    required this.method,
    this.residual,
    required this.sigFigs,
    this.uncertaintyInterval,
    required this.unit,
    required this.value,
  });

  /// wire 键 branches。
  final List<FormulaNode> branches;

  /// wire 键 constants_used。
  final List<ConstantValue> constantsUsed;

  /// wire 键 diagnostics。
  final List<Diagnostic> diagnostics;

  /// wire 键 method。
  final CalcResultMethod method;

  /// wire 键 residual。
  final String? residual;

  /// wire 键 sig_figs。
  final int sigFigs;

  /// wire 键 uncertainty_interval。
  final (String, String)? uncertaintyInterval;

  /// wire 键 unit。
  final String unit;

  /// wire 键 value。
  final String value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcResult.fromJson(Map<String, Object?> json) {
    return CalcResult(
      branches: readList(json, 'branches', (Object? value) => FormulaNode.fromJson(value)),
      constantsUsed: readList(json, 'constants_used', (Object? value) => ConstantValue.fromJson(asObject(value))),
      diagnostics: readList(json, 'diagnostics', (Object? value) => Diagnostic.fromJson(asObject(value))),
      method: readValue(json, 'method', CalcResultMethod.fromJson),
      residual: readStringOrNull(json, 'residual'),
      sigFigs: readInt(json, 'sig_figs'),
      uncertaintyInterval: readValueOrNull(json, 'uncertainty_interval', readCalcResultUncertaintyIntervalValue),
      unit: readString(json, 'unit'),
      value: readString(json, 'value'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'branches': encodeList(branches, (FormulaNode item) => item.toJson()),
      'constants_used': encodeList(constantsUsed, (ConstantValue item) => item.toJson()),
      'diagnostics': encodeList(diagnostics, (Diagnostic item) => item.toJson()),
      'method': method.toJson(),
      'residual': residual,
      'sig_figs': sigFigs,
      'uncertainty_interval': uncertaintyInterval == null ? null : encodeCalcResultUncertaintyInterval(uncertaintyInterval!),
      'unit': unit,
      'value': value,
    };
  }

  @override
  String toString() {
    return 'CalcResult(branches: $branches, constantsUsed: $constantsUsed, diagnostics: $diagnostics, method: $method, residual: $residual, sigFigs: $sigFigs, uncertaintyInterval: $uncertaintyInterval, unit: $unit, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcResult &&
        dtoEquals(branches, other.branches) &&
        dtoEquals(constantsUsed, other.constantsUsed) &&
        dtoEquals(diagnostics, other.diagnostics) &&
        dtoEquals(method, other.method) &&
        dtoEquals(residual, other.residual) &&
        dtoEquals(sigFigs, other.sigFigs) &&
        dtoEquals(uncertaintyInterval, other.uncertaintyInterval) &&
        dtoEquals(unit, other.unit) &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(branches),
    dtoHash(constantsUsed),
    dtoHash(diagnostics),
    dtoHash(method),
    dtoHash(residual),
    dtoHash(sigFigs),
    dtoHash(uncertaintyInterval),
    dtoHash(unit),
    dtoHash(value),
  ]);
}

/// CalcResultMethod：sealed 联合，按 wire 判别分派到分支类。
sealed class CalcResultMethod {
  /// 常量构造。
  const CalcResultMethod();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory CalcResultMethod.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'direct':
          return const CalcResultMethodDirect();
        case 'symbolic':
          return const CalcResultMethodSymbolic();
        default:
          throw FormatException('未知 CalcResultMethod 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('numeric')) {
        return CalcResultMethodNumeric.fromJson(json);
      }
    }
    throw FormatException('非法 CalcResultMethod 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// CalcResultMethod 的标量分支：wire 取值 'direct'。
final class CalcResultMethodDirect extends CalcResultMethod {
  /// 常量分支。
  const CalcResultMethodDirect();

  @override
  Object? toJson() => 'direct';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is CalcResultMethodDirect;
  }

  @override
  int get hashCode => 0;
}

/// CalcResultMethod Numeric：不可变值对象；wire 键见各字段。
final class CalcResultMethodNumeric extends CalcResultMethod {
  /// 由 wire 字段构造。
  const CalcResultMethodNumeric({
    required this.numeric,
  });

  /// wire 键 numeric。
  final CalcResultMethodNumericNumeric numeric;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcResultMethodNumeric.fromJson(Map<String, Object?> json) {
    return CalcResultMethodNumeric(
      numeric: readObject(json, 'numeric', CalcResultMethodNumericNumeric.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'numeric': numeric.toJson(),
    };
  }

  @override
  String toString() {
    return 'CalcResultMethodNumeric(numeric: $numeric)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcResultMethodNumeric &&
        dtoEquals(numeric, other.numeric);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(numeric),
  ]);
}

/// CalcResultMethod 的标量分支：wire 取值 'symbolic'。
final class CalcResultMethodSymbolic extends CalcResultMethod {
  /// 常量分支。
  const CalcResultMethodSymbolic();

  @override
  Object? toJson() => 'symbolic';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is CalcResultMethodSymbolic;
  }

  @override
  int get hashCode => 0;
}

/// CalcResultMethodNumericNumeric：不可变值对象；wire 键见各字段。
final class CalcResultMethodNumericNumeric {
  /// 由 wire 字段构造。
  const CalcResultMethodNumericNumeric({
    required this.lower,
    required this.upper,
  });

  /// wire 键 lower。
  final String lower;

  /// wire 键 upper。
  final String upper;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalcResultMethodNumericNumeric.fromJson(Map<String, Object?> json) {
    return CalcResultMethodNumericNumeric(
      lower: readString(json, 'lower'),
      upper: readString(json, 'upper'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'lower': lower,
      'upper': upper,
    };
  }

  @override
  String toString() {
    return 'CalcResultMethodNumericNumeric(lower: $lower, upper: $upper)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalcResultMethodNumericNumeric &&
        dtoEquals(lower, other.lower) &&
        dtoEquals(upper, other.upper);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(lower),
    dtoHash(upper),
  ]);
}

/// CalcResultUncertaintyInterval：定长元组；wire 为 JSON 数组。
typedef CalcResultUncertaintyInterval = (String, String);

/// 严格解码 CalcResultUncertaintyInterval：元素个数或类型不符抛 [FormatException]。
(String, String) readCalcResultUncertaintyIntervalValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 CalcResultUncertaintyInterval 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    asString(items[1]),
  );
}

/// 编码 CalcResultUncertaintyInterval。
List<Object?> encodeCalcResultUncertaintyInterval((String, String) value) {
  final (String item0, String item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// CalculationPlan：不可变值对象；wire 键见各字段。
final class CalculationPlan {
  /// 由 wire 字段构造。
  const CalculationPlan({
    required this.steps,
  });

  /// wire 键 steps。
  final List<CalculationPlanSteps> steps;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalculationPlan.fromJson(Map<String, Object?> json) {
    return CalculationPlan(
      steps: readList(json, 'steps', (Object? value) => CalculationPlanSteps.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'steps': encodeList(steps, (CalculationPlanSteps item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'CalculationPlan(steps: $steps)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalculationPlan &&
        dtoEquals(steps, other.steps);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(steps),
  ]);
}

/// CalculationPlanSteps：不可变值对象；wire 键见各字段。
final class CalculationPlanSteps {
  /// 由 wire 字段构造。
  const CalculationPlanSteps({
    this.feeds,
    required this.inputs,
    required this.output,
    required this.revision,
  });

  /// wire 键 feeds。
  final int? feeds;

  /// wire 键 inputs。
  final List<Assignment> inputs;

  /// wire 键 output。
  final int output;

  /// wire 键 revision。
  final String revision;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CalculationPlanSteps.fromJson(Map<String, Object?> json) {
    return CalculationPlanSteps(
      feeds: readIntOrNull(json, 'feeds'),
      inputs: readList(json, 'inputs', (Object? value) => Assignment.fromJson(asObject(value))),
      output: readInt(json, 'output'),
      revision: readString(json, 'revision'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'feeds': feeds,
      'inputs': encodeList(inputs, (Assignment item) => item.toJson()),
      'output': output,
      'revision': revision,
    };
  }

  @override
  String toString() {
    return 'CalculationPlanSteps(feeds: $feeds, inputs: $inputs, output: $output, revision: $revision)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CalculationPlanSteps &&
        dtoEquals(feeds, other.feeds) &&
        dtoEquals(inputs, other.inputs) &&
        dtoEquals(output, other.output) &&
        dtoEquals(revision, other.revision);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(feeds),
    dtoHash(inputs),
    dtoHash(output),
    dtoHash(revision),
  ]);
}

/// Candidate：不可变值对象；wire 键见各字段。
final class Candidate {
  /// 由 wire 字段构造。
  const Candidate({
    required this.output,
    required this.outputType,
    required this.revision,
    required this.subject,
  });

  /// wire 键 output。
  final int output;

  /// wire 键 output_type。
  final TypeExpr outputType;

  /// wire 键 revision。
  final String revision;

  /// wire 键 subject。
  final String subject;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Candidate.fromJson(Map<String, Object?> json) {
    return Candidate(
      output: readInt(json, 'output'),
      outputType: readObject(json, 'output_type', TypeExpr.fromJson),
      revision: readString(json, 'revision'),
      subject: readString(json, 'subject'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'output': output,
      'output_type': outputType.toJson(),
      'revision': revision,
      'subject': subject,
    };
  }

  @override
  String toString() {
    return 'Candidate(output: $output, outputType: $outputType, revision: $revision, subject: $subject)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Candidate &&
        dtoEquals(output, other.output) &&
        dtoEquals(outputType, other.outputType) &&
        dtoEquals(revision, other.revision) &&
        dtoEquals(subject, other.subject);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(output),
    dtoHash(outputType),
    dtoHash(revision),
    dtoHash(subject),
  ]);
}

/// CheckResponse：不可变值对象；wire 键见各字段。
final class CheckResponse {
  /// 由 wire 字段构造。
  const CheckResponse({
    required this.ast,
    required this.checkResult,
    required this.sourceMap,
    required this.symbols,
  });

  /// wire 键 ast。
  final FormulaNode ast;

  /// wire 键 check_result。
  final CheckResult checkResult;

  /// wire 键 source_map。
  final SourceMap sourceMap;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CheckResponse.fromJson(Map<String, Object?> json) {
    return CheckResponse(
      ast: readValue(json, 'ast', FormulaNode.fromJson),
      checkResult: readObject(json, 'check_result', CheckResult.fromJson),
      sourceMap: readList(json, 'source_map', (Object? value) => SourceSpan.fromJson(asObject(value))),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ast': ast.toJson(),
      'check_result': checkResult.toJson(),
      'source_map': encodeList(sourceMap, (SourceSpan item) => item.toJson()),
      'symbols': symbols.toJson(),
    };
  }

  @override
  String toString() {
    return 'CheckResponse(ast: $ast, checkResult: $checkResult, sourceMap: $sourceMap, symbols: $symbols)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CheckResponse &&
        dtoEquals(ast, other.ast) &&
        dtoEquals(checkResult, other.checkResult) &&
        dtoEquals(sourceMap, other.sourceMap) &&
        dtoEquals(symbols, other.symbols);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ast),
    dtoHash(checkResult),
    dtoHash(sourceMap),
    dtoHash(symbols),
  ]);
}

/// CheckResult：不可变值对象；wire 键见各字段。
final class CheckResult {
  /// 由 wire 字段构造。
  const CheckResult({
    required this.diagnostics,
    this.typed,
    required this.validation,
  });

  /// wire 键 diagnostics。
  final List<Diagnostic> diagnostics;

  /// wire 键 typed。
  final TypedAst? typed;

  /// wire 键 validation。
  final Validation validation;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory CheckResult.fromJson(Map<String, Object?> json) {
    return CheckResult(
      diagnostics: readList(json, 'diagnostics', (Object? value) => Diagnostic.fromJson(asObject(value))),
      typed: readObjectOrNull(json, 'typed', TypedAst.fromJson),
      validation: readValue(json, 'validation', Validation.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'diagnostics': encodeList(diagnostics, (Diagnostic item) => item.toJson()),
      'typed': typed?.toJson(),
      'validation': validation.toJson(),
    };
  }

  @override
  String toString() {
    return 'CheckResult(diagnostics: $diagnostics, typed: $typed, validation: $validation)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is CheckResult &&
        dtoEquals(diagnostics, other.diagnostics) &&
        dtoEquals(typed, other.typed) &&
        dtoEquals(validation, other.validation);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(diagnostics),
    dtoHash(typed),
    dtoHash(validation),
  ]);
}

/// ConfirmRecord：不可变值对象；wire 键见各字段。
final class ConfirmRecord {
  /// 由 wire 字段构造。
  const ConfirmRecord({
    required this.confirmedAtMs,
    required this.fromKind,
    required this.reasonKey,
    required this.toKind,
  });

  /// wire 键 confirmed_at_ms。
  final int confirmedAtMs;

  /// wire 键 from_kind。
  final String fromKind;

  /// wire 键 reason_key。
  final String reasonKey;

  /// wire 键 to_kind。
  final String toKind;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ConfirmRecord.fromJson(Map<String, Object?> json) {
    return ConfirmRecord(
      confirmedAtMs: readInt(json, 'confirmed_at_ms'),
      fromKind: readString(json, 'from_kind'),
      reasonKey: readString(json, 'reason_key'),
      toKind: readString(json, 'to_kind'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'confirmed_at_ms': confirmedAtMs,
      'from_kind': fromKind,
      'reason_key': reasonKey,
      'to_kind': toKind,
    };
  }

  @override
  String toString() {
    return 'ConfirmRecord(confirmedAtMs: $confirmedAtMs, fromKind: $fromKind, reasonKey: $reasonKey, toKind: $toKind)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ConfirmRecord &&
        dtoEquals(confirmedAtMs, other.confirmedAtMs) &&
        dtoEquals(fromKind, other.fromKind) &&
        dtoEquals(reasonKey, other.reasonKey) &&
        dtoEquals(toKind, other.toKind);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(confirmedAtMs),
    dtoHash(fromKind),
    dtoHash(reasonKey),
    dtoHash(toKind),
  ]);
}

/// ConstantValue：不可变值对象；wire 键见各字段。
final class ConstantValue {
  /// 由 wire 字段构造。
  const ConstantValue({
    required this.key,
    required this.setVersion,
    required this.source,
    required this.sourceRef,
    required this.unit,
    required this.value,
  });

  /// wire 键 key。
  final String key;

  /// wire 键 set_version。
  final String setVersion;

  /// wire 键 source。
  final ConstantValueSource source;

  /// wire 键 source_ref。
  final String sourceRef;

  /// wire 键 unit。
  final String unit;

  /// wire 键 value。
  final String value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ConstantValue.fromJson(Map<String, Object?> json) {
    return ConstantValue(
      key: readString(json, 'key'),
      setVersion: readString(json, 'set_version'),
      source: readEnum(json, 'source', ConstantValueSource.fromWire),
      sourceRef: readString(json, 'source_ref'),
      unit: readString(json, 'unit'),
      value: readString(json, 'value'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'key': key,
      'set_version': setVersion,
      'source': source.wire,
      'source_ref': sourceRef,
      'unit': unit,
      'value': value,
    };
  }

  @override
  String toString() {
    return 'ConstantValue(key: $key, setVersion: $setVersion, source: $source, sourceRef: $sourceRef, unit: $unit, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ConstantValue &&
        dtoEquals(key, other.key) &&
        dtoEquals(setVersion, other.setVersion) &&
        dtoEquals(source, other.source) &&
        dtoEquals(sourceRef, other.sourceRef) &&
        dtoEquals(unit, other.unit) &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(key),
    dtoHash(setVersion),
    dtoHash(source),
    dtoHash(sourceRef),
    dtoHash(unit),
    dtoHash(value),
  ]);
}

/// 枚举 ConstantValueSource：wire 取值为 [wire]。
enum ConstantValueSource {
  /// wire 取值 exact。
  exact('exact'),
  /// wire 取值 textbook。
  textbook('textbook'),
  /// wire 取值 given。
  given('given');

  const ConstantValueSource(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, ConstantValueSource> byWire = <String, ConstantValueSource>{
    'exact': ConstantValueSource.exact,
    'textbook': ConstantValueSource.textbook,
    'given': ConstantValueSource.given,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static ConstantValueSource fromWire(String wire) {
    final ConstantValueSource? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 ConstantValueSource wire 取值: $wire');
    }
    return found;
  }
}

/// Derivation：不可变值对象；wire 键见各字段。
final class Derivation {
  /// 由 wire 字段构造。
  const Derivation({
    this.branch,
    required this.conditions,
    this.crossKindConfirmation,
    required this.depth,
    required this.sourceRevisions,
    required this.targetSlot,
    required this.varMap,
  });

  /// wire 键 branch。
  final int? branch;

  /// wire 键 conditions。
  final List<FormulaNode> conditions;

  /// wire 键 cross_kind_confirmation。
  final ConfirmRecord? crossKindConfirmation;

  /// wire 键 depth。
  final int depth;

  /// wire 键 source_revisions。
  final List<String> sourceRevisions;

  /// wire 键 target_slot。
  final String targetSlot;

  /// wire 键 var_map。
  final List<(int, int)> varMap;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Derivation.fromJson(Map<String, Object?> json) {
    return Derivation(
      branch: readIntOrNull(json, 'branch'),
      conditions: readList(json, 'conditions', (Object? value) => FormulaNode.fromJson(value)),
      crossKindConfirmation: readObjectOrNull(json, 'cross_kind_confirmation', ConfirmRecord.fromJson),
      depth: readInt(json, 'depth'),
      sourceRevisions: readList(json, 'source_revisions', (Object? value) => asString(value)),
      targetSlot: readString(json, 'target_slot'),
      varMap: readList(json, 'var_map', (Object? value) => readDerivationVarMapValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'branch': branch,
      'conditions': encodeList(conditions, (FormulaNode item) => item.toJson()),
      'cross_kind_confirmation': crossKindConfirmation?.toJson(),
      'depth': depth,
      'source_revisions': sourceRevisions,
      'target_slot': targetSlot,
      'var_map': encodeList(varMap, encodeDerivationVarMap),
    };
  }

  @override
  String toString() {
    return 'Derivation(branch: $branch, conditions: $conditions, crossKindConfirmation: $crossKindConfirmation, depth: $depth, sourceRevisions: $sourceRevisions, targetSlot: $targetSlot, varMap: $varMap)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Derivation &&
        dtoEquals(branch, other.branch) &&
        dtoEquals(conditions, other.conditions) &&
        dtoEquals(crossKindConfirmation, other.crossKindConfirmation) &&
        dtoEquals(depth, other.depth) &&
        dtoEquals(sourceRevisions, other.sourceRevisions) &&
        dtoEquals(targetSlot, other.targetSlot) &&
        dtoEquals(varMap, other.varMap);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(branch),
    dtoHash(conditions),
    dtoHash(crossKindConfirmation),
    dtoHash(depth),
    dtoHash(sourceRevisions),
    dtoHash(targetSlot),
    dtoHash(varMap),
  ]);
}

/// DerivationVarMap：定长元组；wire 为 JSON 数组。
typedef DerivationVarMap = (int, int);

/// 严格解码 DerivationVarMap：元素个数或类型不符抛 [FormatException]。
(int, int) readDerivationVarMapValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DerivationVarMap 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asInt(items[0]),
    asInt(items[1]),
  );
}

/// 编码 DerivationVarMap。
List<Object?> encodeDerivationVarMap((int, int) value) {
  final (int item0, int item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// Diagnostic：不可变值对象；wire 键见各字段。
final class Diagnostic {
  /// 由 wire 字段构造。
  const Diagnostic({
    required this.args,
    required this.code,
    this.inputRange,
    required this.needsConfirm,
    this.nodePath,
    this.recovery,
    required this.severity,
  });

  /// wire 键 args。
  final Map<String, String> args;

  /// wire 键 code。
  final String code;

  /// wire 键 input_range。
  final (int, int)? inputRange;

  /// wire 键 needs_confirm。
  final bool needsConfirm;

  /// wire 键 node_path。
  final String? nodePath;

  /// wire 键 recovery。
  final String? recovery;

  /// wire 键 severity。
  final DiagnosticSeverity severity;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Diagnostic.fromJson(Map<String, Object?> json) {
    return Diagnostic(
      args: readStringMap(json, 'args'),
      code: readString(json, 'code'),
      inputRange: readValueOrNull(json, 'input_range', readDiagnosticInputRangeValue),
      needsConfirm: readBool(json, 'needs_confirm'),
      nodePath: readStringOrNull(json, 'node_path'),
      recovery: readStringOrNull(json, 'recovery'),
      severity: readEnum(json, 'severity', DiagnosticSeverity.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'args': args,
      'code': code,
      'input_range': inputRange == null ? null : encodeDiagnosticInputRange(inputRange!),
      'needs_confirm': needsConfirm,
      'node_path': nodePath,
      'recovery': recovery,
      'severity': severity.wire,
    };
  }

  @override
  String toString() {
    return 'Diagnostic(args: $args, code: $code, inputRange: $inputRange, needsConfirm: $needsConfirm, nodePath: $nodePath, recovery: $recovery, severity: $severity)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Diagnostic &&
        dtoEquals(args, other.args) &&
        dtoEquals(code, other.code) &&
        dtoEquals(inputRange, other.inputRange) &&
        dtoEquals(needsConfirm, other.needsConfirm) &&
        dtoEquals(nodePath, other.nodePath) &&
        dtoEquals(recovery, other.recovery) &&
        dtoEquals(severity, other.severity);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(args),
    dtoHash(code),
    dtoHash(inputRange),
    dtoHash(needsConfirm),
    dtoHash(nodePath),
    dtoHash(recovery),
    dtoHash(severity),
  ]);
}

/// DiagnosticInputRange：定长元组；wire 为 JSON 数组。
typedef DiagnosticInputRange = (int, int);

/// 严格解码 DiagnosticInputRange：元素个数或类型不符抛 [FormatException]。
(int, int) readDiagnosticInputRangeValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DiagnosticInputRange 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asInt(items[0]),
    asInt(items[1]),
  );
}

/// 编码 DiagnosticInputRange。
List<Object?> encodeDiagnosticInputRange((int, int) value) {
  final (int item0, int item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// 枚举 DiagnosticSeverity：wire 取值为 [wire]。
enum DiagnosticSeverity {
  /// wire 取值 error。
  error('error'),
  /// wire 取值 warning。
  warning('warning'),
  /// wire 取值 info。
  info('info');

  const DiagnosticSeverity(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, DiagnosticSeverity> byWire = <String, DiagnosticSeverity>{
    'error': DiagnosticSeverity.error,
    'warning': DiagnosticSeverity.warning,
    'info': DiagnosticSeverity.info,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static DiagnosticSeverity fromWire(String wire) {
    final DiagnosticSeverity? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 DiagnosticSeverity wire 取值: $wire');
    }
    return found;
  }
}

/// DimExpr：不可变值对象；wire 键见各字段。
final class DimExpr {
  /// 由 wire 字段构造。
  const DimExpr({
    required this.baseValueValue,
    required this.vars,
  });

  /// wire 键 base。
  final DimensionFull baseValueValue;

  /// wire 键 vars。
  final List<(int, Rational)> vars;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DimExpr.fromJson(Map<String, Object?> json) {
    return DimExpr(
      baseValueValue: readObject(json, 'base', DimensionFull.fromJson),
      vars: readList(json, 'vars', (Object? value) => readDimExprVarsValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'base': baseValueValue.toJson(),
      'vars': encodeList(vars, encodeDimExprVars),
    };
  }

  @override
  String toString() {
    return 'DimExpr(baseValueValue: $baseValueValue, vars: $vars)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DimExpr &&
        dtoEquals(baseValueValue, other.baseValueValue) &&
        dtoEquals(vars, other.vars);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(baseValueValue),
    dtoHash(vars),
  ]);
}

/// DimExprVars：定长元组；wire 为 JSON 数组。
typedef DimExprVars = (int, Rational);

/// 严格解码 DimExprVars：元素个数或类型不符抛 [FormatException]。
(int, Rational) readDimExprVarsValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DimExprVars 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asInt(items[0]),
    Rational.fromJson(asObject(items[1])),
  );
}

/// 编码 DimExprVars。
List<Object?> encodeDimExprVars((int, Rational) value) {
  final (int item0, Rational item1) = value;
  return <Object?>[
    item0,
    item1.toJson(),
  ];
}

/// DimensionFull：不可变值对象；wire 键见各字段。
final class DimensionFull {
  /// 由 wire 字段构造。
  const DimensionFull({
    required this.baseValueValue,
    required this.pseudo,
  });

  /// wire 键 base。
  final DimensionFullBase baseValueValue;

  /// wire 键 pseudo。
  final List<(DimensionFullPseudoItem0, Rational)> pseudo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DimensionFull.fromJson(Map<String, Object?> json) {
    return DimensionFull(
      baseValueValue: readObject(json, 'base', DimensionFullBase.fromJson),
      pseudo: readList(json, 'pseudo', (Object? value) => readDimensionFullPseudoValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'base': baseValueValue.toJson(),
      'pseudo': encodeList(pseudo, encodeDimensionFullPseudo),
    };
  }

  @override
  String toString() {
    return 'DimensionFull(baseValueValue: $baseValueValue, pseudo: $pseudo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DimensionFull &&
        dtoEquals(baseValueValue, other.baseValueValue) &&
        dtoEquals(pseudo, other.pseudo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(baseValueValue),
    dtoHash(pseudo),
  ]);
}

/// DimensionFullBase：不可变值对象；wire 键见各字段。
final class DimensionFullBase {
  /// 由 wire 字段构造。
  const DimensionFullBase({
    required this.exps,
  });

  /// wire 键 exps。
  final List<Rational> exps;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DimensionFullBase.fromJson(Map<String, Object?> json) {
    return DimensionFullBase(
      exps: readList(json, 'exps', (Object? value) => Rational.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'exps': encodeList(exps, (Rational item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'DimensionFullBase(exps: $exps)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DimensionFullBase &&
        dtoEquals(exps, other.exps);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(exps),
  ]);
}

/// DimensionFullPseudo：定长元组；wire 为 JSON 数组。
typedef DimensionFullPseudo = (DimensionFullPseudoItem0, Rational);

/// 严格解码 DimensionFullPseudo：元素个数或类型不符抛 [FormatException]。
(DimensionFullPseudoItem0, Rational) readDimensionFullPseudoValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DimensionFullPseudo 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    DimensionFullPseudoItem0.fromWire(asString(items[0])),
    Rational.fromJson(asObject(items[1])),
  );
}

/// 编码 DimensionFullPseudo。
List<Object?> encodeDimensionFullPseudo((DimensionFullPseudoItem0, Rational) value) {
  final (DimensionFullPseudoItem0 item0, Rational item1) = value;
  return <Object?>[
    item0.wire,
    item1.toJson(),
  ];
}

/// 枚举 DimensionFullPseudoItem0：wire 取值为 [wire]。
enum DimensionFullPseudoItem0 {
  /// wire 取值 angle。
  angle('angle'),
  /// wire 取值 count。
  count('count');

  const DimensionFullPseudoItem0(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, DimensionFullPseudoItem0> byWire = <String, DimensionFullPseudoItem0>{
    'angle': DimensionFullPseudoItem0.angle,
    'count': DimensionFullPseudoItem0.count,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static DimensionFullPseudoItem0 fromWire(String wire) {
    final DimensionFullPseudoItem0? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 DimensionFullPseudoItem0 wire 取值: $wire');
    }
    return found;
  }
}

/// DisplayList：不可变值对象；wire 键见各字段。
final class DisplayList {
  /// 由 wire 字段构造。
  const DisplayList({
    required this.baseline,
    required this.bounds,
    required this.fontIds,
    required this.hitRegions,
    required this.layoutVersion,
    required this.nodeBounds,
    required this.nodes,
    required this.semanticText,
  });

  /// wire 键 baseline。
  final double baseline;

  /// wire 键 bounds。
  final Rect bounds;

  /// wire 键 font_ids。
  final List<String> fontIds;

  /// wire 键 hit_regions。
  final List<(String, Rect)> hitRegions;

  /// wire 键 layout_version。
  final int layoutVersion;

  /// wire 键 node_bounds。
  final List<(String, Rect)> nodeBounds;

  /// wire 键 nodes。
  final List<DrawCmd> nodes;

  /// wire 键 semantic_text。
  final String semanticText;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DisplayList.fromJson(Map<String, Object?> json) {
    return DisplayList(
      baseline: readDouble(json, 'baseline'),
      bounds: readObject(json, 'bounds', Rect.fromJson),
      fontIds: readList(json, 'font_ids', (Object? value) => asString(value)),
      hitRegions: readList(json, 'hit_regions', (Object? value) => readDisplayListHitRegionsValue(value)),
      layoutVersion: readInt(json, 'layout_version'),
      nodeBounds: readList(json, 'node_bounds', (Object? value) => readDisplayListNodeBoundsValue(value)),
      nodes: readList(json, 'nodes', (Object? value) => DrawCmd.fromJson(value)),
      semanticText: readString(json, 'semantic_text'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'baseline': baseline,
      'bounds': bounds.toJson(),
      'font_ids': fontIds,
      'hit_regions': encodeList(hitRegions, encodeDisplayListHitRegions),
      'layout_version': layoutVersion,
      'node_bounds': encodeList(nodeBounds, encodeDisplayListNodeBounds),
      'nodes': encodeList(nodes, (DrawCmd item) => item.toJson()),
      'semantic_text': semanticText,
    };
  }

  @override
  String toString() {
    return 'DisplayList(baseline: $baseline, bounds: $bounds, fontIds: $fontIds, hitRegions: $hitRegions, layoutVersion: $layoutVersion, nodeBounds: $nodeBounds, nodes: $nodes, semanticText: $semanticText)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DisplayList &&
        dtoEquals(baseline, other.baseline) &&
        dtoEquals(bounds, other.bounds) &&
        dtoEquals(fontIds, other.fontIds) &&
        dtoEquals(hitRegions, other.hitRegions) &&
        dtoEquals(layoutVersion, other.layoutVersion) &&
        dtoEquals(nodeBounds, other.nodeBounds) &&
        dtoEquals(nodes, other.nodes) &&
        dtoEquals(semanticText, other.semanticText);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(baseline),
    dtoHash(bounds),
    dtoHash(fontIds),
    dtoHash(hitRegions),
    dtoHash(layoutVersion),
    dtoHash(nodeBounds),
    dtoHash(nodes),
    dtoHash(semanticText),
  ]);
}

/// DisplayListHitRegions：定长元组；wire 为 JSON 数组。
typedef DisplayListHitRegions = (String, Rect);

/// 严格解码 DisplayListHitRegions：元素个数或类型不符抛 [FormatException]。
(String, Rect) readDisplayListHitRegionsValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DisplayListHitRegions 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    Rect.fromJson(asObject(items[1])),
  );
}

/// 编码 DisplayListHitRegions。
List<Object?> encodeDisplayListHitRegions((String, Rect) value) {
  final (String item0, Rect item1) = value;
  return <Object?>[
    item0,
    item1.toJson(),
  ];
}

/// DisplayListNodeBounds：定长元组；wire 为 JSON 数组。
typedef DisplayListNodeBounds = (String, Rect);

/// 严格解码 DisplayListNodeBounds：元素个数或类型不符抛 [FormatException]。
(String, Rect) readDisplayListNodeBoundsValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 DisplayListNodeBounds 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    Rect.fromJson(asObject(items[1])),
  );
}

/// 编码 DisplayListNodeBounds。
List<Object?> encodeDisplayListNodeBounds((String, Rect) value) {
  final (String item0, Rect item1) = value;
  return <Object?>[
    item0,
    item1.toJson(),
  ];
}

/// DisplayPrecision：sealed 联合，按 wire 判别分派到分支类。
sealed class DisplayPrecision {
  /// 常量构造。
  const DisplayPrecision();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory DisplayPrecision.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'least_sig_figs':
          return const DisplayPrecisionLeastSigFigs();
        case 'full':
          return const DisplayPrecisionFull();
        default:
          throw FormatException('未知 DisplayPrecision 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('fixed')) {
        return DisplayPrecisionFixed.fromJson(json);
      }
    }
    throw FormatException('非法 DisplayPrecision 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// DisplayPrecision Fixed：不可变值对象；wire 键见各字段。
final class DisplayPrecisionFixed extends DisplayPrecision {
  /// 由 wire 字段构造。
  const DisplayPrecisionFixed({
    required this.fixed,
  });

  /// wire 键 fixed。
  final int fixed;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DisplayPrecisionFixed.fromJson(Map<String, Object?> json) {
    return DisplayPrecisionFixed(
      fixed: readInt(json, 'fixed'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'fixed': fixed,
    };
  }

  @override
  String toString() {
    return 'DisplayPrecisionFixed(fixed: $fixed)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DisplayPrecisionFixed &&
        dtoEquals(fixed, other.fixed);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(fixed),
  ]);
}

/// DisplayPrecision 的标量分支：wire 取值 'full'。
final class DisplayPrecisionFull extends DisplayPrecision {
  /// 常量分支。
  const DisplayPrecisionFull();

  @override
  Object? toJson() => 'full';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is DisplayPrecisionFull;
  }

  @override
  int get hashCode => 0;
}

/// DisplayPrecision 的标量分支：wire 取值 'least_sig_figs'。
final class DisplayPrecisionLeastSigFigs extends DisplayPrecision {
  /// 常量分支。
  const DisplayPrecisionLeastSigFigs();

  @override
  Object? toJson() => 'least_sig_figs';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is DisplayPrecisionLeastSigFigs;
  }

  @override
  int get hashCode => 0;
}

/// DrawCmd：sealed 联合，按 wire 判别分派到分支类。
sealed class DrawCmd {
  /// 常量构造。
  const DrawCmd();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory DrawCmd.fromJson(Object? json) {
    if (json is Map<String, Object?>) {
      if (json.containsKey('glyph')) {
        return DrawCmdGlyph.fromJson(json);
      }
      if (json.containsKey('rule')) {
        return DrawCmdRule.fromJson(json);
      }
      if (json.containsKey('path')) {
        return DrawCmdPath.fromJson(json);
      }
    }
    throw FormatException('非法 DrawCmd 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// DrawCmd Glyph：不可变值对象；wire 键见各字段。
final class DrawCmdGlyph extends DrawCmd {
  /// 由 wire 字段构造。
  const DrawCmdGlyph({
    required this.glyph,
  });

  /// wire 键 glyph。
  final DrawCmdGlyphGlyph glyph;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdGlyph.fromJson(Map<String, Object?> json) {
    return DrawCmdGlyph(
      glyph: readObject(json, 'glyph', DrawCmdGlyphGlyph.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'glyph': glyph.toJson(),
    };
  }

  @override
  String toString() {
    return 'DrawCmdGlyph(glyph: $glyph)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdGlyph &&
        dtoEquals(glyph, other.glyph);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(glyph),
  ]);
}

/// DrawCmd Path：不可变值对象；wire 键见各字段。
final class DrawCmdPath extends DrawCmd {
  /// 由 wire 字段构造。
  const DrawCmdPath({
    required this.path,
  });

  /// wire 键 path。
  final DrawCmdPathPath path;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdPath.fromJson(Map<String, Object?> json) {
    return DrawCmdPath(
      path: readObject(json, 'path', DrawCmdPathPath.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'path': path.toJson(),
    };
  }

  @override
  String toString() {
    return 'DrawCmdPath(path: $path)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdPath &&
        dtoEquals(path, other.path);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(path),
  ]);
}

/// DrawCmd Rule：不可变值对象；wire 键见各字段。
final class DrawCmdRule extends DrawCmd {
  /// 由 wire 字段构造。
  const DrawCmdRule({
    required this.rule,
  });

  /// wire 键 rule。
  final DrawCmdRuleRule rule;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdRule.fromJson(Map<String, Object?> json) {
    return DrawCmdRule(
      rule: readObject(json, 'rule', DrawCmdRuleRule.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'rule': rule.toJson(),
    };
  }

  @override
  String toString() {
    return 'DrawCmdRule(rule: $rule)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdRule &&
        dtoEquals(rule, other.rule);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(rule),
  ]);
}

/// DrawCmdGlyphGlyph：不可变值对象；wire 键见各字段。
final class DrawCmdGlyphGlyph {
  /// 由 wire 字段构造。
  const DrawCmdGlyphGlyph({
    required this.font,
    required this.glyphId,
    required this.size,
    required this.x,
    required this.y,
  });

  /// wire 键 font。
  final int font;

  /// wire 键 glyph_id。
  final int glyphId;

  /// wire 键 size。
  final double size;

  /// wire 键 x。
  final double x;

  /// wire 键 y。
  final double y;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdGlyphGlyph.fromJson(Map<String, Object?> json) {
    return DrawCmdGlyphGlyph(
      font: readInt(json, 'font'),
      glyphId: readInt(json, 'glyph_id'),
      size: readDouble(json, 'size'),
      x: readDouble(json, 'x'),
      y: readDouble(json, 'y'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'font': font,
      'glyph_id': glyphId,
      'size': size,
      'x': x,
      'y': y,
    };
  }

  @override
  String toString() {
    return 'DrawCmdGlyphGlyph(font: $font, glyphId: $glyphId, size: $size, x: $x, y: $y)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdGlyphGlyph &&
        dtoEquals(font, other.font) &&
        dtoEquals(glyphId, other.glyphId) &&
        dtoEquals(size, other.size) &&
        dtoEquals(x, other.x) &&
        dtoEquals(y, other.y);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(font),
    dtoHash(glyphId),
    dtoHash(size),
    dtoHash(x),
    dtoHash(y),
  ]);
}

/// DrawCmdPathPath：不可变值对象；wire 键见各字段。
final class DrawCmdPathPath {
  /// 由 wire 字段构造。
  const DrawCmdPathPath({
    required this.segs,
    this.strokeWidth,
  });

  /// wire 键 segs。
  final List<PathSeg> segs;

  /// wire 键 stroke_width。
  final double? strokeWidth;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdPathPath.fromJson(Map<String, Object?> json) {
    return DrawCmdPathPath(
      segs: readList(json, 'segs', (Object? value) => PathSeg.fromJson(value)),
      strokeWidth: readDoubleOrNull(json, 'stroke_width'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'segs': encodeList(segs, (PathSeg item) => item.toJson()),
      'stroke_width': strokeWidth,
    };
  }

  @override
  String toString() {
    return 'DrawCmdPathPath(segs: $segs, strokeWidth: $strokeWidth)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdPathPath &&
        dtoEquals(segs, other.segs) &&
        dtoEquals(strokeWidth, other.strokeWidth);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(segs),
    dtoHash(strokeWidth),
  ]);
}

/// DrawCmdRuleRule：不可变值对象；wire 键见各字段。
final class DrawCmdRuleRule {
  /// 由 wire 字段构造。
  const DrawCmdRuleRule({
    required this.h,
    required this.w,
    required this.x,
    required this.y,
  });

  /// wire 键 h。
  final double h;

  /// wire 键 w。
  final double w;

  /// wire 键 x。
  final double x;

  /// wire 键 y。
  final double y;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory DrawCmdRuleRule.fromJson(Map<String, Object?> json) {
    return DrawCmdRuleRule(
      h: readDouble(json, 'h'),
      w: readDouble(json, 'w'),
      x: readDouble(json, 'x'),
      y: readDouble(json, 'y'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'h': h,
      'w': w,
      'x': x,
      'y': y,
    };
  }

  @override
  String toString() {
    return 'DrawCmdRuleRule(h: $h, w: $w, x: $x, y: $y)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is DrawCmdRuleRule &&
        dtoEquals(h, other.h) &&
        dtoEquals(w, other.w) &&
        dtoEquals(x, other.x) &&
        dtoEquals(y, other.y);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(h),
    dtoHash(w),
    dtoHash(x),
    dtoHash(y),
  ]);
}

/// Envelope：不可变值对象；wire 键见各字段。
final class Envelope {
  /// 由 wire 字段构造。
  const Envelope({
    required this.aadVersion,
    required this.accountEpoch,
    required this.ciphertext,
    required this.ciphertextHash,
    required this.deviceId,
    required this.deviceSeq,
    required this.entityId,
    required this.entityType,
    required this.envelopeVersion,
    required this.keyVersion,
    required this.kind,
    required this.nonce,
    required this.opId,
    required this.purpose,
    this.revisionId,
    required this.schemaVersion,
  });

  /// wire 键 aad_version。
  final int aadVersion;

  /// wire 键 account_epoch。
  final int accountEpoch;

  /// wire 键 ciphertext。
  final String ciphertext;

  /// wire 键 ciphertext_hash。
  final String ciphertextHash;

  /// wire 键 device_id。
  final String deviceId;

  /// wire 键 device_seq。
  final int deviceSeq;

  /// wire 键 entity_id。
  final String entityId;

  /// wire 键 entity_type。
  final String entityType;

  /// wire 键 envelope_version。
  final int envelopeVersion;

  /// wire 键 key_version。
  final int keyVersion;

  /// wire 键 kind。
  final String kind;

  /// wire 键 nonce。
  final String nonce;

  /// wire 键 op_id。
  final String opId;

  /// wire 键 purpose。
  final EnvelopePurpose purpose;

  /// wire 键 revision_id。
  final String? revisionId;

  /// wire 键 schema_version。
  final int schemaVersion;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Envelope.fromJson(Map<String, Object?> json) {
    return Envelope(
      aadVersion: readInt(json, 'aad_version'),
      accountEpoch: readInt(json, 'account_epoch'),
      ciphertext: readString(json, 'ciphertext'),
      ciphertextHash: readString(json, 'ciphertext_hash'),
      deviceId: readString(json, 'device_id'),
      deviceSeq: readInt(json, 'device_seq'),
      entityId: readString(json, 'entity_id'),
      entityType: readString(json, 'entity_type'),
      envelopeVersion: readInt(json, 'envelope_version'),
      keyVersion: readInt(json, 'key_version'),
      kind: readString(json, 'kind'),
      nonce: readString(json, 'nonce'),
      opId: readString(json, 'op_id'),
      purpose: readEnum(json, 'purpose', EnvelopePurpose.fromWire),
      revisionId: readStringOrNull(json, 'revision_id'),
      schemaVersion: readInt(json, 'schema_version'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'aad_version': aadVersion,
      'account_epoch': accountEpoch,
      'ciphertext': ciphertext,
      'ciphertext_hash': ciphertextHash,
      'device_id': deviceId,
      'device_seq': deviceSeq,
      'entity_id': entityId,
      'entity_type': entityType,
      'envelope_version': envelopeVersion,
      'key_version': keyVersion,
      'kind': kind,
      'nonce': nonce,
      'op_id': opId,
      'purpose': purpose.wire,
      'revision_id': revisionId,
      'schema_version': schemaVersion,
    };
  }

  @override
  String toString() {
    return 'Envelope(aadVersion: $aadVersion, accountEpoch: $accountEpoch, ciphertext: $ciphertext, ciphertextHash: $ciphertextHash, deviceId: $deviceId, deviceSeq: $deviceSeq, entityId: $entityId, entityType: $entityType, envelopeVersion: $envelopeVersion, keyVersion: $keyVersion, kind: $kind, nonce: $nonce, opId: $opId, purpose: $purpose, revisionId: $revisionId, schemaVersion: $schemaVersion)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Envelope &&
        dtoEquals(aadVersion, other.aadVersion) &&
        dtoEquals(accountEpoch, other.accountEpoch) &&
        dtoEquals(ciphertext, other.ciphertext) &&
        dtoEquals(ciphertextHash, other.ciphertextHash) &&
        dtoEquals(deviceId, other.deviceId) &&
        dtoEquals(deviceSeq, other.deviceSeq) &&
        dtoEquals(entityId, other.entityId) &&
        dtoEquals(entityType, other.entityType) &&
        dtoEquals(envelopeVersion, other.envelopeVersion) &&
        dtoEquals(keyVersion, other.keyVersion) &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(nonce, other.nonce) &&
        dtoEquals(opId, other.opId) &&
        dtoEquals(purpose, other.purpose) &&
        dtoEquals(revisionId, other.revisionId) &&
        dtoEquals(schemaVersion, other.schemaVersion);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(aadVersion),
    dtoHash(accountEpoch),
    dtoHash(ciphertext),
    dtoHash(ciphertextHash),
    dtoHash(deviceId),
    dtoHash(deviceSeq),
    dtoHash(entityId),
    dtoHash(entityType),
    dtoHash(envelopeVersion),
    dtoHash(keyVersion),
    dtoHash(kind),
    dtoHash(nonce),
    dtoHash(opId),
    dtoHash(purpose),
    dtoHash(revisionId),
    dtoHash(schemaVersion),
  ]);
}

/// 枚举 EnvelopePurpose：wire 取值为 [wire]。
enum EnvelopePurpose {
  /// wire 取值 user_formula。
  userFormula('user_formula'),
  /// wire 取值 study_data。
  studyData('study_data'),
  /// wire 取值 user_settings。
  userSettings('user_settings');

  const EnvelopePurpose(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, EnvelopePurpose> byWire = <String, EnvelopePurpose>{
    'user_formula': EnvelopePurpose.userFormula,
    'study_data': EnvelopePurpose.studyData,
    'user_settings': EnvelopePurpose.userSettings,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static EnvelopePurpose fromWire(String wire) {
    final EnvelopePurpose? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 EnvelopePurpose wire 取值: $wire');
    }
    return found;
  }
}

/// FormulaNode：sealed 联合，按 wire 判别分派到分支类。
sealed class FormulaNode {
  /// 常量构造。
  const FormulaNode();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory FormulaNode.fromJson(Object? json) {
    if (json is! Map<String, Object?>) {
      throw FormatException('期望 JSON 对象: ' + json.toString());
    }
    switch (json['k']) {
      case 'symbol':
        return FormulaNodeSymbol.fromJson(json);
      case 'number':
        return FormulaNodeNumber.fromJson(json);
      case 'unit':
        return FormulaNodeUnit.fromJson(json);
      case 'binary':
        return FormulaNodeBinary.fromJson(json);
      case 'unary':
        return FormulaNodeUnary.fromJson(json);
      case 'function':
        return FormulaNodeFunction.fromJson(json);
      case 'derivative':
        return FormulaNodeDerivative.fromJson(json);
      case 'integral':
        return FormulaNodeIntegral.fromJson(json);
      case 'sum_or_limit':
        return FormulaNodeSumOrLimit.fromJson(json);
      case 'vector':
        return FormulaNodeVector.fromJson(json);
      case 'matrix':
        return FormulaNodeMatrix.fromJson(json);
      case 'relation':
        return FormulaNodeRelation.fromJson(json);
      case 'piecewise':
        return FormulaNodePiecewise.fromJson(json);
      case 'hole':
        return FormulaNodeHole.fromJson(json);
      default:
        throw FormatException('未知 FormulaNode 判别取值: ' + json['k'].toString());
    }
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// FormulaNode Binary：不可变值对象；wire 键见各字段。
final class FormulaNodeBinary extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeBinary({
    required this.left,
    required this.op,
    required this.right,
  });

  /// 判别字段 wire 键 k，取常量 binary。
  final String k = 'binary';

  /// wire 键 left。
  final FormulaNode left;

  /// wire 键 op。
  final FormulaNodeBinaryOp op;

  /// wire 键 right。
  final FormulaNode right;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeBinary.fromJson(Map<String, Object?> json) {
    return FormulaNodeBinary(
      left: readValue(json, 'left', FormulaNode.fromJson),
      op: readEnum(json, 'op', FormulaNodeBinaryOp.fromWire),
      right: readValue(json, 'right', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'left': left.toJson(),
      'op': op.wire,
      'right': right.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeBinary(left: $left, op: $op, right: $right)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeBinary &&
        dtoEquals(left, other.left) &&
        dtoEquals(op, other.op) &&
        dtoEquals(right, other.right);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(left),
    dtoHash(op),
    dtoHash(right),
  ]);
}

/// FormulaNode Derivative：不可变值对象；wire 键见各字段。
final class FormulaNodeDerivative extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeDerivative({
    required this.kind,
    required this.order,
    required this.target,
    required this.varValueValue,
  });

  /// 判别字段 wire 键 k，取常量 derivative。
  final String k = 'derivative';

  /// wire 键 kind。
  final FormulaNodeDerivativeKind kind;

  /// wire 键 order。
  final int order;

  /// wire 键 target。
  final FormulaNode target;

  /// wire 键 var。
  final int varValueValue;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeDerivative.fromJson(Map<String, Object?> json) {
    return FormulaNodeDerivative(
      kind: readEnum(json, 'kind', FormulaNodeDerivativeKind.fromWire),
      order: readInt(json, 'order'),
      target: readValue(json, 'target', FormulaNode.fromJson),
      varValueValue: readInt(json, 'var'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'kind': kind.wire,
      'order': order,
      'target': target.toJson(),
      'var': varValueValue,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeDerivative(kind: $kind, order: $order, target: $target, varValueValue: $varValueValue)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeDerivative &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(order, other.order) &&
        dtoEquals(target, other.target) &&
        dtoEquals(varValueValue, other.varValueValue);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(kind),
    dtoHash(order),
    dtoHash(target),
    dtoHash(varValueValue),
  ]);
}

/// FormulaNode Function：不可变值对象；wire 键见各字段。
final class FormulaNodeFunction extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeFunction({
    required this.args,
    required this.id,
  });

  /// 判别字段 wire 键 k，取常量 function。
  final String k = 'function';

  /// wire 键 args。
  final List<FormulaNode> args;

  /// wire 键 id。
  final String id;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeFunction.fromJson(Map<String, Object?> json) {
    return FormulaNodeFunction(
      args: readList(json, 'args', (Object? value) => FormulaNode.fromJson(value)),
      id: readString(json, 'id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'args': encodeList(args, (FormulaNode item) => item.toJson()),
      'id': id,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeFunction(args: $args, id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeFunction &&
        dtoEquals(args, other.args) &&
        dtoEquals(id, other.id);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(args),
    dtoHash(id),
  ]);
}

/// FormulaNode Hole：不可变值对象；wire 键见各字段。
final class FormulaNodeHole extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeHole({
    required this.id,
  });

  /// 判别字段 wire 键 k，取常量 hole。
  final String k = 'hole';

  /// wire 键 id。
  final int id;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeHole.fromJson(Map<String, Object?> json) {
    return FormulaNodeHole(
      id: readInt(json, 'id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'id': id,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeHole(id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeHole &&
        dtoEquals(id, other.id);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(id),
  ]);
}

/// FormulaNode Integral：不可变值对象；wire 键见各字段。
final class FormulaNodeIntegral extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeIntegral({
    required this.differentials,
    required this.integrand,
    required this.kind,
    this.lower,
    this.upper,
  });

  /// 判别字段 wire 键 k，取常量 integral。
  final String k = 'integral';

  /// wire 键 differentials。
  final List<int> differentials;

  /// wire 键 integrand。
  final FormulaNode integrand;

  /// wire 键 kind。
  final FormulaNodeIntegralKind kind;

  /// wire 键 lower。
  final FormulaNode? lower;

  /// wire 键 upper。
  final FormulaNode? upper;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeIntegral.fromJson(Map<String, Object?> json) {
    return FormulaNodeIntegral(
      differentials: readList(json, 'differentials', (Object? value) => asInt(value)),
      integrand: readValue(json, 'integrand', FormulaNode.fromJson),
      kind: readValue(json, 'kind', FormulaNodeIntegralKind.fromJson),
      lower: readValueOrNull(json, 'lower', FormulaNode.fromJson),
      upper: readValueOrNull(json, 'upper', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'differentials': differentials,
      'integrand': integrand.toJson(),
      'kind': kind.toJson(),
      'lower': lower?.toJson(),
      'upper': upper?.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeIntegral(differentials: $differentials, integrand: $integrand, kind: $kind, lower: $lower, upper: $upper)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeIntegral &&
        dtoEquals(differentials, other.differentials) &&
        dtoEquals(integrand, other.integrand) &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(lower, other.lower) &&
        dtoEquals(upper, other.upper);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(differentials),
    dtoHash(integrand),
    dtoHash(kind),
    dtoHash(lower),
    dtoHash(upper),
  ]);
}

/// FormulaNode Matrix：不可变值对象；wire 键见各字段。
final class FormulaNodeMatrix extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeMatrix({
    required this.rows,
  });

  /// 判别字段 wire 键 k，取常量 matrix。
  final String k = 'matrix';

  /// wire 键 rows。
  final List<List<FormulaNode>> rows;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeMatrix.fromJson(Map<String, Object?> json) {
    return FormulaNodeMatrix(
      rows: readList(json, 'rows', (Object? value) => List<FormulaNode>.unmodifiable(asList(value).map<FormulaNode>((Object? value) => FormulaNode.fromJson(value)))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'rows': encodeList(rows, (List<FormulaNode> item) => encodeList(item, (FormulaNode value) => value.toJson())),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeMatrix(rows: $rows)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeMatrix &&
        dtoEquals(rows, other.rows);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(rows),
  ]);
}

/// FormulaNode Number：不可变值对象；wire 键见各字段。
final class FormulaNodeNumber extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeNumber({
    this.sigDigits,
    required this.text,
  });

  /// 判别字段 wire 键 k，取常量 number。
  final String k = 'number';

  /// wire 键 sig_digits。
  final int? sigDigits;

  /// wire 键 text。
  final String text;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeNumber.fromJson(Map<String, Object?> json) {
    return FormulaNodeNumber(
      sigDigits: readIntOrNull(json, 'sig_digits'),
      text: readString(json, 'text'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'sig_digits': sigDigits,
      'text': text,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeNumber(sigDigits: $sigDigits, text: $text)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeNumber &&
        dtoEquals(sigDigits, other.sigDigits) &&
        dtoEquals(text, other.text);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(sigDigits),
    dtoHash(text),
  ]);
}

/// FormulaNode Piecewise：不可变值对象；wire 键见各字段。
final class FormulaNodePiecewise extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodePiecewise({
    required this.branches,
  });

  /// 判别字段 wire 键 k，取常量 piecewise。
  final String k = 'piecewise';

  /// wire 键 branches。
  final List<FormulaNodePiecewiseBranches> branches;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodePiecewise.fromJson(Map<String, Object?> json) {
    return FormulaNodePiecewise(
      branches: readList(json, 'branches', (Object? value) => FormulaNodePiecewiseBranches.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'branches': encodeList(branches, (FormulaNodePiecewiseBranches item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'FormulaNodePiecewise(branches: $branches)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodePiecewise &&
        dtoEquals(branches, other.branches);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(branches),
  ]);
}

/// FormulaNode Relation：不可变值对象；wire 键见各字段。
final class FormulaNodeRelation extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeRelation({
    required this.left,
    required this.op,
    required this.right,
  });

  /// 判别字段 wire 键 k，取常量 relation。
  final String k = 'relation';

  /// wire 键 left。
  final FormulaNode left;

  /// wire 键 op。
  final FormulaNodeRelationOp op;

  /// wire 键 right。
  final FormulaNode right;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeRelation.fromJson(Map<String, Object?> json) {
    return FormulaNodeRelation(
      left: readValue(json, 'left', FormulaNode.fromJson),
      op: readEnum(json, 'op', FormulaNodeRelationOp.fromWire),
      right: readValue(json, 'right', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'left': left.toJson(),
      'op': op.wire,
      'right': right.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeRelation(left: $left, op: $op, right: $right)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeRelation &&
        dtoEquals(left, other.left) &&
        dtoEquals(op, other.op) &&
        dtoEquals(right, other.right);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(left),
    dtoHash(op),
    dtoHash(right),
  ]);
}

/// FormulaNode SumOrLimit：不可变值对象；wire 键见各字段。
final class FormulaNodeSumOrLimit extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeSumOrLimit({
    required this.body,
    this.indexValueValue,
    required this.kind,
    this.lower,
    this.upper,
  });

  /// 判别字段 wire 键 k，取常量 sum_or_limit。
  final String k = 'sum_or_limit';

  /// wire 键 body。
  final FormulaNode body;

  /// wire 键 index。
  final int? indexValueValue;

  /// wire 键 kind。
  final FormulaNodeSumOrLimitKind kind;

  /// wire 键 lower。
  final FormulaNode? lower;

  /// wire 键 upper。
  final FormulaNode? upper;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeSumOrLimit.fromJson(Map<String, Object?> json) {
    return FormulaNodeSumOrLimit(
      body: readValue(json, 'body', FormulaNode.fromJson),
      indexValueValue: readIntOrNull(json, 'index'),
      kind: readEnum(json, 'kind', FormulaNodeSumOrLimitKind.fromWire),
      lower: readValueOrNull(json, 'lower', FormulaNode.fromJson),
      upper: readValueOrNull(json, 'upper', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'body': body.toJson(),
      'index': indexValueValue,
      'kind': kind.wire,
      'lower': lower?.toJson(),
      'upper': upper?.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeSumOrLimit(body: $body, indexValueValue: $indexValueValue, kind: $kind, lower: $lower, upper: $upper)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeSumOrLimit &&
        dtoEquals(body, other.body) &&
        dtoEquals(indexValueValue, other.indexValueValue) &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(lower, other.lower) &&
        dtoEquals(upper, other.upper);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(body),
    dtoHash(indexValueValue),
    dtoHash(kind),
    dtoHash(lower),
    dtoHash(upper),
  ]);
}

/// FormulaNode Symbol：不可变值对象；wire 键见各字段。
final class FormulaNodeSymbol extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeSymbol({
    required this.id,
  });

  /// 判别字段 wire 键 k，取常量 symbol。
  final String k = 'symbol';

  /// wire 键 id。
  final int id;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeSymbol.fromJson(Map<String, Object?> json) {
    return FormulaNodeSymbol(
      id: readInt(json, 'id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'id': id,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeSymbol(id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeSymbol &&
        dtoEquals(id, other.id);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(id),
  ]);
}

/// FormulaNode Unary：不可变值对象；wire 键见各字段。
final class FormulaNodeUnary extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeUnary({
    required this.op,
    required this.operand,
  });

  /// 判别字段 wire 键 k，取常量 unary。
  final String k = 'unary';

  /// wire 键 op。
  final FormulaNodeUnaryOp op;

  /// wire 键 operand。
  final FormulaNode operand;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeUnary.fromJson(Map<String, Object?> json) {
    return FormulaNodeUnary(
      op: readEnum(json, 'op', FormulaNodeUnaryOp.fromWire),
      operand: readValue(json, 'operand', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'op': op.wire,
      'operand': operand.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeUnary(op: $op, operand: $operand)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeUnary &&
        dtoEquals(op, other.op) &&
        dtoEquals(operand, other.operand);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(op),
    dtoHash(operand),
  ]);
}

/// FormulaNode Unit：不可变值对象；wire 键见各字段。
final class FormulaNodeUnit extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeUnit({
    required this.id,
  });

  /// 判别字段 wire 键 k，取常量 unit。
  final String k = 'unit';

  /// wire 键 id。
  final String id;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeUnit.fromJson(Map<String, Object?> json) {
    return FormulaNodeUnit(
      id: readString(json, 'id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'id': id,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeUnit(id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeUnit &&
        dtoEquals(id, other.id);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(id),
  ]);
}

/// FormulaNode Vector：不可变值对象；wire 键见各字段。
final class FormulaNodeVector extends FormulaNode {
  /// 由 wire 字段构造。
  const FormulaNodeVector({
    required this.items,
  });

  /// 判别字段 wire 键 k，取常量 vector。
  final String k = 'vector';

  /// wire 键 items。
  final List<FormulaNode> items;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeVector.fromJson(Map<String, Object?> json) {
    return FormulaNodeVector(
      items: readList(json, 'items', (Object? value) => FormulaNode.fromJson(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'k': k,
      'items': encodeList(items, (FormulaNode item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'FormulaNodeVector(items: $items)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeVector &&
        dtoEquals(items, other.items);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(items),
  ]);
}

/// 枚举 FormulaNodeBinaryOp：wire 取值为 [wire]。
enum FormulaNodeBinaryOp {
  /// wire 取值 add。
  add('add'),
  /// wire 取值 sub。
  sub('sub'),
  /// wire 取值 mul。
  mul('mul'),
  /// wire 取值 div。
  div('div'),
  /// wire 取值 pow。
  pow('pow'),
  /// wire 取值 dot。
  dot('dot'),
  /// wire 取值 cross。
  cross('cross');

  const FormulaNodeBinaryOp(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, FormulaNodeBinaryOp> byWire = <String, FormulaNodeBinaryOp>{
    'add': FormulaNodeBinaryOp.add,
    'sub': FormulaNodeBinaryOp.sub,
    'mul': FormulaNodeBinaryOp.mul,
    'div': FormulaNodeBinaryOp.div,
    'pow': FormulaNodeBinaryOp.pow,
    'dot': FormulaNodeBinaryOp.dot,
    'cross': FormulaNodeBinaryOp.cross,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static FormulaNodeBinaryOp fromWire(String wire) {
    final FormulaNodeBinaryOp? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 FormulaNodeBinaryOp wire 取值: $wire');
    }
    return found;
  }
}

/// 枚举 FormulaNodeDerivativeKind：wire 取值为 [wire]。
enum FormulaNodeDerivativeKind {
  /// wire 取值 ordinary。
  ordinary('ordinary'),
  /// wire 取值 partial。
  partial('partial'),
  /// wire 取值 dot。
  dot('dot');

  const FormulaNodeDerivativeKind(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, FormulaNodeDerivativeKind> byWire = <String, FormulaNodeDerivativeKind>{
    'ordinary': FormulaNodeDerivativeKind.ordinary,
    'partial': FormulaNodeDerivativeKind.partial,
    'dot': FormulaNodeDerivativeKind.dot,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static FormulaNodeDerivativeKind fromWire(String wire) {
    final FormulaNodeDerivativeKind? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 FormulaNodeDerivativeKind wire 取值: $wire');
    }
    return found;
  }
}

/// FormulaNodeIntegralKind：sealed 联合，按 wire 判别分派到分支类。
sealed class FormulaNodeIntegralKind {
  /// 常量构造。
  const FormulaNodeIntegralKind();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory FormulaNodeIntegralKind.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'indefinite':
          return const FormulaNodeIntegralKindIndefinite();
        case 'definite':
          return const FormulaNodeIntegralKindDefinite();
        case 'line':
          return const FormulaNodeIntegralKindLine();
        case 'surface':
          return const FormulaNodeIntegralKindSurface();
        case 'closed':
          return const FormulaNodeIntegralKindClosed();
        default:
          throw FormatException('未知 FormulaNodeIntegralKind 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('multiple')) {
        return FormulaNodeIntegralKindMultiple.fromJson(json);
      }
    }
    throw FormatException('非法 FormulaNodeIntegralKind 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// FormulaNodeIntegralKind 的标量分支：wire 取值 'closed'。
final class FormulaNodeIntegralKindClosed extends FormulaNodeIntegralKind {
  /// 常量分支。
  const FormulaNodeIntegralKindClosed();

  @override
  Object? toJson() => 'closed';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is FormulaNodeIntegralKindClosed;
  }

  @override
  int get hashCode => 0;
}

/// FormulaNodeIntegralKind 的标量分支：wire 取值 'definite'。
final class FormulaNodeIntegralKindDefinite extends FormulaNodeIntegralKind {
  /// 常量分支。
  const FormulaNodeIntegralKindDefinite();

  @override
  Object? toJson() => 'definite';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is FormulaNodeIntegralKindDefinite;
  }

  @override
  int get hashCode => 0;
}

/// FormulaNodeIntegralKind 的标量分支：wire 取值 'indefinite'。
final class FormulaNodeIntegralKindIndefinite extends FormulaNodeIntegralKind {
  /// 常量分支。
  const FormulaNodeIntegralKindIndefinite();

  @override
  Object? toJson() => 'indefinite';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is FormulaNodeIntegralKindIndefinite;
  }

  @override
  int get hashCode => 0;
}

/// FormulaNodeIntegralKind 的标量分支：wire 取值 'line'。
final class FormulaNodeIntegralKindLine extends FormulaNodeIntegralKind {
  /// 常量分支。
  const FormulaNodeIntegralKindLine();

  @override
  Object? toJson() => 'line';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is FormulaNodeIntegralKindLine;
  }

  @override
  int get hashCode => 0;
}

/// FormulaNodeIntegralKind Multiple：不可变值对象；wire 键见各字段。
final class FormulaNodeIntegralKindMultiple extends FormulaNodeIntegralKind {
  /// 由 wire 字段构造。
  const FormulaNodeIntegralKindMultiple({
    required this.multiple,
  });

  /// wire 键 multiple。
  final int multiple;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodeIntegralKindMultiple.fromJson(Map<String, Object?> json) {
    return FormulaNodeIntegralKindMultiple(
      multiple: readInt(json, 'multiple'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'multiple': multiple,
    };
  }

  @override
  String toString() {
    return 'FormulaNodeIntegralKindMultiple(multiple: $multiple)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodeIntegralKindMultiple &&
        dtoEquals(multiple, other.multiple);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(multiple),
  ]);
}

/// FormulaNodeIntegralKind 的标量分支：wire 取值 'surface'。
final class FormulaNodeIntegralKindSurface extends FormulaNodeIntegralKind {
  /// 常量分支。
  const FormulaNodeIntegralKindSurface();

  @override
  Object? toJson() => 'surface';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is FormulaNodeIntegralKindSurface;
  }

  @override
  int get hashCode => 0;
}

/// FormulaNodePiecewiseBranches：不可变值对象；wire 键见各字段。
final class FormulaNodePiecewiseBranches {
  /// 由 wire 字段构造。
  const FormulaNodePiecewiseBranches({
    this.condition,
    required this.value,
  });

  /// wire 键 condition。
  final FormulaNode? condition;

  /// wire 键 value。
  final FormulaNode value;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaNodePiecewiseBranches.fromJson(Map<String, Object?> json) {
    return FormulaNodePiecewiseBranches(
      condition: readValueOrNull(json, 'condition', FormulaNode.fromJson),
      value: readValue(json, 'value', FormulaNode.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'condition': condition?.toJson(),
      'value': value.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaNodePiecewiseBranches(condition: $condition, value: $value)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaNodePiecewiseBranches &&
        dtoEquals(condition, other.condition) &&
        dtoEquals(value, other.value);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(condition),
    dtoHash(value),
  ]);
}

/// 枚举 FormulaNodeRelationOp：wire 取值为 [wire]。
enum FormulaNodeRelationOp {
  /// wire 取值 eq。
  eq('eq'),
  /// wire 取值 ne。
  ne('ne'),
  /// wire 取值 lt。
  lt('lt'),
  /// wire 取值 le。
  le('le'),
  /// wire 取值 gt。
  gt('gt'),
  /// wire 取值 ge。
  ge('ge'),
  /// wire 取值 approx。
  approx('approx'),
  /// wire 取值 equiv。
  equiv('equiv');

  const FormulaNodeRelationOp(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, FormulaNodeRelationOp> byWire = <String, FormulaNodeRelationOp>{
    'eq': FormulaNodeRelationOp.eq,
    'ne': FormulaNodeRelationOp.ne,
    'lt': FormulaNodeRelationOp.lt,
    'le': FormulaNodeRelationOp.le,
    'gt': FormulaNodeRelationOp.gt,
    'ge': FormulaNodeRelationOp.ge,
    'approx': FormulaNodeRelationOp.approx,
    'equiv': FormulaNodeRelationOp.equiv,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static FormulaNodeRelationOp fromWire(String wire) {
    final FormulaNodeRelationOp? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 FormulaNodeRelationOp wire 取值: $wire');
    }
    return found;
  }
}

/// 枚举 FormulaNodeSumOrLimitKind：wire 取值为 [wire]。
enum FormulaNodeSumOrLimitKind {
  /// wire 取值 sum。
  sum('sum'),
  /// wire 取值 product。
  product('product'),
  /// wire 取值 limit。
  limit('limit');

  const FormulaNodeSumOrLimitKind(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, FormulaNodeSumOrLimitKind> byWire = <String, FormulaNodeSumOrLimitKind>{
    'sum': FormulaNodeSumOrLimitKind.sum,
    'product': FormulaNodeSumOrLimitKind.product,
    'limit': FormulaNodeSumOrLimitKind.limit,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static FormulaNodeSumOrLimitKind fromWire(String wire) {
    final FormulaNodeSumOrLimitKind? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 FormulaNodeSumOrLimitKind wire 取值: $wire');
    }
    return found;
  }
}

/// 枚举 FormulaNodeUnaryOp：wire 取值为 [wire]。
enum FormulaNodeUnaryOp {
  /// wire 取值 neg。
  neg('neg'),
  /// wire 取值 plus。
  plus('plus'),
  /// wire 取值 factorial。
  factorial('factorial'),
  /// wire 取值 transpose。
  transpose('transpose'),
  /// wire 取值 conjugate。
  conjugate('conjugate'),
  /// wire 取值 adjugate。
  adjugate('adjugate');

  const FormulaNodeUnaryOp(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, FormulaNodeUnaryOp> byWire = <String, FormulaNodeUnaryOp>{
    'neg': FormulaNodeUnaryOp.neg,
    'plus': FormulaNodeUnaryOp.plus,
    'factorial': FormulaNodeUnaryOp.factorial,
    'transpose': FormulaNodeUnaryOp.transpose,
    'conjugate': FormulaNodeUnaryOp.conjugate,
    'adjugate': FormulaNodeUnaryOp.adjugate,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static FormulaNodeUnaryOp fromWire(String wire) {
    final FormulaNodeUnaryOp? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 FormulaNodeUnaryOp wire 取值: $wire');
    }
    return found;
  }
}

/// FormulaRevision：不可变值对象；wire 键见各字段。
final class FormulaRevision {
  /// 由 wire 字段构造。
  const FormulaRevision({
    required this.ast,
    required this.astSchema,
    required this.conditions,
    required this.createdAtMs,
    this.derivedFrom,
    required this.detached,
    required this.draft,
    required this.id,
    required this.item,
    required this.notationProfileId,
    required this.parents,
    required this.provenance,
    required this.sourceLatex,
    required this.symbols,
    required this.validation,
  });

  /// wire 键 ast。
  final FormulaNode ast;

  /// wire 键 ast_schema。
  final int astSchema;

  /// wire 键 conditions。
  final List<FormulaNode> conditions;

  /// wire 键 created_at_ms。
  final int createdAtMs;

  /// wire 键 derived_from。
  final Derivation? derivedFrom;

  /// wire 键 detached。
  final bool detached;

  /// wire 键 draft。
  final bool draft;

  /// wire 键 id。
  final String id;

  /// wire 键 item。
  final String item;

  /// wire 键 notation_profile_id。
  final String notationProfileId;

  /// wire 键 parents。
  final List<String> parents;

  /// wire 键 provenance。
  final Provenance provenance;

  /// wire 键 source_latex。
  final String sourceLatex;

  /// wire 键 symbols。
  final SymbolEnv symbols;

  /// wire 键 validation。
  final Validation validation;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory FormulaRevision.fromJson(Map<String, Object?> json) {
    return FormulaRevision(
      ast: readValue(json, 'ast', FormulaNode.fromJson),
      astSchema: readInt(json, 'ast_schema'),
      conditions: readList(json, 'conditions', (Object? value) => FormulaNode.fromJson(value)),
      createdAtMs: readInt(json, 'created_at_ms'),
      derivedFrom: readObjectOrNull(json, 'derived_from', Derivation.fromJson),
      detached: readBool(json, 'detached'),
      draft: readBool(json, 'draft'),
      id: readString(json, 'id'),
      item: readString(json, 'item'),
      notationProfileId: readString(json, 'notation_profile_id'),
      parents: readList(json, 'parents', (Object? value) => asString(value)),
      provenance: readValue(json, 'provenance', Provenance.fromJson),
      sourceLatex: readString(json, 'source_latex'),
      symbols: readObject(json, 'symbols', SymbolEnv.fromJson),
      validation: readValue(json, 'validation', Validation.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'ast': ast.toJson(),
      'ast_schema': astSchema,
      'conditions': encodeList(conditions, (FormulaNode item) => item.toJson()),
      'created_at_ms': createdAtMs,
      'derived_from': derivedFrom?.toJson(),
      'detached': detached,
      'draft': draft,
      'id': id,
      'item': item,
      'notation_profile_id': notationProfileId,
      'parents': parents,
      'provenance': provenance.toJson(),
      'source_latex': sourceLatex,
      'symbols': symbols.toJson(),
      'validation': validation.toJson(),
    };
  }

  @override
  String toString() {
    return 'FormulaRevision(ast: $ast, astSchema: $astSchema, conditions: $conditions, createdAtMs: $createdAtMs, derivedFrom: $derivedFrom, detached: $detached, draft: $draft, id: $id, item: $item, notationProfileId: $notationProfileId, parents: $parents, provenance: $provenance, sourceLatex: $sourceLatex, symbols: $symbols, validation: $validation)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is FormulaRevision &&
        dtoEquals(ast, other.ast) &&
        dtoEquals(astSchema, other.astSchema) &&
        dtoEquals(conditions, other.conditions) &&
        dtoEquals(createdAtMs, other.createdAtMs) &&
        dtoEquals(derivedFrom, other.derivedFrom) &&
        dtoEquals(detached, other.detached) &&
        dtoEquals(draft, other.draft) &&
        dtoEquals(id, other.id) &&
        dtoEquals(item, other.item) &&
        dtoEquals(notationProfileId, other.notationProfileId) &&
        dtoEquals(parents, other.parents) &&
        dtoEquals(provenance, other.provenance) &&
        dtoEquals(sourceLatex, other.sourceLatex) &&
        dtoEquals(symbols, other.symbols) &&
        dtoEquals(validation, other.validation);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(ast),
    dtoHash(astSchema),
    dtoHash(conditions),
    dtoHash(createdAtMs),
    dtoHash(derivedFrom),
    dtoHash(detached),
    dtoHash(draft),
    dtoHash(id),
    dtoHash(item),
    dtoHash(notationProfileId),
    dtoHash(parents),
    dtoHash(provenance),
    dtoHash(sourceLatex),
    dtoHash(symbols),
    dtoHash(validation),
  ]);
}

/// IntegrityReport：不可变值对象；wire 键见各字段。
final class IntegrityReport {
  /// 由 wire 字段构造。
  const IntegrityReport({
    required this.foreignKeyViolations,
    required this.ok,
    required this.schemaVersion,
    required this.sqliteMessages,
  });

  /// wire 键 foreign_key_violations。
  final int foreignKeyViolations;

  /// wire 键 ok。
  final bool ok;

  /// wire 键 schema_version。
  final int schemaVersion;

  /// wire 键 sqlite_messages。
  final List<String> sqliteMessages;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory IntegrityReport.fromJson(Map<String, Object?> json) {
    return IntegrityReport(
      foreignKeyViolations: readInt(json, 'foreign_key_violations'),
      ok: readBool(json, 'ok'),
      schemaVersion: readInt(json, 'schema_version'),
      sqliteMessages: readList(json, 'sqlite_messages', (Object? value) => asString(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'foreign_key_violations': foreignKeyViolations,
      'ok': ok,
      'schema_version': schemaVersion,
      'sqlite_messages': sqliteMessages,
    };
  }

  @override
  String toString() {
    return 'IntegrityReport(foreignKeyViolations: $foreignKeyViolations, ok: $ok, schemaVersion: $schemaVersion, sqliteMessages: $sqliteMessages)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is IntegrityReport &&
        dtoEquals(foreignKeyViolations, other.foreignKeyViolations) &&
        dtoEquals(ok, other.ok) &&
        dtoEquals(schemaVersion, other.schemaVersion) &&
        dtoEquals(sqliteMessages, other.sqliteMessages);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(foreignKeyViolations),
    dtoHash(ok),
    dtoHash(schemaVersion),
    dtoHash(sqliteMessages),
  ]);
}

/// LayoutOptions：不可变值对象；wire 键见各字段。
final class LayoutOptions {
  /// 由 wire 字段构造。
  const LayoutOptions({
    required this.displayStyle,
    required this.fontSizePx,
    required this.highlight,
    this.maxWidthPx,
    required this.wrap,
  });

  /// wire 键 display_style。
  final bool displayStyle;

  /// wire 键 font_size_px。
  final double fontSizePx;

  /// wire 键 highlight。
  final List<String> highlight;

  /// wire 键 max_width_px。
  final double? maxWidthPx;

  /// wire 键 wrap。
  final LayoutOptionsWrap wrap;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory LayoutOptions.fromJson(Map<String, Object?> json) {
    return LayoutOptions(
      displayStyle: readBool(json, 'display_style'),
      fontSizePx: readDouble(json, 'font_size_px'),
      highlight: readList(json, 'highlight', (Object? value) => asString(value)),
      maxWidthPx: readDoubleOrNull(json, 'max_width_px'),
      wrap: readEnum(json, 'wrap', LayoutOptionsWrap.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'display_style': displayStyle,
      'font_size_px': fontSizePx,
      'highlight': highlight,
      'max_width_px': maxWidthPx,
      'wrap': wrap.wire,
    };
  }

  @override
  String toString() {
    return 'LayoutOptions(displayStyle: $displayStyle, fontSizePx: $fontSizePx, highlight: $highlight, maxWidthPx: $maxWidthPx, wrap: $wrap)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is LayoutOptions &&
        dtoEquals(displayStyle, other.displayStyle) &&
        dtoEquals(fontSizePx, other.fontSizePx) &&
        dtoEquals(highlight, other.highlight) &&
        dtoEquals(maxWidthPx, other.maxWidthPx) &&
        dtoEquals(wrap, other.wrap);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(displayStyle),
    dtoHash(fontSizePx),
    dtoHash(highlight),
    dtoHash(maxWidthPx),
    dtoHash(wrap),
  ]);
}

/// 枚举 LayoutOptionsWrap：wire 取值为 [wire]。
enum LayoutOptionsWrap {
  /// wire 取值 wrap。
  wrap('wrap'),
  /// wire 取值 scroll。
  scroll('scroll');

  const LayoutOptionsWrap(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, LayoutOptionsWrap> byWire = <String, LayoutOptionsWrap>{
    'wrap': LayoutOptionsWrap.wrap,
    'scroll': LayoutOptionsWrap.scroll,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static LayoutOptionsWrap fromWire(String wire) {
    final LayoutOptionsWrap? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 LayoutOptionsWrap wire 取值: $wire');
    }
    return found;
  }
}

/// LocalSetting：不可变值对象；wire 键见各字段。
final class LocalSetting {
  /// 由 wire 字段构造。
  const LocalSetting({
    this.reminderTime,
  });

  /// wire 键 reminder_time。
  final String? reminderTime;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory LocalSetting.fromJson(Map<String, Object?> json) {
    return LocalSetting(
      reminderTime: readStringOrNull(json, 'reminder_time'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'reminder_time': reminderTime,
    };
  }

  @override
  String toString() {
    return 'LocalSetting(reminderTime: $reminderTime)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is LocalSetting &&
        dtoEquals(reminderTime, other.reminderTime);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(reminderTime),
  ]);
}

/// MathKind：sealed 联合，按 wire 判别分派到分支类。
sealed class MathKind {
  /// 常量构造。
  const MathKind();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory MathKind.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'scalar':
          return const MathKindScalar();
        case 'complex':
          return const MathKindComplex();
        case 'scalar_field':
          return const MathKindScalarField();
        case 'vector_field':
          return const MathKindVectorField();
        case 'sequence':
          return const MathKindSequence();
        case 'series':
          return const MathKindSeries();
        case 'operator':
          return const MathKindOperator();
        case 'distribution':
          return const MathKindDistribution();
        case 'density':
          return const MathKindDensity();
        case 'unknown':
          return const MathKindUnknown();
        default:
          throw FormatException('未知 MathKind 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('vector')) {
        return MathKindVector.fromJson(json);
      }
      if (json.containsKey('matrix')) {
        return MathKindMatrix.fromJson(json);
      }
      if (json.containsKey('function')) {
        return MathKindFunction.fromJson(json);
      }
    }
    throw FormatException('非法 MathKind 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// MathKind 的标量分支：wire 取值 'complex'。
final class MathKindComplex extends MathKind {
  /// 常量分支。
  const MathKindComplex();

  @override
  Object? toJson() => 'complex';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindComplex;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'density'。
final class MathKindDensity extends MathKind {
  /// 常量分支。
  const MathKindDensity();

  @override
  Object? toJson() => 'density';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindDensity;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'distribution'。
final class MathKindDistribution extends MathKind {
  /// 常量分支。
  const MathKindDistribution();

  @override
  Object? toJson() => 'distribution';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindDistribution;
  }

  @override
  int get hashCode => 0;
}

/// MathKind Function：不可变值对象；wire 键见各字段。
final class MathKindFunction extends MathKind {
  /// 由 wire 字段构造。
  const MathKindFunction({
    required this.function,
  });

  /// wire 键 function。
  final int function;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory MathKindFunction.fromJson(Map<String, Object?> json) {
    return MathKindFunction(
      function: readInt(json, 'function'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'function': function,
    };
  }

  @override
  String toString() {
    return 'MathKindFunction(function: $function)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is MathKindFunction &&
        dtoEquals(function, other.function);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(function),
  ]);
}

/// MathKind Matrix：不可变值对象；wire 键见各字段。
final class MathKindMatrix extends MathKind {
  /// 由 wire 字段构造。
  const MathKindMatrix({
    required this.matrix,
  });

  /// wire 键 matrix。
  final (int, int) matrix;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory MathKindMatrix.fromJson(Map<String, Object?> json) {
    return MathKindMatrix(
      matrix: readValue(json, 'matrix', readMathKindMatrixMatrixValue),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'matrix': encodeMathKindMatrixMatrix(matrix),
    };
  }

  @override
  String toString() {
    return 'MathKindMatrix(matrix: $matrix)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is MathKindMatrix &&
        dtoEquals(matrix, other.matrix);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(matrix),
  ]);
}

/// MathKind 的标量分支：wire 取值 'operator'。
final class MathKindOperator extends MathKind {
  /// 常量分支。
  const MathKindOperator();

  @override
  Object? toJson() => 'operator';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindOperator;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'scalar'。
final class MathKindScalar extends MathKind {
  /// 常量分支。
  const MathKindScalar();

  @override
  Object? toJson() => 'scalar';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindScalar;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'scalar_field'。
final class MathKindScalarField extends MathKind {
  /// 常量分支。
  const MathKindScalarField();

  @override
  Object? toJson() => 'scalar_field';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindScalarField;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'sequence'。
final class MathKindSequence extends MathKind {
  /// 常量分支。
  const MathKindSequence();

  @override
  Object? toJson() => 'sequence';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindSequence;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'series'。
final class MathKindSeries extends MathKind {
  /// 常量分支。
  const MathKindSeries();

  @override
  Object? toJson() => 'series';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindSeries;
  }

  @override
  int get hashCode => 0;
}

/// MathKind 的标量分支：wire 取值 'unknown'。
final class MathKindUnknown extends MathKind {
  /// 常量分支。
  const MathKindUnknown();

  @override
  Object? toJson() => 'unknown';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindUnknown;
  }

  @override
  int get hashCode => 0;
}

/// MathKind Vector：不可变值对象；wire 键见各字段。
final class MathKindVector extends MathKind {
  /// 由 wire 字段构造。
  const MathKindVector({
    required this.vector,
  });

  /// wire 键 vector。
  final int? vector;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory MathKindVector.fromJson(Map<String, Object?> json) {
    return MathKindVector(
      vector: readIntPresent(json, 'vector'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'vector': vector,
    };
  }

  @override
  String toString() {
    return 'MathKindVector(vector: $vector)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is MathKindVector &&
        dtoEquals(vector, other.vector);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(vector),
  ]);
}

/// MathKind 的标量分支：wire 取值 'vector_field'。
final class MathKindVectorField extends MathKind {
  /// 常量分支。
  const MathKindVectorField();

  @override
  Object? toJson() => 'vector_field';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is MathKindVectorField;
  }

  @override
  int get hashCode => 0;
}

/// MathKindMatrixMatrix：定长元组；wire 为 JSON 数组。
typedef MathKindMatrixMatrix = (int, int);

/// 严格解码 MathKindMatrixMatrix：元素个数或类型不符抛 [FormatException]。
(int, int) readMathKindMatrixMatrixValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 MathKindMatrixMatrix 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asInt(items[0]),
    asInt(items[1]),
  );
}

/// 编码 MathKindMatrixMatrix。
List<Object?> encodeMathKindMatrixMatrix((int, int) value) {
  final (int item0, int item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// 共享别名 NodePath：wire 形状与 String 相同。
typedef NodePath = String;

/// NotationProfile：不可变值对象；wire 键见各字段。
final class NotationProfile {
  /// 由 wire 字段构造。
  const NotationProfile({
    required this.aliases,
    required this.defaults,
    required this.id,
  });

  /// wire 键 aliases。
  final List<NotationProfileAliases> aliases;

  /// wire 键 defaults。
  final List<(String, String)> defaults;

  /// wire 键 id。
  final String id;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationProfile.fromJson(Map<String, Object?> json) {
    return NotationProfile(
      aliases: readList(json, 'aliases', (Object? value) => NotationProfileAliases.fromJson(asObject(value))),
      defaults: readList(json, 'defaults', (Object? value) => readNotationProfileDefaultsValue(value)),
      id: readString(json, 'id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'aliases': encodeList(aliases, (NotationProfileAliases item) => item.toJson()),
      'defaults': encodeList(defaults, encodeNotationProfileDefaults),
      'id': id,
    };
  }

  @override
  String toString() {
    return 'NotationProfile(aliases: $aliases, defaults: $defaults, id: $id)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationProfile &&
        dtoEquals(aliases, other.aliases) &&
        dtoEquals(defaults, other.defaults) &&
        dtoEquals(id, other.id);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(aliases),
    dtoHash(defaults),
    dtoHash(id),
  ]);
}

/// NotationProfileAliases：不可变值对象；wire 键见各字段。
final class NotationProfileAliases {
  /// 由 wire 字段构造。
  const NotationProfileAliases({
    this.context,
    required this.glyph,
    required this.meaningKey,
  });

  /// wire 键 context。
  final String? context;

  /// wire 键 glyph。
  final String glyph;

  /// wire 键 meaning_key。
  final String meaningKey;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory NotationProfileAliases.fromJson(Map<String, Object?> json) {
    return NotationProfileAliases(
      context: readStringOrNull(json, 'context'),
      glyph: readString(json, 'glyph'),
      meaningKey: readString(json, 'meaning_key'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'context': context,
      'glyph': glyph,
      'meaning_key': meaningKey,
    };
  }

  @override
  String toString() {
    return 'NotationProfileAliases(context: $context, glyph: $glyph, meaningKey: $meaningKey)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is NotationProfileAliases &&
        dtoEquals(context, other.context) &&
        dtoEquals(glyph, other.glyph) &&
        dtoEquals(meaningKey, other.meaningKey);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(context),
    dtoHash(glyph),
    dtoHash(meaningKey),
  ]);
}

/// NotationProfileDefaults：定长元组；wire 为 JSON 数组。
typedef NotationProfileDefaults = (String, String);

/// 严格解码 NotationProfileDefaults：元素个数或类型不符抛 [FormatException]。
(String, String) readNotationProfileDefaultsValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 NotationProfileDefaults 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    asString(items[1]),
  );
}

/// 编码 NotationProfileDefaults。
List<Object?> encodeNotationProfileDefaults((String, String) value) {
  final (String item0, String item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// PathSeg：sealed 联合，按 wire 判别分派到分支类。
sealed class PathSeg {
  /// 常量构造。
  const PathSeg();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory PathSeg.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'close':
          return const PathSegClose();
        default:
          throw FormatException('未知 PathSeg 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('move_to')) {
        return PathSegMoveTo.fromJson(json);
      }
      if (json.containsKey('line_to')) {
        return PathSegLineTo.fromJson(json);
      }
      if (json.containsKey('quad_to')) {
        return PathSegQuadTo.fromJson(json);
      }
      if (json.containsKey('cubic_to')) {
        return PathSegCubicTo.fromJson(json);
      }
    }
    throw FormatException('非法 PathSeg 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// PathSeg 的标量分支：wire 取值 'close'。
final class PathSegClose extends PathSeg {
  /// 常量分支。
  const PathSegClose();

  @override
  Object? toJson() => 'close';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is PathSegClose;
  }

  @override
  int get hashCode => 0;
}

/// PathSeg CubicTo：不可变值对象；wire 键见各字段。
final class PathSegCubicTo extends PathSeg {
  /// 由 wire 字段构造。
  const PathSegCubicTo({
    required this.cubicTo,
  });

  /// wire 键 cubic_to。
  final (double, double, double, double, double, double) cubicTo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PathSegCubicTo.fromJson(Map<String, Object?> json) {
    return PathSegCubicTo(
      cubicTo: readValue(json, 'cubic_to', readPathSegCubicToCubicToValue),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'cubic_to': encodePathSegCubicToCubicTo(cubicTo),
    };
  }

  @override
  String toString() {
    return 'PathSegCubicTo(cubicTo: $cubicTo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PathSegCubicTo &&
        dtoEquals(cubicTo, other.cubicTo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(cubicTo),
  ]);
}

/// PathSeg LineTo：不可变值对象；wire 键见各字段。
final class PathSegLineTo extends PathSeg {
  /// 由 wire 字段构造。
  const PathSegLineTo({
    required this.lineTo,
  });

  /// wire 键 line_to。
  final (double, double) lineTo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PathSegLineTo.fromJson(Map<String, Object?> json) {
    return PathSegLineTo(
      lineTo: readValue(json, 'line_to', readPathSegLineToLineToValue),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'line_to': encodePathSegLineToLineTo(lineTo),
    };
  }

  @override
  String toString() {
    return 'PathSegLineTo(lineTo: $lineTo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PathSegLineTo &&
        dtoEquals(lineTo, other.lineTo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(lineTo),
  ]);
}

/// PathSeg MoveTo：不可变值对象；wire 键见各字段。
final class PathSegMoveTo extends PathSeg {
  /// 由 wire 字段构造。
  const PathSegMoveTo({
    required this.moveTo,
  });

  /// wire 键 move_to。
  final (double, double) moveTo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PathSegMoveTo.fromJson(Map<String, Object?> json) {
    return PathSegMoveTo(
      moveTo: readValue(json, 'move_to', readPathSegMoveToMoveToValue),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'move_to': encodePathSegMoveToMoveTo(moveTo),
    };
  }

  @override
  String toString() {
    return 'PathSegMoveTo(moveTo: $moveTo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PathSegMoveTo &&
        dtoEquals(moveTo, other.moveTo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(moveTo),
  ]);
}

/// PathSeg QuadTo：不可变值对象；wire 键见各字段。
final class PathSegQuadTo extends PathSeg {
  /// 由 wire 字段构造。
  const PathSegQuadTo({
    required this.quadTo,
  });

  /// wire 键 quad_to。
  final (double, double, double, double) quadTo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PathSegQuadTo.fromJson(Map<String, Object?> json) {
    return PathSegQuadTo(
      quadTo: readValue(json, 'quad_to', readPathSegQuadToQuadToValue),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'quad_to': encodePathSegQuadToQuadTo(quadTo),
    };
  }

  @override
  String toString() {
    return 'PathSegQuadTo(quadTo: $quadTo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PathSegQuadTo &&
        dtoEquals(quadTo, other.quadTo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(quadTo),
  ]);
}

/// PathSegCubicToCubicTo：定长元组；wire 为 JSON 数组。
typedef PathSegCubicToCubicTo = (double, double, double, double, double, double);

/// 严格解码 PathSegCubicToCubicTo：元素个数或类型不符抛 [FormatException]。
(double, double, double, double, double, double) readPathSegCubicToCubicToValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 6) {
    throw FormatException('元组 PathSegCubicToCubicTo 期望 6 个元素，实际 ' + items.length.toString());
  }
  return (
    asDouble(items[0]),
    asDouble(items[1]),
    asDouble(items[2]),
    asDouble(items[3]),
    asDouble(items[4]),
    asDouble(items[5]),
  );
}

/// 编码 PathSegCubicToCubicTo。
List<Object?> encodePathSegCubicToCubicTo((double, double, double, double, double, double) value) {
  final (double item0, double item1, double item2, double item3, double item4, double item5) = value;
  return <Object?>[
    item0,
    item1,
    item2,
    item3,
    item4,
    item5,
  ];
}

/// PathSegLineToLineTo：定长元组；wire 为 JSON 数组。
typedef PathSegLineToLineTo = (double, double);

/// 严格解码 PathSegLineToLineTo：元素个数或类型不符抛 [FormatException]。
(double, double) readPathSegLineToLineToValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 PathSegLineToLineTo 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asDouble(items[0]),
    asDouble(items[1]),
  );
}

/// 编码 PathSegLineToLineTo。
List<Object?> encodePathSegLineToLineTo((double, double) value) {
  final (double item0, double item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// PathSegMoveToMoveTo：定长元组；wire 为 JSON 数组。
typedef PathSegMoveToMoveTo = (double, double);

/// 严格解码 PathSegMoveToMoveTo：元素个数或类型不符抛 [FormatException]。
(double, double) readPathSegMoveToMoveToValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 PathSegMoveToMoveTo 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asDouble(items[0]),
    asDouble(items[1]),
  );
}

/// 编码 PathSegMoveToMoveTo。
List<Object?> encodePathSegMoveToMoveTo((double, double) value) {
  final (double item0, double item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// PathSegQuadToQuadTo：定长元组；wire 为 JSON 数组。
typedef PathSegQuadToQuadTo = (double, double, double, double);

/// 严格解码 PathSegQuadToQuadTo：元素个数或类型不符抛 [FormatException]。
(double, double, double, double) readPathSegQuadToQuadToValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 4) {
    throw FormatException('元组 PathSegQuadToQuadTo 期望 4 个元素，实际 ' + items.length.toString());
  }
  return (
    asDouble(items[0]),
    asDouble(items[1]),
    asDouble(items[2]),
    asDouble(items[3]),
  );
}

/// 编码 PathSegQuadToQuadTo。
List<Object?> encodePathSegQuadToQuadTo((double, double, double, double) value) {
  final (double item0, double item1, double item2, double item3) = value;
  return <Object?>[
    item0,
    item1,
    item2,
    item3,
  ];
}

/// Profile：不可变值对象；wire 键见各字段。
final class Profile {
  /// 由 wire 字段构造。
  const Profile({
    this.accountId,
    required this.dbPath,
    this.emailMasked,
    required this.lastUsedMs,
    required this.loggedOut,
    required this.profileId,
    required this.syncEnabled,
  });

  /// wire 键 account_id。
  final String? accountId;

  /// wire 键 db_path。
  final String dbPath;

  /// wire 键 email_masked。
  final String? emailMasked;

  /// wire 键 last_used_ms。
  final int lastUsedMs;

  /// wire 键 logged_out。
  final bool loggedOut;

  /// wire 键 profile_id。
  final String profileId;

  /// wire 键 sync_enabled。
  final bool syncEnabled;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Profile.fromJson(Map<String, Object?> json) {
    return Profile(
      accountId: readStringOrNull(json, 'account_id'),
      dbPath: readString(json, 'db_path'),
      emailMasked: readStringOrNull(json, 'email_masked'),
      lastUsedMs: readInt(json, 'last_used_ms'),
      loggedOut: readBool(json, 'logged_out'),
      profileId: readString(json, 'profile_id'),
      syncEnabled: readBool(json, 'sync_enabled'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'account_id': accountId,
      'db_path': dbPath,
      'email_masked': emailMasked,
      'last_used_ms': lastUsedMs,
      'logged_out': loggedOut,
      'profile_id': profileId,
      'sync_enabled': syncEnabled,
    };
  }

  @override
  String toString() {
    return 'Profile(accountId: $accountId, dbPath: $dbPath, emailMasked: $emailMasked, lastUsedMs: $lastUsedMs, loggedOut: $loggedOut, profileId: $profileId, syncEnabled: $syncEnabled)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Profile &&
        dtoEquals(accountId, other.accountId) &&
        dtoEquals(dbPath, other.dbPath) &&
        dtoEquals(emailMasked, other.emailMasked) &&
        dtoEquals(lastUsedMs, other.lastUsedMs) &&
        dtoEquals(loggedOut, other.loggedOut) &&
        dtoEquals(profileId, other.profileId) &&
        dtoEquals(syncEnabled, other.syncEnabled);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(accountId),
    dtoHash(dbPath),
    dtoHash(emailMasked),
    dtoHash(lastUsedMs),
    dtoHash(loggedOut),
    dtoHash(profileId),
    dtoHash(syncEnabled),
  ]);
}

/// Provenance：sealed 联合，按 wire 判别分派到分支类。
sealed class Provenance {
  /// 常量构造。
  const Provenance();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory Provenance.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'user_input':
          return const ProvenanceUserInput();
        default:
          throw FormatException('未知 Provenance 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('handwriting')) {
        return ProvenanceHandwriting.fromJson(json);
      }
      if (json.containsKey('photo')) {
        return ProvenancePhoto.fromJson(json);
      }
      if (json.containsKey('pack')) {
        return ProvenancePack.fromJson(json);
      }
      if (json.containsKey('import')) {
        return ProvenanceImport.fromJson(json);
      }
    }
    throw FormatException('非法 Provenance 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// Provenance Handwriting：不可变值对象；wire 键见各字段。
final class ProvenanceHandwriting extends Provenance {
  /// 由 wire 字段构造。
  const ProvenanceHandwriting({
    required this.handwriting,
  });

  /// wire 键 handwriting。
  final ProvenanceHandwritingHandwriting handwriting;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenanceHandwriting.fromJson(Map<String, Object?> json) {
    return ProvenanceHandwriting(
      handwriting: readObject(json, 'handwriting', ProvenanceHandwritingHandwriting.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'handwriting': handwriting.toJson(),
    };
  }

  @override
  String toString() {
    return 'ProvenanceHandwriting(handwriting: $handwriting)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenanceHandwriting &&
        dtoEquals(handwriting, other.handwriting);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(handwriting),
  ]);
}

/// Provenance Import：不可变值对象；wire 键见各字段。
final class ProvenanceImport extends Provenance {
  /// 由 wire 字段构造。
  const ProvenanceImport({
    required this.importValueValue,
  });

  /// wire 键 import。
  final ProvenanceImportImport importValueValue;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenanceImport.fromJson(Map<String, Object?> json) {
    return ProvenanceImport(
      importValueValue: readObject(json, 'import', ProvenanceImportImport.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'import': importValueValue.toJson(),
    };
  }

  @override
  String toString() {
    return 'ProvenanceImport(importValueValue: $importValueValue)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenanceImport &&
        dtoEquals(importValueValue, other.importValueValue);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(importValueValue),
  ]);
}

/// Provenance Pack：不可变值对象；wire 键见各字段。
final class ProvenancePack extends Provenance {
  /// 由 wire 字段构造。
  const ProvenancePack({
    required this.pack,
  });

  /// wire 键 pack。
  final ProvenancePackPack pack;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenancePack.fromJson(Map<String, Object?> json) {
    return ProvenancePack(
      pack: readObject(json, 'pack', ProvenancePackPack.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'pack': pack.toJson(),
    };
  }

  @override
  String toString() {
    return 'ProvenancePack(pack: $pack)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenancePack &&
        dtoEquals(pack, other.pack);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(pack),
  ]);
}

/// Provenance Photo：不可变值对象；wire 键见各字段。
final class ProvenancePhoto extends Provenance {
  /// 由 wire 字段构造。
  const ProvenancePhoto({
    required this.photo,
  });

  /// wire 键 photo。
  final ProvenancePhotoPhoto photo;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenancePhoto.fromJson(Map<String, Object?> json) {
    return ProvenancePhoto(
      photo: readObject(json, 'photo', ProvenancePhotoPhoto.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'photo': photo.toJson(),
    };
  }

  @override
  String toString() {
    return 'ProvenancePhoto(photo: $photo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenancePhoto &&
        dtoEquals(photo, other.photo);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(photo),
  ]);
}

/// Provenance 的标量分支：wire 取值 'user_input'。
final class ProvenanceUserInput extends Provenance {
  /// 常量分支。
  const ProvenanceUserInput();

  @override
  Object? toJson() => 'user_input';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is ProvenanceUserInput;
  }

  @override
  int get hashCode => 0;
}

/// ProvenanceHandwritingHandwriting：不可变值对象；wire 键见各字段。
final class ProvenanceHandwritingHandwriting {
  /// 由 wire 字段构造。
  const ProvenanceHandwritingHandwriting({
    required this.session,
  });

  /// wire 键 session。
  final String session;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenanceHandwritingHandwriting.fromJson(Map<String, Object?> json) {
    return ProvenanceHandwritingHandwriting(
      session: readString(json, 'session'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'session': session,
    };
  }

  @override
  String toString() {
    return 'ProvenanceHandwritingHandwriting(session: $session)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenanceHandwritingHandwriting &&
        dtoEquals(session, other.session);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(session),
  ]);
}

/// ProvenanceImportImport：不可变值对象；wire 键见各字段。
final class ProvenanceImportImport {
  /// 由 wire 字段构造。
  const ProvenanceImportImport({
    required this.batch,
  });

  /// wire 键 batch。
  final String batch;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenanceImportImport.fromJson(Map<String, Object?> json) {
    return ProvenanceImportImport(
      batch: readString(json, 'batch'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'batch': batch,
    };
  }

  @override
  String toString() {
    return 'ProvenanceImportImport(batch: $batch)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenanceImportImport &&
        dtoEquals(batch, other.batch);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(batch),
  ]);
}

/// ProvenancePackPack：不可变值对象；wire 键见各字段。
final class ProvenancePackPack {
  /// 由 wire 字段构造。
  const ProvenancePackPack({
    required this.entryKey,
    required this.packId,
    required this.packVersion,
  });

  /// wire 键 entry_key。
  final String entryKey;

  /// wire 键 pack_id。
  final String packId;

  /// wire 键 pack_version。
  final String packVersion;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenancePackPack.fromJson(Map<String, Object?> json) {
    return ProvenancePackPack(
      entryKey: readString(json, 'entry_key'),
      packId: readString(json, 'pack_id'),
      packVersion: readString(json, 'pack_version'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'entry_key': entryKey,
      'pack_id': packId,
      'pack_version': packVersion,
    };
  }

  @override
  String toString() {
    return 'ProvenancePackPack(entryKey: $entryKey, packId: $packId, packVersion: $packVersion)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenancePackPack &&
        dtoEquals(entryKey, other.entryKey) &&
        dtoEquals(packId, other.packId) &&
        dtoEquals(packVersion, other.packVersion);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(entryKey),
    dtoHash(packId),
    dtoHash(packVersion),
  ]);
}

/// ProvenancePhotoPhoto：不可变值对象；wire 键见各字段。
final class ProvenancePhotoPhoto {
  /// 由 wire 字段构造。
  const ProvenancePhotoPhoto({
    required this.session,
  });

  /// wire 键 session。
  final String session;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ProvenancePhotoPhoto.fromJson(Map<String, Object?> json) {
    return ProvenancePhotoPhoto(
      session: readString(json, 'session'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'session': session,
    };
  }

  @override
  String toString() {
    return 'ProvenancePhotoPhoto(session: $session)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ProvenancePhotoPhoto &&
        dtoEquals(session, other.session);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(session),
  ]);
}

/// PullResponse：不可变值对象；wire 键见各字段。
final class PullResponse {
  /// 由 wire 字段构造。
  const PullResponse({
    required this.accountEpoch,
    required this.envelopes,
    required this.hasMore,
    required this.nextCursor,
  });

  /// wire 键 account_epoch。
  final int accountEpoch;

  /// wire 键 envelopes。
  final List<Envelope> envelopes;

  /// wire 键 has_more。
  final bool hasMore;

  /// wire 键 next_cursor。
  final String nextCursor;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PullResponse.fromJson(Map<String, Object?> json) {
    return PullResponse(
      accountEpoch: readInt(json, 'account_epoch'),
      envelopes: readList(json, 'envelopes', (Object? value) => Envelope.fromJson(asObject(value))),
      hasMore: readBool(json, 'has_more'),
      nextCursor: readString(json, 'next_cursor'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'account_epoch': accountEpoch,
      'envelopes': encodeList(envelopes, (Envelope item) => item.toJson()),
      'has_more': hasMore,
      'next_cursor': nextCursor,
    };
  }

  @override
  String toString() {
    return 'PullResponse(accountEpoch: $accountEpoch, envelopes: $envelopes, hasMore: $hasMore, nextCursor: $nextCursor)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PullResponse &&
        dtoEquals(accountEpoch, other.accountEpoch) &&
        dtoEquals(envelopes, other.envelopes) &&
        dtoEquals(hasMore, other.hasMore) &&
        dtoEquals(nextCursor, other.nextCursor);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(accountEpoch),
    dtoHash(envelopes),
    dtoHash(hasMore),
    dtoHash(nextCursor),
  ]);
}

/// PushItemResult：sealed 联合，按 wire 判别分派到分支类。
sealed class PushItemResult {
  /// 常量构造。
  const PushItemResult();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory PushItemResult.fromJson(Object? json) {
    if (json is! Map<String, Object?>) {
      throw FormatException('期望 JSON 对象: ' + json.toString());
    }
    switch (json['status']) {
      case 'ACK':
        return PushItemResultACK.fromJson(json);
      case 'CONFLICT':
        return PushItemResultCONFLICT.fromJson(json);
      default:
        throw FormatException('未知 PushItemResult 判别取值: ' + json['status'].toString());
    }
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// PushItemResult ACK：不可变值对象；wire 键见各字段。
final class PushItemResultACK extends PushItemResult {
  /// 由 wire 字段构造。
  const PushItemResultACK({
    required this.opId,
    required this.serverSeq,
  });

  /// 判别字段 wire 键 status，取常量 ACK。
  final String status = 'ACK';

  /// wire 键 op_id。
  final String opId;

  /// wire 键 server_seq。
  final int serverSeq;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PushItemResultACK.fromJson(Map<String, Object?> json) {
    return PushItemResultACK(
      opId: readString(json, 'op_id'),
      serverSeq: readInt(json, 'server_seq'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'status': status,
      'op_id': opId,
      'server_seq': serverSeq,
    };
  }

  @override
  String toString() {
    return 'PushItemResultACK(opId: $opId, serverSeq: $serverSeq)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PushItemResultACK &&
        dtoEquals(opId, other.opId) &&
        dtoEquals(serverSeq, other.serverSeq);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(opId),
    dtoHash(serverSeq),
  ]);
}

/// PushItemResult CONFLICT：不可变值对象；wire 键见各字段。
final class PushItemResultCONFLICT extends PushItemResult {
  /// 由 wire 字段构造。
  const PushItemResultCONFLICT({
    required this.opId,
  });

  /// 判别字段 wire 键 status，取常量 CONFLICT。
  final String status = 'CONFLICT';

  /// wire 键 op_id。
  final String opId;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory PushItemResultCONFLICT.fromJson(Map<String, Object?> json) {
    return PushItemResultCONFLICT(
      opId: readString(json, 'op_id'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'status': status,
      'op_id': opId,
    };
  }

  @override
  String toString() {
    return 'PushItemResultCONFLICT(opId: $opId)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is PushItemResultCONFLICT &&
        dtoEquals(opId, other.opId);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(opId),
  ]);
}

/// Rational：不可变值对象；wire 键见各字段。
final class Rational {
  /// 由 wire 字段构造。
  const Rational({
    required this.den,
    required this.num,
  });

  /// wire 键 den。
  final String den;

  /// wire 键 num。
  final String num;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Rational.fromJson(Map<String, Object?> json) {
    return Rational(
      den: readString(json, 'den'),
      num: readString(json, 'num'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'den': den,
      'num': num,
    };
  }

  @override
  String toString() {
    return 'Rational(den: $den, num: $num)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Rational &&
        dtoEquals(den, other.den) &&
        dtoEquals(num, other.num);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(den),
    dtoHash(num),
  ]);
}

/// RawSymbol：不可变值对象；wire 键见各字段。
final class RawSymbol {
  /// 由 wire 字段构造。
  const RawSymbol({
    required this.glyph,
    required this.hint,
    required this.id,
    required this.occurrences,
    this.subscript,
  });

  /// wire 键 glyph。
  final String glyph;

  /// wire 键 hint。
  final RawSymbolHint hint;

  /// wire 键 id。
  final int id;

  /// wire 键 occurrences。
  final List<String> occurrences;

  /// wire 键 subscript。
  final String? subscript;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory RawSymbol.fromJson(Map<String, Object?> json) {
    return RawSymbol(
      glyph: readString(json, 'glyph'),
      hint: readEnum(json, 'hint', RawSymbolHint.fromWire),
      id: readInt(json, 'id'),
      occurrences: readList(json, 'occurrences', (Object? value) => asString(value)),
      subscript: readStringOrNull(json, 'subscript'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'glyph': glyph,
      'hint': hint.wire,
      'id': id,
      'occurrences': occurrences,
      'subscript': subscript,
    };
  }

  @override
  String toString() {
    return 'RawSymbol(glyph: $glyph, hint: $hint, id: $id, occurrences: $occurrences, subscript: $subscript)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is RawSymbol &&
        dtoEquals(glyph, other.glyph) &&
        dtoEquals(hint, other.hint) &&
        dtoEquals(id, other.id) &&
        dtoEquals(occurrences, other.occurrences) &&
        dtoEquals(subscript, other.subscript);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(glyph),
    dtoHash(hint),
    dtoHash(id),
    dtoHash(occurrences),
    dtoHash(subscript),
  ]);
}

/// 枚举 RawSymbolHint：wire 取值为 [wire]。
enum RawSymbolHint {
  /// wire 取值 plain。
  plain('plain'),
  /// wire 取值 function_head。
  functionHead('function_head'),
  /// wire 取值 differential。
  differential('differential'),
  /// wire 取值 bound_index。
  boundIndex('bound_index'),
  /// wire 取值 unit_position。
  unitPosition('unit_position');

  const RawSymbolHint(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, RawSymbolHint> byWire = <String, RawSymbolHint>{
    'plain': RawSymbolHint.plain,
    'function_head': RawSymbolHint.functionHead,
    'differential': RawSymbolHint.differential,
    'bound_index': RawSymbolHint.boundIndex,
    'unit_position': RawSymbolHint.unitPosition,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static RawSymbolHint fromWire(String wire) {
    final RawSymbolHint? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 RawSymbolHint wire 取值: $wire');
    }
    return found;
  }
}

/// Rect：不可变值对象；wire 键见各字段。
final class Rect {
  /// 由 wire 字段构造。
  const Rect({
    required this.h,
    required this.w,
    required this.x,
    required this.y,
  });

  /// wire 键 h。
  final double h;

  /// wire 键 w。
  final double w;

  /// wire 键 x。
  final double x;

  /// wire 键 y。
  final double y;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Rect.fromJson(Map<String, Object?> json) {
    return Rect(
      h: readDouble(json, 'h'),
      w: readDouble(json, 'w'),
      x: readDouble(json, 'x'),
      y: readDouble(json, 'y'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'h': h,
      'w': w,
      'x': x,
      'y': y,
    };
  }

  @override
  String toString() {
    return 'Rect(h: $h, w: $w, x: $x, y: $y)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Rect &&
        dtoEquals(h, other.h) &&
        dtoEquals(w, other.w) &&
        dtoEquals(x, other.x) &&
        dtoEquals(y, other.y);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(h),
    dtoHash(w),
    dtoHash(x),
    dtoHash(y),
  ]);
}

/// RevisionSnapshot：不可变值对象；wire 键见各字段。
final class RevisionSnapshot {
  /// 由 wire 字段构造。
  const RevisionSnapshot({
    required this.revision,
    required this.typed,
  });

  /// wire 键 revision。
  final FormulaRevision revision;

  /// wire 键 typed。
  final TypedAst typed;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory RevisionSnapshot.fromJson(Map<String, Object?> json) {
    return RevisionSnapshot(
      revision: readObject(json, 'revision', FormulaRevision.fromJson),
      typed: readObject(json, 'typed', TypedAst.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'revision': revision.toJson(),
      'typed': typed.toJson(),
    };
  }

  @override
  String toString() {
    return 'RevisionSnapshot(revision: $revision, typed: $typed)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is RevisionSnapshot &&
        dtoEquals(revision, other.revision) &&
        dtoEquals(typed, other.typed);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(revision),
    dtoHash(typed),
  ]);
}

/// SlotRef：不可变值对象；wire 键见各字段。
final class SlotRef {
  /// 由 wire 字段构造。
  const SlotRef({
    required this.path,
    required this.revision,
    required this.slotType,
  });

  /// wire 键 path。
  final String path;

  /// wire 键 revision。
  final String revision;

  /// wire 键 slot_type。
  final TypeExpr slotType;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SlotRef.fromJson(Map<String, Object?> json) {
    return SlotRef(
      path: readString(json, 'path'),
      revision: readString(json, 'revision'),
      slotType: readObject(json, 'slot_type', TypeExpr.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'path': path,
      'revision': revision,
      'slot_type': slotType.toJson(),
    };
  }

  @override
  String toString() {
    return 'SlotRef(path: $path, revision: $revision, slotType: $slotType)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SlotRef &&
        dtoEquals(path, other.path) &&
        dtoEquals(revision, other.revision) &&
        dtoEquals(slotType, other.slotType);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(path),
    dtoHash(revision),
    dtoHash(slotType),
  ]);
}

/// SolveCapability：sealed 联合，按 wire 判别分派到分支类。
sealed class SolveCapability {
  /// 常量构造。
  const SolveCapability();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory SolveCapability.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'direct':
          return const SolveCapabilityDirect();
        case 'symbolic':
          return const SolveCapabilitySymbolic();
        case 'numeric_only':
          return const SolveCapabilityNumericOnly();
        default:
          throw FormatException('未知 SolveCapability 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('not_computable')) {
        return SolveCapabilityNotComputable.fromJson(json);
      }
    }
    throw FormatException('非法 SolveCapability 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// SolveCapability 的标量分支：wire 取值 'direct'。
final class SolveCapabilityDirect extends SolveCapability {
  /// 常量分支。
  const SolveCapabilityDirect();

  @override
  Object? toJson() => 'direct';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is SolveCapabilityDirect;
  }

  @override
  int get hashCode => 0;
}

/// SolveCapability NotComputable：不可变值对象；wire 键见各字段。
final class SolveCapabilityNotComputable extends SolveCapability {
  /// 由 wire 字段构造。
  const SolveCapabilityNotComputable({
    required this.notComputable,
  });

  /// wire 键 not_computable。
  final String notComputable;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SolveCapabilityNotComputable.fromJson(Map<String, Object?> json) {
    return SolveCapabilityNotComputable(
      notComputable: readString(json, 'not_computable'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'not_computable': notComputable,
    };
  }

  @override
  String toString() {
    return 'SolveCapabilityNotComputable(notComputable: $notComputable)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SolveCapabilityNotComputable &&
        dtoEquals(notComputable, other.notComputable);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(notComputable),
  ]);
}

/// SolveCapability 的标量分支：wire 取值 'numeric_only'。
final class SolveCapabilityNumericOnly extends SolveCapability {
  /// 常量分支。
  const SolveCapabilityNumericOnly();

  @override
  Object? toJson() => 'numeric_only';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is SolveCapabilityNumericOnly;
  }

  @override
  int get hashCode => 0;
}

/// SolveCapability 的标量分支：wire 取值 'symbolic'。
final class SolveCapabilitySymbolic extends SolveCapability {
  /// 常量分支。
  const SolveCapabilitySymbolic();

  @override
  Object? toJson() => 'symbolic';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is SolveCapabilitySymbolic;
  }

  @override
  int get hashCode => 0;
}

/// 共享别名 SourceMap：wire 形状与 List<SourceSpan> 相同。
typedef SourceMap = List<SourceSpan>;

/// SourceSpan：不可变值对象；wire 键见各字段。
final class SourceSpan {
  /// 由 wire 字段构造。
  const SourceSpan({
    required this.end,
    required this.path,
    required this.start,
  });

  /// wire 键 end。
  final int end;

  /// wire 键 path。
  final String path;

  /// wire 键 start。
  final int start;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SourceSpan.fromJson(Map<String, Object?> json) {
    return SourceSpan(
      end: readInt(json, 'end'),
      path: readString(json, 'path'),
      start: readInt(json, 'start'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'end': end,
      'path': path,
      'start': start,
    };
  }

  @override
  String toString() {
    return 'SourceSpan(end: $end, path: $path, start: $start)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SourceSpan &&
        dtoEquals(end, other.end) &&
        dtoEquals(path, other.path) &&
        dtoEquals(start, other.start);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(end),
    dtoHash(path),
    dtoHash(start),
  ]);
}

/// StoreConfig：不可变值对象；wire 键见各字段。
final class StoreConfig {
  /// 由 wire 字段构造。
  const StoreConfig({
    required this.backupDir,
    required this.dbPath,
    required this.readPool,
  });

  /// wire 键 backup_dir。
  final String backupDir;

  /// wire 键 db_path。
  final String dbPath;

  /// wire 键 read_pool。
  final int readPool;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory StoreConfig.fromJson(Map<String, Object?> json) {
    return StoreConfig(
      backupDir: readString(json, 'backup_dir'),
      dbPath: readString(json, 'db_path'),
      readPool: readInt(json, 'read_pool'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'backup_dir': backupDir,
      'db_path': dbPath,
      'read_pool': readPool,
    };
  }

  @override
  String toString() {
    return 'StoreConfig(backupDir: $backupDir, dbPath: $dbPath, readPool: $readPool)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is StoreConfig &&
        dtoEquals(backupDir, other.backupDir) &&
        dtoEquals(dbPath, other.dbPath) &&
        dtoEquals(readPool, other.readPool);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(backupDir),
    dtoHash(dbPath),
    dtoHash(readPool),
  ]);
}

/// SubstituteRequest：不可变值对象；wire 键见各字段。
final class SubstituteRequest {
  /// 由 wire 字段构造。
  const SubstituteRequest({
    this.branch,
    this.confirmCrossKind,
    required this.slot,
    required this.source,
    required this.sourceOutput,
    required this.target,
    required this.varMap,
  });

  /// wire 键 branch。
  final int? branch;

  /// wire 键 confirm_cross_kind。
  final ConfirmRecord? confirmCrossKind;

  /// wire 键 slot。
  final String slot;

  /// wire 键 source。
  final RevisionSnapshot source;

  /// wire 键 source_output。
  final int sourceOutput;

  /// wire 键 target。
  final RevisionSnapshot target;

  /// wire 键 var_map。
  final List<(int, int)> varMap;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SubstituteRequest.fromJson(Map<String, Object?> json) {
    return SubstituteRequest(
      branch: readIntOrNull(json, 'branch'),
      confirmCrossKind: readObjectOrNull(json, 'confirm_cross_kind', ConfirmRecord.fromJson),
      slot: readString(json, 'slot'),
      source: readObject(json, 'source', RevisionSnapshot.fromJson),
      sourceOutput: readInt(json, 'source_output'),
      target: readObject(json, 'target', RevisionSnapshot.fromJson),
      varMap: readList(json, 'var_map', (Object? value) => readSubstituteRequestVarMapValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'branch': branch,
      'confirm_cross_kind': confirmCrossKind?.toJson(),
      'slot': slot,
      'source': source.toJson(),
      'source_output': sourceOutput,
      'target': target.toJson(),
      'var_map': encodeList(varMap, encodeSubstituteRequestVarMap),
    };
  }

  @override
  String toString() {
    return 'SubstituteRequest(branch: $branch, confirmCrossKind: $confirmCrossKind, slot: $slot, source: $source, sourceOutput: $sourceOutput, target: $target, varMap: $varMap)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SubstituteRequest &&
        dtoEquals(branch, other.branch) &&
        dtoEquals(confirmCrossKind, other.confirmCrossKind) &&
        dtoEquals(slot, other.slot) &&
        dtoEquals(source, other.source) &&
        dtoEquals(sourceOutput, other.sourceOutput) &&
        dtoEquals(target, other.target) &&
        dtoEquals(varMap, other.varMap);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(branch),
    dtoHash(confirmCrossKind),
    dtoHash(slot),
    dtoHash(source),
    dtoHash(sourceOutput),
    dtoHash(target),
    dtoHash(varMap),
  ]);
}

/// SubstituteRequestVarMap：定长元组；wire 为 JSON 数组。
typedef SubstituteRequestVarMap = (int, int);

/// 严格解码 SubstituteRequestVarMap：元素个数或类型不符抛 [FormatException]。
(int, int) readSubstituteRequestVarMapValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 SubstituteRequestVarMap 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asInt(items[0]),
    asInt(items[1]),
  );
}

/// 编码 SubstituteRequestVarMap。
List<Object?> encodeSubstituteRequestVarMap((int, int) value) {
  final (int item0, int item1) = value;
  return <Object?>[
    item0,
    item1,
  ];
}

/// SymbolDecl：不可变值对象；wire 键见各字段。
final class SymbolDecl {
  /// 由 wire 字段构造。
  const SymbolDecl({
    this.declaredType,
    this.domain,
    required this.glyph,
    required this.id,
    required this.meaningKey,
    required this.role,
  });

  /// wire 键 declared_type。
  final TypeDecl? declaredType;

  /// wire 键 domain。
  final String? domain;

  /// wire 键 glyph。
  final String glyph;

  /// wire 键 id。
  final int id;

  /// wire 键 meaning_key。
  final String meaningKey;

  /// wire 键 role。
  final SymbolDeclRole role;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SymbolDecl.fromJson(Map<String, Object?> json) {
    return SymbolDecl(
      declaredType: readObjectOrNull(json, 'declared_type', TypeDecl.fromJson),
      domain: readStringOrNull(json, 'domain'),
      glyph: readString(json, 'glyph'),
      id: readInt(json, 'id'),
      meaningKey: readString(json, 'meaning_key'),
      role: readEnum(json, 'role', SymbolDeclRole.fromWire),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'declared_type': declaredType?.toJson(),
      'domain': domain,
      'glyph': glyph,
      'id': id,
      'meaning_key': meaningKey,
      'role': role.wire,
    };
  }

  @override
  String toString() {
    return 'SymbolDecl(declaredType: $declaredType, domain: $domain, glyph: $glyph, id: $id, meaningKey: $meaningKey, role: $role)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SymbolDecl &&
        dtoEquals(declaredType, other.declaredType) &&
        dtoEquals(domain, other.domain) &&
        dtoEquals(glyph, other.glyph) &&
        dtoEquals(id, other.id) &&
        dtoEquals(meaningKey, other.meaningKey) &&
        dtoEquals(role, other.role);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(declaredType),
    dtoHash(domain),
    dtoHash(glyph),
    dtoHash(id),
    dtoHash(meaningKey),
    dtoHash(role),
  ]);
}

/// 枚举 SymbolDeclRole：wire 取值为 [wire]。
enum SymbolDeclRole {
  /// wire 取值 variable。
  variable('variable'),
  /// wire 取值 constant。
  constant('constant'),
  /// wire 取值 function。
  function('function'),
  /// wire 取值 unit。
  unit('unit'),
  /// wire 取值 bound_var。
  boundVar('bound_var'),
  /// wire 取值 parameter。
  parameter('parameter');

  const SymbolDeclRole(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, SymbolDeclRole> byWire = <String, SymbolDeclRole>{
    'variable': SymbolDeclRole.variable,
    'constant': SymbolDeclRole.constant,
    'function': SymbolDeclRole.function,
    'unit': SymbolDeclRole.unit,
    'bound_var': SymbolDeclRole.boundVar,
    'parameter': SymbolDeclRole.parameter,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static SymbolDeclRole fromWire(String wire) {
    final SymbolDeclRole? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 SymbolDeclRole wire 取值: $wire');
    }
    return found;
  }
}

/// SymbolEnv：不可变值对象；wire 键见各字段。
final class SymbolEnv {
  /// 由 wire 字段构造。
  const SymbolEnv({
    required this.decls,
  });

  /// wire 键 decls。
  final List<SymbolDecl> decls;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory SymbolEnv.fromJson(Map<String, Object?> json) {
    return SymbolEnv(
      decls: readList(json, 'decls', (Object? value) => SymbolDecl.fromJson(asObject(value))),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'decls': encodeList(decls, (SymbolDecl item) => item.toJson()),
    };
  }

  @override
  String toString() {
    return 'SymbolEnv(decls: $decls)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is SymbolEnv &&
        dtoEquals(decls, other.decls);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(decls),
  ]);
}

/// TypeDecl：不可变值对象；wire 键见各字段。
final class TypeDecl {
  /// 由 wire 字段构造。
  const TypeDecl({
    this.dimension,
    this.mathKind,
    this.quantityKind,
  });

  /// wire 键 dimension。
  final String? dimension;

  /// wire 键 math_kind。
  final MathKind? mathKind;

  /// wire 键 quantity_kind。
  final String? quantityKind;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypeDecl.fromJson(Map<String, Object?> json) {
    return TypeDecl(
      dimension: readStringOrNull(json, 'dimension'),
      mathKind: readValueOrNull(json, 'math_kind', MathKind.fromJson),
      quantityKind: readStringOrNull(json, 'quantity_kind'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'dimension': dimension,
      'math_kind': mathKind?.toJson(),
      'quantity_kind': quantityKind,
    };
  }

  @override
  String toString() {
    return 'TypeDecl(dimension: $dimension, mathKind: $mathKind, quantityKind: $quantityKind)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypeDecl &&
        dtoEquals(dimension, other.dimension) &&
        dtoEquals(mathKind, other.mathKind) &&
        dtoEquals(quantityKind, other.quantityKind);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dimension),
    dtoHash(mathKind),
    dtoHash(quantityKind),
  ]);
}

/// TypeExpr：不可变值对象；wire 键见各字段。
final class TypeExpr {
  /// 由 wire 字段构造。
  const TypeExpr({
    required this.assumptions,
    this.dimension,
    required this.mathKind,
    this.quantityKind,
  });

  /// wire 键 assumptions。
  final List<String> assumptions;

  /// wire 键 dimension。
  final DimExpr? dimension;

  /// wire 键 math_kind。
  final MathKind mathKind;

  /// wire 键 quantity_kind。
  final String? quantityKind;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypeExpr.fromJson(Map<String, Object?> json) {
    return TypeExpr(
      assumptions: readList(json, 'assumptions', (Object? value) => asString(value)),
      dimension: readObjectOrNull(json, 'dimension', DimExpr.fromJson),
      mathKind: readValue(json, 'math_kind', MathKind.fromJson),
      quantityKind: readStringOrNull(json, 'quantity_kind'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'assumptions': assumptions,
      'dimension': dimension?.toJson(),
      'math_kind': mathKind.toJson(),
      'quantity_kind': quantityKind,
    };
  }

  @override
  String toString() {
    return 'TypeExpr(assumptions: $assumptions, dimension: $dimension, mathKind: $mathKind, quantityKind: $quantityKind)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypeExpr &&
        dtoEquals(assumptions, other.assumptions) &&
        dtoEquals(dimension, other.dimension) &&
        dtoEquals(mathKind, other.mathKind) &&
        dtoEquals(quantityKind, other.quantityKind);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(assumptions),
    dtoHash(dimension),
    dtoHash(mathKind),
    dtoHash(quantityKind),
  ]);
}

/// TypedAst：不可变值对象；wire 键见各字段。
final class TypedAst {
  /// 由 wire 字段构造。
  const TypedAst({
    required this.types,
  });

  /// wire 键 types。
  final List<(String, TypeExpr)> types;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory TypedAst.fromJson(Map<String, Object?> json) {
    return TypedAst(
      types: readList(json, 'types', (Object? value) => readTypedAstTypesValue(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'types': encodeList(types, encodeTypedAstTypes),
    };
  }

  @override
  String toString() {
    return 'TypedAst(types: $types)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is TypedAst &&
        dtoEquals(types, other.types);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(types),
  ]);
}

/// TypedAstTypes：定长元组；wire 为 JSON 数组。
typedef TypedAstTypes = (String, TypeExpr);

/// 严格解码 TypedAstTypes：元素个数或类型不符抛 [FormatException]。
(String, TypeExpr) readTypedAstTypesValue(Object? value) {
  final List<Object?> items = asList(value);
  if (items.length != 2) {
    throw FormatException('元组 TypedAstTypes 期望 2 个元素，实际 ' + items.length.toString());
  }
  return (
    asString(items[0]),
    TypeExpr.fromJson(asObject(items[1])),
  );
}

/// 编码 TypedAstTypes。
List<Object?> encodeTypedAstTypes((String, TypeExpr) value) {
  final (String item0, TypeExpr item1) = value;
  return <Object?>[
    item0,
    item1.toJson(),
  ];
}

/// Unit：不可变值对象；wire 键见各字段。
final class Unit {
  /// 由 wire 字段构造。
  const Unit({
    required this.dimension,
    required this.id,
    required this.kind,
    required this.namespace,
    this.offset,
    required this.scale,
    required this.version,
  });

  /// wire 键 dimension。
  final DimensionFull dimension;

  /// wire 键 id。
  final String id;

  /// wire 键 kind。
  final UnitKind kind;

  /// wire 键 namespace。
  final String namespace;

  /// wire 键 offset。
  final Rational? offset;

  /// wire 键 scale。
  final Rational scale;

  /// wire 键 version。
  final int version;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory Unit.fromJson(Map<String, Object?> json) {
    return Unit(
      dimension: readObject(json, 'dimension', DimensionFull.fromJson),
      id: readString(json, 'id'),
      kind: readEnum(json, 'kind', UnitKind.fromWire),
      namespace: readString(json, 'namespace'),
      offset: readObjectOrNull(json, 'offset', Rational.fromJson),
      scale: readObject(json, 'scale', Rational.fromJson),
      version: readInt(json, 'version'),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'dimension': dimension.toJson(),
      'id': id,
      'kind': kind.wire,
      'namespace': namespace,
      'offset': offset?.toJson(),
      'scale': scale.toJson(),
      'version': version,
    };
  }

  @override
  String toString() {
    return 'Unit(dimension: $dimension, id: $id, kind: $kind, namespace: $namespace, offset: $offset, scale: $scale, version: $version)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is Unit &&
        dtoEquals(dimension, other.dimension) &&
        dtoEquals(id, other.id) &&
        dtoEquals(kind, other.kind) &&
        dtoEquals(namespace, other.namespace) &&
        dtoEquals(offset, other.offset) &&
        dtoEquals(scale, other.scale) &&
        dtoEquals(version, other.version);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(dimension),
    dtoHash(id),
    dtoHash(kind),
    dtoHash(namespace),
    dtoHash(offset),
    dtoHash(scale),
    dtoHash(version),
  ]);
}

/// 枚举 UnitKind：wire 取值为 [wire]。
enum UnitKind {
  /// wire 取值 absolute。
  absolute('absolute'),
  /// wire 取值 affine_point。
  affinePoint('affine_point'),
  /// wire 取值 difference。
  difference('difference');

  const UnitKind(this.wire);

  /// wire 取值（JSON 字符串）。
  final String wire;

  /// wire 取值 → 成员。
  static const Map<String, UnitKind> byWire = <String, UnitKind>{
    'absolute': UnitKind.absolute,
    'affine_point': UnitKind.affinePoint,
    'difference': UnitKind.difference,
  };

  /// 严格解码：未知 wire 取值抛 [FormatException]。
  static UnitKind fromWire(String wire) {
    final UnitKind? found = byWire[wire];
    if (found == null) {
      throw FormatException('未知 UnitKind wire 取值: $wire');
    }
    return found;
  }
}

/// 共享别名 Uuid：wire 形状与 String 相同。
typedef Uuid = String;

/// Validation：sealed 联合，按 wire 判别分派到分支类。
sealed class Validation {
  /// 常量构造。
  const Validation();

  /// 严格解码：未知判别或形状不符抛 [FormatException]。
  factory Validation.fromJson(Object? json) {
    if (json is String) {
      switch (json) {
        case 'draft':
          return const ValidationDraft();
        case 'unresolved':
          return const ValidationUnresolved();
        case 'invalid':
          return const ValidationInvalid();
        case 'verified':
          return const ValidationVerified();
        default:
          throw FormatException('未知 Validation 取值: ' + json);
      }
    }
    if (json is Map<String, Object?>) {
      if (json.containsKey('verified_polymorphic')) {
        return ValidationVerifiedPolymorphic.fromJson(json);
      }
    }
    throw FormatException('非法 Validation 判别值: ' + json.toString());
  }

  /// 编码为 wire 形状。
  Object? toJson();
}

/// Validation 的标量分支：wire 取值 'draft'。
final class ValidationDraft extends Validation {
  /// 常量分支。
  const ValidationDraft();

  @override
  Object? toJson() => 'draft';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is ValidationDraft;
  }

  @override
  int get hashCode => 0;
}

/// Validation 的标量分支：wire 取值 'invalid'。
final class ValidationInvalid extends Validation {
  /// 常量分支。
  const ValidationInvalid();

  @override
  Object? toJson() => 'invalid';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is ValidationInvalid;
  }

  @override
  int get hashCode => 0;
}

/// Validation 的标量分支：wire 取值 'unresolved'。
final class ValidationUnresolved extends Validation {
  /// 常量分支。
  const ValidationUnresolved();

  @override
  Object? toJson() => 'unresolved';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is ValidationUnresolved;
  }

  @override
  int get hashCode => 0;
}

/// Validation 的标量分支：wire 取值 'verified'。
final class ValidationVerified extends Validation {
  /// 常量分支。
  const ValidationVerified();

  @override
  Object? toJson() => 'verified';

  @override
  bool operator ==(Object other) {
    return identical(this, other) || other is ValidationVerified;
  }

  @override
  int get hashCode => 0;
}

/// Validation VerifiedPolymorphic：不可变值对象；wire 键见各字段。
final class ValidationVerifiedPolymorphic extends Validation {
  /// 由 wire 字段构造。
  const ValidationVerifiedPolymorphic({
    required this.verifiedPolymorphic,
  });

  /// wire 键 verified_polymorphic。
  final ValidationVerifiedPolymorphicVerifiedPolymorphic verifiedPolymorphic;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ValidationVerifiedPolymorphic.fromJson(Map<String, Object?> json) {
    return ValidationVerifiedPolymorphic(
      verifiedPolymorphic: readObject(json, 'verified_polymorphic', ValidationVerifiedPolymorphicVerifiedPolymorphic.fromJson),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'verified_polymorphic': verifiedPolymorphic.toJson(),
    };
  }

  @override
  String toString() {
    return 'ValidationVerifiedPolymorphic(verifiedPolymorphic: $verifiedPolymorphic)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ValidationVerifiedPolymorphic &&
        dtoEquals(verifiedPolymorphic, other.verifiedPolymorphic);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(verifiedPolymorphic),
  ]);
}

/// ValidationVerifiedPolymorphicVerifiedPolymorphic：不可变值对象；wire 键见各字段。
final class ValidationVerifiedPolymorphicVerifiedPolymorphic {
  /// 由 wire 字段构造。
  const ValidationVerifiedPolymorphicVerifiedPolymorphic({
    required this.constraints,
    required this.vars,
  });

  /// wire 键 constraints。
  final List<String> constraints;

  /// wire 键 vars。
  final List<int> vars;

  /// 严格解码：缺失必填或类型不符抛 [FormatException]。
  factory ValidationVerifiedPolymorphicVerifiedPolymorphic.fromJson(Map<String, Object?> json) {
    return ValidationVerifiedPolymorphicVerifiedPolymorphic(
      constraints: readList(json, 'constraints', (Object? value) => asString(value)),
      vars: readList(json, 'vars', (Object? value) => asInt(value)),
    );
  }

  /// 编码为 wire 形状（敏感字段照常传输，仅在 toString 脱敏）。
  Map<String, Object?> toJson() {
    return <String, Object?>{
      'constraints': constraints,
      'vars': vars,
    };
  }

  @override
  String toString() {
    return 'ValidationVerifiedPolymorphicVerifiedPolymorphic(constraints: $constraints, vars: $vars)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        other is ValidationVerifiedPolymorphicVerifiedPolymorphic &&
        dtoEquals(constraints, other.constraints) &&
        dtoEquals(vars, other.vars);
  }

  @override
  int get hashCode => Object.hashAll(<int>[
    dtoHash(constraints),
    dtoHash(vars),
  ]);
}

/// 把 JSON 值收成 double。
double asDouble(Object? value) {
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw const FormatException('元素应为 number');
}

/// 把 JSON 值收成 int。
int asInt(Object? value) {
  if (value is int) return value;
  throw const FormatException('元素应为 int');
}

/// 断言 JSON 数组并返回元素列表。
List<Object?> asList(Object? value) {
  if (value is! List) {
    throw FormatException('期望 JSON 数组: $value');
  }
  return value;
}

/// 把 JSON 值收成对象。
Map<String, Object?> asObject(Object? value) {
  if (value is Map<String, Object?>) return value;
  throw const FormatException('元素应为 object');
}

/// 把 JSON 值收成 string。
String asString(Object? value) {
  if (value is String) return value;
  throw const FormatException('元素应为 string');
}

/// 递归值相等：列表逐项、映射逐键，其余用 ==。
bool dtoEquals(Object? a, Object? b) {
  if (identical(a, b)) {
    return true;
  }
  if (a is List && b is List) {
    if (a.length != b.length) {
      return false;
    }
    for (int index = 0; index < a.length; index++) {
      if (!dtoEquals(a[index], b[index])) {
        return false;
      }
    }
    return true;
  }
  if (a is Map && b is Map) {
    if (a.length != b.length) {
      return false;
    }
    for (final Object? key in a.keys) {
      if (!b.containsKey(key) || !dtoEquals(a[key], b[key])) {
        return false;
      }
    }
    return true;
  }
  return a == b;
}

/// 与 [dtoEquals] 一致的递归哈希：列表有序、映射无序。
int dtoHash(Object? value) {
  if (value is List) {
    final List<int> hashes = <int>[];
    for (final Object? item in value) {
      hashes.add(dtoHash(item));
    }
    return Object.hashAll(hashes);
  }
  if (value is Map) {
    final List<int> hashes = <int>[];
    for (final Object? key in value.keys) {
      hashes.add(Object.hash(dtoHash(key), dtoHash(value[key])));
    }
    return Object.hashAllUnordered(hashes);
  }
  return value.hashCode;
}

/// 把列表逐项编码成 JSON 值。
List<Object?> encodeList<T>(List<T> values, Object? Function(T) encode) {
  return values.map<Object?>(encode).toList(growable: false);
}

/// 严格读取 bool 字段。
bool readBool(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is bool) return value;
  throw FormatException('字段 ' + key + ' 应为 bool');
}

/// 严格读取 number 字段；JSON 整数按 double 收下。
double readDouble(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw FormatException('字段 ' + key + ' 应为 number');
}

/// 读取可空 number 字段。
double? readDoubleOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is int) return value.toDouble();
  if (value is double && value.isFinite) return value;
  throw FormatException('字段 ' + key + ' 应为 number 或 null');
}

/// 严格读取枚举字段（wire 字符串）。
T readEnum<T>(
  Map<String, Object?> json,
  String key,
  T Function(String) fromWire,
) {
  final Object? value = json[key];
  if (value is String) return fromWire(value);
  throw FormatException('字段 ' + key + ' 应为字符串枚举');
}

/// 严格读取 int 字段。
int readInt(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int');
}

/// 读取可空 int 字段。
int? readIntOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is int) return value;
  throw FormatException('字段 ' + key + ' 应为 int 或 null');
}

/// 读取必填且可空的 int 字段：键必须出现，值可为 null。
int? readIntPresent(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填字段 ' + key);
  }
  return readIntOrNull(json, key);
}

/// 严格读取数组字段并逐个解码。
List<T> readList<T>(
  Map<String, Object?> json,
  String key,
  T Function(Object?) decode,
) {
  final Object? value = json[key];
  if (value is List<Object?>) {
    return List<T>.unmodifiable(value.map<T>(decode));
  }
  throw FormatException('字段 ' + key + ' 应为数组');
}

/// 严格读取对象字段并解码。
T readObject<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object');
}

/// 读取可空对象字段并解码。
T? readObjectOrNull<T>(
  Map<String, Object?> json,
  String key,
  T Function(Map<String, Object?>) decode,
) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is Map<String, Object?>) return decode(value);
  throw FormatException('字段 ' + key + ' 应为 object 或 null');
}

/// 严格读取 string 字段。
String readString(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string');
}

/// 读取必填的字符串映射；缺键抛 [FormatException]。
Map<String, String> readStringMap(Map<String, Object?> json, String key) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return readStringMapOrNull(json, key)!;
}

/// 读取字符串映射；值非字符串抛 [FormatException]，结果不可修改。
Map<String, String>? readStringMapOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) {
    return null;
  }
  if (value is! Map) {
    throw FormatException('键 $key 期望 JSON 对象');
  }
  final Map<String, String> out = <String, String>{};
  for (final Object? name in value.keys) {
    if (name is! String) {
      throw FormatException('键 $key 的映射键必须是字符串');
    }
    out[name] = asString(value[name]);
  }
  return Map<String, String>.unmodifiable(out);
}

/// 读取可空 string 字段。
String? readStringOrNull(Map<String, Object?> json, String key) {
  final Object? value = json[key];
  if (value == null) return null;
  if (value is String) return value;
  throw FormatException('字段 ' + key + ' 应为 string 或 null');
}

/// 读取必填键并交给 [decode]；缺键抛 [FormatException]。
T readValue<T>(Map<String, Object?> json, String key, T Function(Object?) decode) {
  if (!json.containsKey(key)) {
    throw FormatException('缺少必填键: $key');
  }
  return decode(json[key]);
}

/// 读取可空键并交给 [decode]；缺键或显式 null 返回 null。
T? readValueOrNull<T>(
    Map<String, Object?> json, String key, T Function(Object?) decode) {
  final Object? value = json[key];
  return value == null ? null : decode(value);
}
