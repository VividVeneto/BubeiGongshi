"""CORE-67 阶段2：Dart DTO 生成命令行（只读漂移检查 + 原子写盘 + stale 清理）。

两个互斥入口：--check 只读（唯一写动作是 --report 指定的漂移报告），--write 只写
本次应存在的确定文件集（<out>/types.g.dart 加每个 ready op 一域的 <out>/<domain>.g.dart），
不写报告，写后删除集合外仍带生成头的 *.g.dart。schema 语义一律由 CORE-100 的
dto_schema.compile_manifest 给出，本脚本只透传 --required-stage/--release，并固定
include_shared=True 让类型图带上共享类型（types.schema.json 的具名节点）；不提供
关闭开关，共享类型不得靠命令行裁剪。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dto_emit
import dto_schema

#: 仓库根（tools/ci/gen_dto.py 的上两级）；相对路径都相对它解释。
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = "contracts/dto/manifest.json"
DEFAULT_OUT = "app/lib/binding/dto"
DEFAULT_REPORT = "build/dto/drift.json"
#: 漂移报告格式版本；字段只增不改。
REPORT_VERSION = 1
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_ERROR = 2

#: 供 CORE-41 的 tools/ci/manifest.json 收录的步骤片段（本卡不写该文件，
#: 由 CORE-41 按其冻结的 {version:1, steps:[{id,owner,argv,release_args?}]} 合入）。
CI_STEP_FRAGMENT = json.dumps({
    "id": "dto-drift",
    "owner": "CORE-67",
    "argv": ["python", "tools/ci/gen_dto.py", "--check",
             "--report", "build/dto/drift.json"],
    "release_args": ["--release"],
}, ensure_ascii=False, indent=2) + chr(10)


def _path(value: str) -> Path:
    """相对路径按仓库根展开，绝对路径原样返回。"""
    candidate = Path(value)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _rel(path: Path) -> str:
    """仓库内路径转 posix 相对路径；仓库外保留绝对 posix 路径。"""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _parser() -> argparse.ArgumentParser:
    """命令行：--check 与 --write 互斥且必填。"""
    parser = argparse.ArgumentParser(
        prog="gen_dto.py",
        description="从 CORE-100 类型图生成 Dart DTO；--check 只读，--write 写盘。",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true",
                       help="只读比较生成物与磁盘（唯一写动作是 --report）")
    group.add_argument("--write", action="store_true",
                       help="写出应存在的确定文件集，不写报告")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST,
                        help="DTO manifest 路径（默认 %s）" % DEFAULT_MANIFEST)
    parser.add_argument("--out", default=DEFAULT_OUT,
                        help="生成目录（默认 %s）" % DEFAULT_OUT)
    parser.add_argument("--report", default=DEFAULT_REPORT,
                        help="--check 的漂移报告路径（默认 %s）" % DEFAULT_REPORT)
    parser.add_argument("--required-stage", choices=dto_schema.STAGES, default=None,
                        help="只要求不晚于该阶段的操作（透传给 CORE-100）")
    parser.add_argument("--release", action="store_true",
                        help="按发布口径要求全部操作（透传给 CORE-100）")
    return parser


def _status_rows(result: dto_emit.EmitResult,
                  out_dir: Path) -> tuple[list[dict[str, object]], list[Path]]:
    """逐文件四态：missing/drift/match/stale；stale 为集合外仍带生成头的产物。"""
    rows: list[dict[str, object]] = []
    expected = {item.path: item for item in result.files}
    for item in result.files:
        target = out_dir / item.path
        if not target.is_file():
            rows.append({"path": _rel(target), "status": "missing",
                         "sha256": None, "expected_sha256": item.sha256})
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        status = "match" if actual == item.sha256 else "drift"
        rows.append({"path": _rel(target), "status": status,
                     "sha256": actual, "expected_sha256": item.sha256})
    stale: list[Path] = []
    if out_dir.is_dir():
        for target in sorted(out_dir.glob("*.g.dart")):
            if target.name in expected or not target.is_file():
                continue
            text = target.read_text(encoding="utf-8", errors="replace")
            if dto_emit.has_generated_header(text):
                stale.append(target)
    for target in stale:
        rows.append({"path": _rel(target), "status": "stale",
                     "sha256": None, "expected_sha256": None})
    rows.sort(key=lambda row: str(row["path"]))
    return rows, stale


def _header_diagnostics(result: dto_emit.EmitResult,
                        out_dir: Path) -> list[dto_emit.Diagnostic]:
    """期望路径已有同名文件但缺生成头：两种模式都拒绝覆盖并退 1。"""
    found: list[dto_emit.Diagnostic] = []
    for item in result.files:
        target = out_dir / item.path
        if not target.is_file():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        if dto_emit.has_generated_header(text):
            continue
        found.append(dto_emit.Diagnostic(
            severity="error", code=dto_emit.D_HEADER_MISSING, file=_rel(target),
            pointer=None, op=None, message="目标文件缺少生成头，拒绝覆盖"))
    return found


def _diagnostics(result: dto_emit.EmitResult,
                 extra: list[dto_emit.Diagnostic]) -> list[dict[str, object]]:
    """诊断转成报告里的 JSON 形状（CORE-100 的码原样保留）。"""
    merged = list(result.diagnostics) + list(extra)
    merged.sort(key=lambda diag: (diag.file or "", diag.code, diag.op or "",
                                  diag.message))
    return [
        {"severity": diag.severity, "code": diag.code, "op": diag.op,
         "file": diag.file, "pointer": diag.pointer, "message": diag.message}
        for diag in merged
    ]


def _report(args: argparse.Namespace, bundle: dto_schema.SchemaBundle,
            result: dto_emit.EmitResult, rows: list[dict[str, object]],
            diagnostics: list[dict[str, object]],
            exit_code: int) -> dict[str, object]:
    """--check 的漂移报告；字段只增不改。"""
    return {
        "version": REPORT_VERSION,
        "mode": "check",
        "manifest": _rel(_path(args.manifest)),
        "required_stage": args.required_stage,
        "release": bool(args.release),
        "ready": len(bundle.ready),
        "pending": len(bundle.pending),
        "skipped": list(result.skipped),
        "files": rows,
        "diagnostics": diagnostics,
        "exit": exit_code,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """写报告：UTF-8、LF、缩进 2，便于 diff。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _atomic_write(target: Path, text: str) -> None:
    """同目录临时文件写满后 replace 换名，避免留下半截产物。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name("." + target.name + ".tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
        temp.replace(target)
    finally:
        if temp.exists():
            temp.unlink()


def _write_files(result: dto_emit.EmitResult, out_dir: Path,
                 stale: list[Path]) -> tuple[list[str], list[str]]:
    """原子写出确定文件集，然后删除 stale；返回 (写入, 删除) 名单。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in result.files:
        _atomic_write(out_dir / item.path, item.text)
    removed: list[str] = []
    for target in stale:
        target.unlink()
        removed.append(_rel(target))
    return [item.path for item in result.files], removed


