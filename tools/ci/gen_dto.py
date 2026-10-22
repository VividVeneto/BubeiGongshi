"""CORE-67 阶段1：Dart DTO 生成命令行（只读漂移检查 + 显式写盘）。

两个互斥入口：--check 只读（唯一写动作是 --report 指定的漂移报告），--write 只写
本次应存在的确定文件集（<out>/types.g.dart 加每个 ready op 一域的 <out>/<domain>.g.dart），
不写报告、不删任何文件（stale 清理属阶段2）。schema 语义一律由 CORE-100 的
dto_schema.compile_manifest 给出，本脚本只透传 --required-stage/--release。
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



def _rows(result: dto_emit.EmitResult, out_dir: Path) -> list[dict[str, object]]:
    """逐文件状态：阶段1 只看 missing/match/drift（stale 属阶段2）。"""
    rows: list[dict[str, object]] = []
    for item in result.files:
        target = out_dir / item.path
        expected = item.sha256
        if not target.is_file():
            rows.append({"path": _rel(target), "status": "missing",
                         "sha256": None, "expected_sha256": expected})
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        status = "match" if actual == expected else "drift"
        rows.append({"path": _rel(target), "status": status,
                     "sha256": actual, "expected_sha256": expected})
    rows.sort(key=lambda row: str(row["path"]))
    return rows


def _diagnostics(result: dto_emit.EmitResult) -> list[dict[str, object]]:
    """诊断转成报告里的 JSON 形状（CORE-100 的码原样保留）。"""
    return [
        {"severity": diag.severity, "code": diag.code, "op": diag.op,
         "file": diag.file, "pointer": diag.pointer, "message": diag.message}
        for diag in result.diagnostics
    ]


def _report(args: argparse.Namespace, bundle: dto_schema.SchemaBundle,
            result: dto_emit.EmitResult, rows: list[dict[str, object]],
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
        "diagnostics": _diagnostics(result),
        "exit": exit_code,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """写报告：UTF-8、LF、缩进 2，便于 diff。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _write_files(result: dto_emit.EmitResult, out_dir: Path) -> list[str]:
    """写出确定文件集（不删集合外文件，不写报告）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in result.files:
        target = out_dir / item.path
        target.write_text(item.text, encoding="utf-8", newline="\n")
    return [item.path for item in result.files]


def run(argv: list[str] | None = None) -> int:
    """执行一次生成；返回 0/1/2。"""
    args = _parser().parse_args(argv)
    try:
        bundle = dto_schema.compile_manifest(
            _path(args.manifest), required_stage=args.required_stage,
            release=args.release)
        result = dto_emit.emit(bundle, Path(args.manifest).name)
        out_dir = _path(args.out)
        if args.write:
            if result.refused:
                print("dto: 拒绝写入（生成诊断含错误），未改动任何文件", file=sys.stderr)
                return EXIT_DRIFT
            written = _write_files(result, out_dir)
            print("dto: 写入 %d 个文件（ready=%d pending=%d）" % (
                len(written), len(bundle.ready), len(bundle.pending)))
            for name in written:
                print("  " + name)
            return EXIT_OK
        rows = _rows(result, out_dir)
        failed = result.refused or any(row["status"] != "match" for row in rows)
        exit_code = EXIT_DRIFT if failed else EXIT_OK
        report_path = _path(args.report)
        _write_json(report_path, _report(args, bundle, result, rows, exit_code))
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

