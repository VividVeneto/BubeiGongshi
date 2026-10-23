#!/usr/bin/env python3
"""CORE-74 门禁：UNSAFE-1（unsafe 白名单）与 UNSAFE-2（SAFETY 注释下界）。

判据见 S0_CORE-74:14。Finding、GateError、emit、run 与退出码收敛由 CORE-69 的
common 提供，词法层由 CORE-69 的 source_scan 提供：本脚本不复制公共类型、不另写
词法器（S0_CORE-69:12）。

- UNSAFE-1：白名单只允许 fml-ffi、fml-imgproc、fml-recognize-local（CORE-01:133
  的常量镜像，脚本不读 SADD）；其他成员（crates/*/ 与存在的 server/）出现 unsafe
  修饰即报 1。成员内全部 **/*.rs 都在扫描面内。
- UNSAFE-2：白名单成员的每处 unsafe 起始行前 3 行内、或同行行尾，须有 SAFETY:
  注释；去掉前缀与空白后不足 8 个非空白字符或不含字母同样报 1。

退出码：0 无 Finding，1 有 Finding，2 输入/环境错误（唯一通道 GATE-1）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:  # pragma: no cover - 运行期由 main 延迟导入，缺失时走 GATE-1
    from common import Finding, Token

# CORE-01:133 的三名白名单；夹具断言恰好三名，产品脚本不读 SADD。
UNSAFE_WHITELIST = frozenset({"fml-ffi", "fml-imgproc", "fml-recognize-local"})
SAFETY_KEYWORD = "SAFETY:"
SAFETY_MIN_CHARS = 8
SAFETY_LOOKBACK_LINES = 3
_SOURCE_SUFFIXES = (".rs",)
# unsafe 关键字：前后都不是标识符字符；r#unsafe 这类原始标识符不算构造。
_UNSAFE_RE = re.compile(r"(?<![0-9A-Za-z_#])unsafe(?![0-9A-Za-z_])")


def _parser(common) -> argparse.ArgumentParser:
    """参数错误同样走 GATE-1：不打印 usage，交给 common.main 收敛成单行。"""
    class _Parser(argparse.ArgumentParser):
        def error(self, message: str) -> None:  # type: ignore[override]
            raise common.GateError(None, (message or "参数错误").splitlines()[0])

    parser = _Parser(prog="check_unsafe.py", add_help=False)
    parser.add_argument("--root", default=None, help="仓库根，缺省为脚本上溯两级")
    return parser


def _crate_members(root: Path) -> list[tuple[str, Path]]:
    """成员 = crates/*/（每个子目录一个 crate）∪ 存在的 server/。"""
    members: list[tuple[str, Path]] = []
    crates = root / "crates"
    if crates.is_dir():
        for child in crates.iterdir():
            if child.is_dir():
                members.append((child.name, child))
    server = root / "server"
    if server.is_dir():
        members.append(("server", server))
    return sorted(members, key=lambda item: item[1].relative_to(root).as_posix())


def _file_tokens(source_scan, member: Path) -> dict[str, list]:
    """按文件分组返回 Token；scan_tree 已保证路径字典序与文件内出现顺序。

    CORE-69 阶段1（850dc28）起 code token 不再吞并紧邻的字面量，本脚本直接消费原样
    token 文本；旧 s0r4 的 _strip_swallowed_literal 补偿随之删除（见 Q26）。
    """
    grouped: dict[str, list] = {}
    for relative, token in source_scan.scan_tree(member, _SOURCE_SUFFIXES):
        grouped.setdefault(relative, []).append(token)
    return grouped


def _comment_body(text: str) -> str | None:
    """去掉注释标记与逐行星号，返回注释正文；不是注释返回 None。"""
    body = text
    if body.startswith("//"):
        body = body[2:]
        while body[:1] in ("/", "!"):
            body = body[1:]
    elif body.startswith("/*"):
        body = body[2:]
        if body.startswith("*"):
            body = body[1:]
        if body.endswith("*/"):
            body = body[:-2]
    else:
        return None
    lines = [line.strip().lstrip("*").strip() for line in body.splitlines()]
    return " ".join(line for line in lines if line)


def _safety_content(body: str | None) -> str | None:
    """注释正文以 SAFETY: 开头时返回其后的说明文本，否则返回 None。"""
    if body is None or not body.startswith(SAFETY_KEYWORD):
        return None
    return body[len(SAFETY_KEYWORD):].strip()


def _safety_reason(comments: Iterable, line: int, offset: int) -> str | None:
    """合规返回 None，否则返回 UNSAFE-2 的原因：取窗口内最近的 SAFETY 注释判定。"""
    nearest: tuple[tuple[int, int], str] | None = None
    has_marker = False
    for comment in comments:
        content = _safety_content(_comment_body(comment.text))
        if content is None:
            continue
        has_marker = True
        end_line = comment.line + comment.text.count("\n")
        same_line = comment.line == line and comment.offset > offset
        preceding = line - SAFETY_LOOKBACK_LINES <= end_line <= line - 1
        if not (same_line or preceding):
            continue
        key = (comment.line, comment.offset)
        if nearest is None or key > nearest[0]:
            nearest = (key, content)
    if not has_marker:
        return "缺少 SAFETY: 注释"
    if nearest is None:
        return f"SAFETY: 注释须位于 unsafe 起始行前 {SAFETY_LOOKBACK_LINES} 行内或同行行尾"
    compact = "".join(nearest[1].split())
    if len(compact) < SAFETY_MIN_CHARS:
        return f"SAFETY 说明不足 {SAFETY_MIN_CHARS} 个非空白字符"
    if not any(char.isalpha() for char in compact):
        return "SAFETY 说明不含字母"
    return None


def _findings(root: Path, common, source_scan) -> list:
    """按成员与出现顺序产出 UNSAFE-1 / UNSAFE-2。"""
    findings = []
    for crate, member in _crate_members(root):
        prefix = member.relative_to(root).as_posix()
        for relative, tokens in _file_tokens(source_scan, member).items():
            path = prefix + "/" + relative
            comments = [token for token in tokens if token.kind == "comment"]
            for token in tokens:
                if token.kind != "code":
                    continue
                for match in _UNSAFE_RE.finditer(token.text):
                    if crate not in UNSAFE_WHITELIST:
                        findings.append(
                            common.Finding(path, token.line, "UNSAFE-1", f"{crate} 不在 unsafe 白名单")
                        )
                        continue
                    offset = token.offset + len(token.text[: match.start()].encode("utf-8"))
                    reason = _safety_reason(comments, token.line, offset)
                    if reason is not None:
                        findings.append(common.Finding(path, token.line, "UNSAFE-2", reason))
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    """命令行入口：先延迟导入 CORE-69 的公共层，再按 common.main 收敛退出码。"""
    try:
        import common
        import source_scan
    except ImportError:
        print("-: GATE-1 依赖 CORE-69 的 common/source_scan 尚未交付", file=sys.stderr)
        return 2

    def body():
        arguments = list(sys.argv[1:] if argv is None else argv)
        args = _parser(common).parse_args(arguments)
        root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
        if not root.is_dir():
            raise common.GateError(None, f"扫描根不是目录：{root}")
        return _findings(root, common, source_scan)

    return common.main(body)


if __name__ == "__main__":
    sys.exit(main())
