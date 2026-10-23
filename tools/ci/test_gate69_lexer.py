#!/usr/bin/env python3
"""CORE-69 阶段1 词法与 scan_tree 验收测试。

对照 SADD/Test/S0/S0_CORE-69_TEST.md 第 6～9 行与卡 SADD/S0/S0_CORE-69_基座.md 第 12、37、43 行。
运行：python -m unittest tools.ci.test_gate69_lexer -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import common
import source_scan

CI_DIR = Path(__file__).resolve().parent
FIXTURES = CI_DIR / "tests" / "fixtures" / "gate69"
SCRIPT = CI_DIR / "source_scan.py"
REPO_ROOT = CI_DIR.parent.parent
SCAN_ROOTS = ("crates", "app", "server")
SKIP_PARTS = {"target", "build", ".dart_tool", ".git", "node_modules", "temp"}


def fixture(name: str) -> Path:
    return FIXTURES / name


def raw_text(path: Path) -> str:
    return Path(path).read_bytes().decode("utf-8")


def tokens_of(name: str, language: str | None = None) -> list:
    return source_scan.tokens(fixture(name), language)


def code_texts(items) -> list[str]:
    return [token.text for token in items if token.kind == "code"]


def string_texts(items) -> list[str]:
    return [token.text for token in items if token.kind == "string"]


def comment_texts(items) -> list[str]:
    return [token.text for token in items if token.kind == "comment"]


def locate(text: str, needle: str, occurrence: int = 0) -> tuple[int, int]:
    index = -1
    for _ in range(occurrence + 1):
        index = text.index(needle, index + 1)
    return index, len(text[:index].encode("utf-8"))


def tree_paths(items) -> list[str]:
    paths: list[str] = []
    for relative, _token in items:
        if not paths or paths[-1] != relative:
            paths.append(relative)
    return paths


def stream_problems(items, data) -> list[str]:
    """按出现顺序核对切片保真、offset 单调且不重叠；返回问题清单（空即合规）。"""
    problems: list[str] = []
    cursor = 0
    for token in items:
        encoded = token.text.encode("utf-8")
        if data[token.offset:token.offset + len(encoded)] != encoded:
            problems.append(f"切片保真失败：{token.text!r} @ {token.offset}")
        if token.offset < cursor:
            problems.append(f"offset 重叠或乱序：{token.text!r} @ {token.offset} < {cursor}")
        cursor = token.offset + len(encoded)
    return problems


def repo_sources() -> list[Path]:
    """真实仓库中 CORE-71/74 会扫描的源文件；跳过构建产物目录。"""
    found: list[Path] = []
    for name in SCAN_ROOTS:
        root = REPO_ROOT / name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if set(path.relative_to(root).parts) & SKIP_PARTS:
                continue
            if path.suffix.lower() not in source_scan.LANGUAGE_BY_SUFFIX:
                continue
            found.append(path)
    return found


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    return common.run([str(SCRIPT), *argv])


class TempDirTest(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)

    def write(self, name: str, data) -> Path:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (bytes, bytearray)):
            target.write_bytes(bytes(data))
        else:
            target.write_bytes(str(data).encode("utf-8"))
        return target


class LexicalTokenTest(TempDirTest):
    def test_t01_offset_is_utf8_bytes(self) -> None:
        path = fixture("utf8_bytes.rs")
        data = path.read_bytes()
        text = data.decode("utf-8")
        items = source_scan.tokens(path)
        index, offset = locate(text, "fn")
        self.assertEqual(offset, len("// 注释\n".encode("utf-8")))
        self.assertEqual(offset, 10)
        fn_token = next(token for token in items if token.text == "fn")
        self.assertEqual((fn_token.offset, fn_token.line), (offset, 2))
        for token in items:
            encoded = token.text.encode("utf-8")
            self.assertEqual(data[token.offset:token.offset + len(encoded)], encoded)
        self.assertEqual(len(text[:index].encode("utf-8")), offset)
        self.assertNotEqual(len(text[:index]), offset)

    def test_t02_line_is_one_based_and_multiline_starts_first(self) -> None:
        path = fixture("rust_block_comments.rs")
        text = raw_text(path)
        items = source_scan.tokens(path)
        block = next(token for token in items if token.kind == "comment")
        self.assertTrue(block.text.startswith("/* 块注释"))
        self.assertIn("\n", block.text)
        self.assertEqual(block.line, 1)
        fn_token = next(token for token in items if token.text == "fn")
        self.assertEqual(fn_token.line, text[:text.index("fn")].count("\n") + 1)
        self.assertEqual(fn_token.line, 4)

    def test_t03_text_is_verbatim_slice(self) -> None:
        broken = {"invalid_utf8.rs", "unclosed_block_comment.rs", "unclosed_string.dart"}
        for path in sorted(FIXTURES.iterdir()):
            if path.name in broken:
                continue
            with self.subTest(name=path.name):
                data = path.read_bytes()
                for token in source_scan.tokens(path):
                    encoded = token.text.encode("utf-8")
                    self.assertEqual(data[token.offset:token.offset + len(encoded)], encoded)

    def test_t04_string_and_comment_keep_markers(self) -> None:
        items = (
            tokens_of("string_vs_comment.rs")
            + tokens_of("dart_strings.dart")
            + tokens_of("rust_char_literal.rs")
            + tokens_of("extern_c.rs")
        )
        for token in items:
            if token.kind == "string":
                body = token.text[1:] if token.text.startswith("r") else token.text
                self.assertIn(body[:1], {"'", '"'}, token.text)
                self.assertIn(token.text[-1:], {"'", '"'}, token.text)
            if token.kind == "comment":
                self.assertTrue(
                    token.text.startswith("//") or token.text.startswith("/*"),
                    token.text,
                )

    def test_t05_kinds_are_three_values(self) -> None:
        seen = set()
        for path in sorted(FIXTURES.iterdir()):
            if path.name.startswith(("unclosed_", "invalid_")):
                continue
            seen.update(token.kind for token in source_scan.tokens(path))
        self.assertEqual(seen, {"code", "string", "comment"})

    def test_t06_code_tokens_split_on_whitespace(self) -> None:
        items = tokens_of("extern_c.rs")
        self.assertEqual(
            code_texts(items),
            ["extern", "{", "fn", "c_call();", "}", "extern", "fn", "f()", "{}"],
        )
        self.assertEqual(string_texts(items), ['"C"', '"C"'])
        for text in code_texts(items):
            self.assertFalse(any(ch.isspace() for ch in text), text)

    def test_t07_only_lf_counts_as_line_break(self) -> None:
        path = self.write("line_break.rs", "a\r\nb\rc\u2028d\u2029e\nf\n")
        items = source_scan.tokens(path)
        self.assertEqual([token.text for token in items], ["a", "b", "c\u2028d\u2029e", "f"])
        self.assertEqual([token.line for token in items], [1, 2, 2, 3])

    def test_t08_crlf_counts_single_line(self) -> None:
        path = self.write("crlf.rs", "a\r\nb\r\nc\n")
        items = source_scan.tokens(path)
        self.assertEqual([token.text for token in items], ["a", "b", "c"])
        self.assertEqual([token.line for token in items], [1, 2, 3])

    def test_t09_u2028_is_plain_character(self) -> None:
        path = self.write("u2028.rs", "let s = \"a\u2028b\";\nlet t = 1;\n")
        items = source_scan.tokens(path)
        self.assertEqual(string_texts(items), ['"a\u2028b"'])
        self.assertEqual([token.text for token in items if token.text == "let"], ["let", "let"])
        self.assertEqual([token.line for token in items if token.text == "let"], [1, 2])

    def test_t10_invalid_utf8_gate_error(self) -> None:
        path = self.write("bad.rs", b"fn f() {}\n\xff\xfe\n")
        with self.assertRaises(common.GateError) as caught:
            source_scan.tokens(path)
        self.assertEqual(str(caught.exception.path), str(path))
        code, out, err = run_cli(["--root", str(self.root)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("\ufffd", err)
        self.assertEqual(len(err.splitlines()), 1)

    def test_t11_dart_single_quote_is_string(self) -> None:
        items = tokens_of("dart_strings.dart")
        self.assertIn("'single'", string_texts(items))
        self.assertNotIn("'single'", code_texts(items))
        self.assertFalse([text for text in code_texts(items) if text.startswith("'")])

    def test_t12_dart_triple_quoted(self) -> None:
        items = tokens_of("dart_strings.dart")
        self.assertIn('"""\ntriple\n"""', string_texts(items))

    def test_t13_dart_raw_string(self) -> None:
        items = tokens_of("dart_strings.dart")
        self.assertIn("r'raw\\d'", string_texts(items))

    def test_t14_rust_lifetime_is_code(self) -> None:
        items = tokens_of("rust_lifetime.rs")
        self.assertEqual(string_texts(items), [])
        self.assertEqual({token.kind for token in items}, {"code"})
        self.assertIn("&'a", code_texts(items))
        self.assertIn("f<'a>(s:", code_texts(items))

    def test_t15_rust_char_literal_is_string(self) -> None:
        self.assertEqual(
            string_texts(tokens_of("rust_char_literal.rs")),
            ["'\\u{1F600}'", "'\\n'", "'\\''"],
        )

    def test_t16_rust_line_comment_markers(self) -> None:
        self.assertEqual(
            comment_texts(tokens_of("rust_doc_comments.rs")),
            ["/// 文档注释", "//! 内部文档注释", "// SAFETY: 调用方保证非空"],
        )

    def test_t17_block_and_doc_block_comments(self) -> None:
        self.assertEqual(
            comment_texts(tokens_of("rust_block_comments.rs")),
            ["/* 块注释\n第二行 */", "/** 文档块注释 */"],
        )

    def test_t18_rust_nested_block_comment(self) -> None:
        items = tokens_of("rust_nested_block.rs")
        comments = [token for token in items if token.kind == "comment"]
        self.assertEqual(len(comments), 1)
        self.assertIn("/* 内 */", comments[0].text)
        self.assertIn("外", comments[0].text)
        self.assertEqual(
            code_texts(items),
            ["fn", "f()", "{", "let", "x", "=", "1;", "}"],
        )

    def test_t19_rust_raw_string_with_hashes(self) -> None:
        self.assertEqual(string_texts(tokens_of("rust_raw_string.rs")), ['r#"a "b" c"#'])

    def test_t20_cpp_raw_string_delimiter(self) -> None:
        self.assertEqual(string_texts(tokens_of("cpp_raw_string.cpp")), ['R"xy(a ) " b)xy"'])

    def test_t21_string_and_comment_do_not_swallow(self) -> None:
        items = tokens_of("string_vs_comment.rs")
        self.assertEqual(string_texts(items), ['"http://x//y"'])
        self.assertEqual(comment_texts(items), ['/* "not a string" */'])

    def test_t22_unclosed_is_gate_error(self) -> None:
        for name in ("unclosed_block_comment.rs", "unclosed_string.dart"):
            with self.subTest(name=name):
                with self.assertRaises(common.GateError) as caught:
                    source_scan.tokens(fixture(name))
                self.assertEqual(str(caught.exception.path), str(fixture(name)))
        code, out, err = run_cli(["--root", str(FIXTURES)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(len(err.splitlines()), 1)
        self.assertRegex(err, r"^.+: GATE-1 \S.*\n$")

    def test_t39_safety_comment_single_token(self) -> None:
        items = tokens_of("rust_doc_comments.rs")
        safety = [token for token in items if token.text.startswith("// SAFETY:")]
        self.assertEqual(len(safety), 1)
        self.assertEqual(safety[0].kind, "comment")
        self.assertEqual(safety[0].line, 3)
        self.assertEqual(safety[0].text, "// SAFETY: 调用方保证非空")

    def test_t40_kind_projection(self) -> None:
        items = tokens_of("string_vs_comment.rs")
        self.assertEqual({token.kind for token in items}, {"code", "string", "comment"})
        projection = " ".join(code_texts(items))
        self.assertNotIn("http", projection)
        self.assertNotIn("not a string", projection)
        self.assertEqual(
            code_texts(items),
            ["fn", "f()", "{", "let", "url", "=", ";", "}"],
        )


class LanguageDetectionTest(TempDirTest):
    def test_t23_unbalanced_brackets_ok(self) -> None:
        self.write("unbalanced.rs", "fn f() { (\n")
        items = source_scan.tokens(self.root / "unbalanced.rs")
        self.assertTrue(items)
        code, out, err = run_cli(["--root", str(self.root)])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("unbalanced.rs: 4 token(s)", out)

    def test_t24_missing_or_directory_path(self) -> None:
        missing = self.root / "missing.rs"
        with self.assertRaises(common.GateError) as caught:
            source_scan.tokens(missing)
        self.assertEqual(str(caught.exception.path), str(missing))
        with self.assertRaises(common.GateError):
            source_scan.tokens(self.root)
        code, out, err = run_cli(["--root", str(missing)])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1)
        self.assertRegex(err, r"^.+: GATE-1 \S.*\n$")

    def test_t24b_unknown_option_is_gate_error(self) -> None:
        """未知参数走 GATE-1：stdout 空、stderr 单行、path 为 `-`。"""
        code, out, err = run_cli(["--nope"])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("-: GATE-1 "), err)
        self.assertEqual(err.count("\n"), 1)

    def test_t25_suffix_language_mapping(self) -> None:
        self.assertEqual(
            source_scan.LANGUAGE_BY_SUFFIX,
            {
                ".rs": "rust",
                ".dart": "dart",
                ".h": "cpp",
                ".hpp": "cpp",
                ".c": "cpp",
                ".cc": "cpp",
                ".cpp": "cpp",
            },
        )
        rust_file = self.write("a.rs", "fn f<'a>(s: &'a str) {}\n")
        dart_file = self.write("b.dart", "const a = 'x';\n")
        header = self.write("c.h", 'const char* s = R"z(a)z";\n')
        cpp_file = self.write("d.cpp", 'const char* s = R"z(a)z";\n')
        self.assertEqual(string_texts(source_scan.tokens(rust_file)), [])
        self.assertEqual(string_texts(source_scan.tokens(dart_file)), ["'x'"])
        self.assertEqual(string_texts(source_scan.tokens(header)), ['R"z(a)z"'])
        self.assertEqual(string_texts(source_scan.tokens(cpp_file)), ['R"z(a)z"'])

    def test_t26_unknown_suffix_gate_error(self) -> None:
        path = self.write("x.txt", "let x = 1;\n")
        with self.assertRaises(common.GateError) as caught:
            source_scan.tokens(path)
        self.assertEqual(str(caught.exception.path), str(path))
        code, out, err = run_cli(["--root", str(self.root), "--suffix", ".txt"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1)

    def test_t27_explicit_language_overrides_suffix(self) -> None:
        path = self.write("raw.inc", 'const char* s = R"z(a)z";\n')
        with self.assertRaises(common.GateError):
            source_scan.tokens(path)
        self.assertEqual(string_texts(source_scan.tokens(path, "cpp")), ['R"z(a)z"'])
        self.assertEqual(
            string_texts(source_scan.tokens(path, language="cpp")),
            ['R"z(a)z"'],
        )


class ScanTreeTest(TempDirTest):
    def test_t28_scan_tree_relative_posix(self) -> None:
        self.write("a.rs", "fn a() {}\n")
        self.write("sub/b.rs", "fn b() {}\n")
        items = source_scan.scan_tree(self.root, [".rs"])
        self.assertEqual(tree_paths(items), ["a.rs", "sub/b.rs"])
        for rel, token in items:
            self.assertNotIn("\\", rel)
            self.assertFalse(Path(rel).is_absolute(), rel)
            self.assertEqual(token.kind, "code")
        self.assertEqual([token.text for _, token in items], ["fn", "a()", "{}", "fn", "b()", "{}"])

    def test_t29_scan_tree_sorted_by_path(self) -> None:
        self.write("b.rs", "fn b() {}\n")
        self.write("a/z.rs", "fn z() {}\n")
        self.write("a.rs", "fn a() {}\n")
        paths = tree_paths(source_scan.scan_tree(self.root, [".rs"]))
        self.assertEqual(paths, ["a.rs", "a/z.rs", "b.rs"])

    def test_t30_scan_tree_suffix_filter(self) -> None:
        self.write("a.rs", "fn a() {}\n")
        self.write("b.txt", "let x = 1;\n")
        self.write("c.dart", "const a = 'x';\n")
        self.assertEqual(tree_paths(source_scan.scan_tree(self.root, [".rs"])), ["a.rs"])
        self.assertEqual(tree_paths(source_scan.scan_tree(self.root, [".dart"])), ["c.dart"])
        self.assertEqual(tree_paths(source_scan.scan_tree(self.root, ["rs"])), ["a.rs"])


class LiteralBoundaryTest(TempDirTest):
    """B1/B2 回归：Rust 裸换行字符串与紧邻字面量的 token 边界（卡:37、卡:43）。"""

    def test_t42_rust_double_quote_allows_bare_newline(self) -> None:
        """B1：Rust 普通双引号字符串跨行仍是一个 string token，起始行取首行。"""
        path = fixture("rust_multiline_string.rs")
        data = path.read_bytes()
        items = source_scan.tokens(path)
        strings = [token for token in items if token.kind == "string"]
        self.assertEqual(len(strings), 1)
        token = strings[0]
        self.assertIn("\n", token.text)
        self.assertTrue(token.text.startswith('"') and token.text.endswith('"'), token.text)
        self.assertEqual(token.line, 2)
        encoded = token.text.encode("utf-8")
        self.assertEqual(data[token.offset:token.offset + len(encoded)], encoded)
        self.assertEqual(
            code_texts(items),
            ["const", "DOC:", "&str", "=", ";", "fn", "after()", "{}"],
        )
        following = next(item for item in items if item.text == "fn")
        self.assertEqual(following.line, 5)
        self.assertEqual(stream_problems(items, data), [])

    def test_t43_other_quotes_still_reject_bare_newline(self) -> None:
        """B1 边界：只有 Rust 双引号放开裸换行，Dart 单/双引号、C++ 与 Rust 单引号仍报 2。"""
        cases = {
            "single.dart": "const s = 'a\nb';\n",
            "double.dart": 'const s = "a\nb";\n',
            "double.cpp": 'const char* s = "a\nb";\n',
            "quote.rs": "let c = '\n",
        }
        for name, data in cases.items():
            with self.subTest(name=name):
                path = self.write(name, data)
                with self.assertRaises(common.GateError) as caught:
                    source_scan.tokens(path)
                self.assertIn("字符串未闭合", str(caught.exception))

    def test_t44_adjacent_literals_keep_order_without_overlap(self) -> None:
        """B2：紧邻字符串/注释先 flush 代码段，token 顺序与 offset 不重叠，code 不含字面量。"""
        path = fixture("literal_adjacent.rs")
        data = path.read_bytes()
        items = source_scan.tokens(path)
        self.assertEqual(stream_problems(items, data), [])
        self.assertEqual(
            [(token.text, token.kind) for token in items[:5]],
            [("fn", "code"), ("call()", "code"), ("{", "code"), ("g(", "code"), ('"x"', "string")],
        )
        self.assertEqual(
            [(token.text, token.kind) for token in items[7:11]],
            [("fn", "code"), ("tail()", "code"), ("{}", "code"), ("// 尾注释", "comment")],
        )
        self.assertEqual(
            code_texts(items),
            [
                "fn", "call()", "{", "g(", ");", "}",
                "fn", "tail()", "{}",
                "fn", "printer()", "{", "println!(", ");", "}",
                "fn", "bytes()", "->", "&'static", "[u8]", "{", "b", "}",
            ],
        )
        self.assertEqual(string_texts(items), ['"x"', '"v={}"', '"ab"'])
        self.assertEqual(comment_texts(items), ["// 尾注释"])
        projection = " ".join(code_texts(items))
        self.assertNotIn('"', projection)
        self.assertNotIn("//", projection)
        self.assertNotIn("/*", projection)

    def test_t45_real_repo_sources_tokenize_cleanly(self) -> None:
        """B1/B2 真实面：仓库内 tracked 源文件全部可扫，切片保真且 code 不含字面量。"""
        files = repo_sources()
        self.assertGreaterEqual(len(files), 8, [path.as_posix() for path in files])
        present = {path.relative_to(REPO_ROOT).as_posix() for path in files}
        self.assertIn("crates/fml-error/tests/doc_lints.rs", present)
        self.assertIn("app/test/config_test.dart", present)
        for path in files:
            name = path.relative_to(REPO_ROOT).as_posix()
            with self.subTest(name=name):
                data = path.read_bytes()
                items = source_scan.tokens(path)
                self.assertTrue(items, name)
                self.assertEqual(stream_problems(items, data), [], name)
                projection = " ".join(code_texts(items))
                self.assertNotIn('"', projection, name)
                self.assertNotIn("//", projection, name)
                self.assertNotIn("/*", projection, name)

    def test_t46_multiline_then_unclosed_is_atomic_gate_error(self) -> None:
        """B1 原子性：先扫过合法多行字面量，后续未闭合仍只出单行 GATE-1，stdout 为空。"""
        self.write("a_good.rs", fixture("rust_multiline_string.rs").read_bytes())
        bad = self.write("z_bad.dart", "const s = 'a\n")
        argv = ["--root", str(self.root), "--suffix", ".rs", "--suffix", ".dart"]
        code, out, err = run_cli(argv)
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("z_bad.dart: GATE-1 字符串未闭合", err)
        self.assertNotIn("a_good.rs", err)
        bad.unlink()
        code, out, err = run_cli(argv)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(out.splitlines()), 1, out)
        self.assertTrue(out.startswith("a_good.rs: "), out)
        self.assertTrue(out.strip().endswith(" token(s)"), out)


if __name__ == "__main__":
    unittest.main()