def run(argv: list[str] | None = None) -> int:
    """执行一次生成；返回 0（一致）/1（漂移或拒绝）/2（工具错误）。"""
    args = _parser().parse_args(argv)
    try:
        bundle = dto_schema.compile_manifest(
            _path(args.manifest), required_stage=args.required_stage,
            release=args.release, include_shared=True)
        result = dto_emit.emit(bundle, Path(args.manifest).name)
        out_dir = _path(args.out)
        header = _header_diagnostics(result, out_dir)
        if args.write:
            if result.refused:
                print("dto: 拒绝写入（生成诊断含错误），未改动任何文件", file=sys.stderr)
                return EXIT_DRIFT
            if header:
                print("dto: 拒绝写入：%d 个目标文件缺少生成头，未改动任何文件"
                      % len(header), file=sys.stderr)
                for diag in header:
                    print("  " + (diag.file or ""), file=sys.stderr)
                return EXIT_DRIFT
            rows, stale = _status_rows(result, out_dir)
            written, removed = _write_files(result, out_dir, stale)
            print("dto: 写入 %d 个文件（ready=%d pending=%d，删除 stale=%d）" % (
                len(written), len(bundle.ready), len(bundle.pending), len(removed)))
            for name in written:
                print("  + " + name)
            for name in removed:
                print("  - " + name)
            return EXIT_OK
        rows, _stale = _status_rows(result, out_dir)
        diagnostics = _diagnostics(result, header)
        failed = (result.refused or bool(header)
                  or any(row["status"] != "match" for row in rows))
        exit_code = EXIT_DRIFT if failed else EXIT_OK
        report_path = _path(args.report)
        _write_json(report_path, _report(args, bundle, result, rows, diagnostics,
                                         exit_code))
        counts: dict[str, int] = {}
        for row in rows:
            key = str(row["status"])
            counts[key] = counts.get(key, 0) + 1
        summary = ", ".join("%s=%d" % (key, counts[key]) for key in sorted(counts))
        print("dto: %s ready=%d pending=%d 报告=%s 文件=%s" % (
            "drift" if exit_code else "ok", len(bundle.ready), len(bundle.pending),
            _rel(report_path), summary or "无"))
        return exit_code
    except (OSError, dto_schema.SchemaToolError) as exc:
        print("gen_dto: " + str(exc), file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:  # noqa: BLE001 - 未预期异常必须是工具错误 2
        print("gen_dto: 内部错误 %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    """入口：把 run 的退出码交给解释器。"""
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())

