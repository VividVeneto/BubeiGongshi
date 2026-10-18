#!/usr/bin/env python3
"""生成 SADD 功能与代码模块映射（v4）。

输入：SADD/resources/feature-code-map.json 的 mapping 部分（人工维护），以及
SADD/00、09、10、11、12、13 的标题与表格（需求、R04 子项、验收 ID、目录树、
端口、实体、里程碑、待决事项与 ADR 编号）。

输出：SADD/14-功能与代码模块映射-v4.md、SADD/功能代码映射图.html、
SADD/diagrams/feature-module-map.svg、SADD/diagrams/backend-module-map.svg，
并回填 SADD/resources/feature-code-map.json 的 derived 部分（mapping 原样保留）。

用法：
    python tools/generate-feature-map.py           写出有变化的文件
    python tools/generate-feature-map.py --check   只在内存中生成并比对，不写盘

退出码：0 成功或无漂移；1 --check 发现漂移，或 diagrams/ 中有非生成文件；
2 输入无效或校验失败（不写任何文件）。

只用 Python 标准库（3.9 及以上）；不读取字体文件，同一输入在任何平台生成相同字节。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
SADD = ROOT / "SADD"
MAP_JSON = SADD / "resources" / "feature-code-map.json"
OUT_MD = SADD / "14-功能与代码模块映射-v4.md"
OUT_HTML = SADD / "功能代码映射图.html"
DIAGRAMS = SADD / "diagrams"
OUT_FEATURE_SVG = DIAGRAMS / "feature-module-map.svg"
OUT_BACKEND_SVG = DIAGRAMS / "backend-module-map.svg"
OUTPUT_PATHS = (OUT_MD, OUT_HTML, OUT_FEATURE_SVG, OUT_BACKEND_SVG, MAP_JSON)

SCHEMA = "bubei-feature-code-map/v4"
OWN_DOC = "14"
TITLE = "14 功能与代码模块映射 v4.0"
TAGLINE = "需求到计划代码模块、端口、实体与验收 ID 的映射，由 13、10 与映射数据生成"
REQUIRED_DOCS = ("00", "09", "10", "11", "12", "13")
TOP_KEYS = ("schema", "version", "date", "note", "mapping", "derived")
MAPPING_KEYS = (
    "docs", "layers", "modules", "forbidden_dependencies", "ports", "entities",
    "requirements", "r04_items", "client_surfaces", "externals", "server_features",
    "revision_log",
)

H2 = {
    "purpose": ("📋", "用途与生成方式"),
    "overview": ("🗺️", "功能—模块总览"),
    "modules": ("🧱", "代码模块与职责"),
    "ports": ("🔌", "端口与归属"),
    "entities": ("🧠", "学习域与公式语义实体"),
    "trace": ("🎯", "需求—模块—验收追踪"),
    "client": ("📱", "客户端功能面与平台差异"),
    "server": ("☁️", "服务端功能与外部依赖"),
    "milestones": ("🛤️", "里程碑落地顺序"),
    "repro": ("🔍", "生成、校验与复现"),
    "revisions": ("🔁", "v4 修订记录"),
}
H3 = {
    "deps": "依赖约束",
    "r04": "R04 功能近似子项落点",
    "tests": "验收 ID 反查",
    "externals": "外部依赖",
}
OWN_TITLES = {title for _, title in H2.values()} | set(H3.values()) | {TITLE}
HTML_SECTIONS = ("purpose", "overview", "modules", "ports", "entities", "trace",
                 "client", "server", "milestones", "repro")

BT = "\x60"
MD_FENCE = BT * 3

REQ_ID_RE = re.compile(r"(?:R|H|A|C)\d{2}", re.A)
R04_ID_RE = re.compile(r"R04\.[a-j]", re.A)
FAMILY_RE = re.compile(r"T-[A-Z]+", re.A)
TEST_ID_RE = re.compile(r"T-[A-Z]+(?:-\d{2})?", re.A)
SUB_ID_RE = re.compile(r"T-[A-Z]+-\d{2}", re.A)
D_ID_RE = re.compile(r"D-\d{2}", re.A)
ADR_ID_RE = re.compile(r"ADR-\d{3}", re.A)
RV_ID_RE = re.compile(r"RV-\d{2}", re.A)
CF_ID_RE = re.compile(r"CF-\d{2}", re.A)
SF_ID_RE = re.compile(r"SF-\d{2}", re.A)
GATE_RE = re.compile(r"\s*(M\d)", re.A)
MILESTONE_CELL_RE = re.compile(r"(M\d)\s+(.+)", re.A)
ROW_ID_RE = re.compile(
    r"(?<![A-Za-z0-9.-])(R\d{2}\.[a-j]|ADR-\d{3}|T-[A-Z]+-\d{2}|T-[A-Z]+|CF-\d{2}|SF-\d{2}"
    r"|D-\d{2}|[RHA]\d{2}|M\d)(?![A-Za-z0-9])",
    re.A,
)
# 以下检查与 tools/verify-sadd.mjs 一致
T_TOKEN_RE = re.compile(r"\bT-[A-Z]+(?:-\d{2})?\b", re.A)
D_TOKEN_RE = re.compile(r"\bD-\d{2}\b", re.A)
ADR_TOKEN_RE = re.compile(r"\bADR-\d{3}\b", re.A)
LINE_REF_RE = re.compile(r"(?<![0-9.:])((?:0[09]|1[0-4])(?:-[^\s:：|)]*\.md)?):([0-9]{1,4})(?![0-9:])")
LINE_ANCHOR_RE = re.compile(r"#L\d")
YOLO_RE = re.compile(r"ultralytics|yolov\d|\.pt\b|onnx.*yolo", re.I | re.A)
RETIRED_RE = re.compile(r"-v3\.md$|^0[1-8]-|历史-v2\.2")
CONTROL_RE = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
URL_RE = re.compile(r"https?://[^\s\"'<>)]+")
REF_RE = re.compile(r"(?:(?<![0-9A-Za-z])(00|09|1[0-4])[ \u00a0]?|(本文)[ \u00a0]?)?§[ \u00a0]*")
SEGMENT_RE = re.compile(r"([|；;。\n])")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
FENCE_RE = re.compile(r"^[ ]{0,3}(\x60{3,}|~{3,})")
SEP_RE = re.compile(r"^:?-{3,}:?$")
SVG_NS = "http://www.w3.org/2000/svg"
STRIP_CATS = {"So", "Sk", "Cf", "Mn", "Me", "Zs", "Cs", "Co"}


class InputError(Exception):
    def __init__(self, errors):
        super().__init__("; ".join(errors))
        self.errors = list(errors)


def rel(path):
    return path.relative_to(ROOT).as_posix()


# ------------------------------------------------------------------ Markdown

def scan_lines(text):
    """返回 ([(行号, 行, 是否在代码块内)], 代码块是否全部闭合)；代码块起止行算在块内。"""
    out, opener = [], None
    for no, line in enumerate(text.split("\n"), 1):
        m = FENCE_RE.match(line)
        if opener is None:
            if m:
                opener = m.group(1)
            out.append((no, line, opener is not None))
        else:
            mark = line.strip()
            if m and mark and set(mark) == {opener[0]} and len(mark) >= len(opener):
                opener = None
            out.append((no, line, True))
    return out, opener is None


def norm_heading(text):
    s = text.strip()
    i = 0
    while i < len(s) and unicodedata.category(s[i]) in STRIP_CATS:
        i += 1
    return s[i:].strip()


def split_row(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and s[i + 1:i + 2] == "|":
            cur.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def plain(cell):
    s = INLINE_LINK_RE.sub(r"\1", cell)
    s = s.replace(BT, "")
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def parse_tables(lines):
    blocks, cur, heading, cur_heading = [], [], "", ""
    for no, line, fenced in lines:
        if not fenced and line.lstrip().startswith("|"):
            if not cur:
                cur_heading = heading
            cur.append((no, line))
            continue
        if cur:
            blocks.append((cur_heading, cur))
            cur = []
        if not fenced:
            m = HEADING_RE.match(line)
            if m:
                heading = norm_heading(m.group(2))
    if cur:
        blocks.append((cur_heading, cur))
    tables = []
    for head, blk in blocks:
        if len(blk) < 2:
            continue
        sep = [c.replace(" ", "") for c in split_row(blk[1][1])]
        if not sep or not all(SEP_RE.match(c) for c in sep):
            continue
        header = [plain(c) for c in split_row(blk[0][1])]
        rows = [(no, [plain(c) for c in split_row(t)]) for no, t in blk[2:]]
        tables.append(NS(line=blk[0][0], header=header, rows=rows, heading=head))
    return tables


class Doc:
    def __init__(self, num, file, use, text):
        self.num, self.file, self.use = num, file, use
        self.text = text.replace("\r\n", "\n")
        self.lines, self.fences_closed = scan_lines(self.text)
        self.headings = []
        for no, line, fenced in self.lines:
            if not fenced:
                m = HEADING_RE.match(line)
                if m:
                    self.headings.append((len(m.group(1)), norm_heading(m.group(2)), no))
        h1 = [t for lvl, t, _ in self.headings if lvl == 1]
        self.h1 = h1[0] if len(h1) == 1 else ""
        self.titles = {t for _, t, _ in self.headings}
        self.tables = parse_tables(self.lines)

    def tables_with(self, header):
        return [t for t in self.tables if t.header == header]


def one_table(doc, header, errors):
    found = doc.tables_with(header)
    if len(found) != 1:
        errors.append(f"{doc.num}：表头为“{' | '.join(header)}”的表应恰有 1 张，实际 {len(found)} 张")
        return None
    return found[0]


def split_ids(cell):
    return [p for p in re.split(r"[、，,\s]+", cell.strip()) if p and p != "—"]


def report_dups(values, where, errors):
    seen, dups = set(), []
    for v in values:
        if v in seen and v not in dups:
            dups.append(v)
        seen.add(v)
    if dups:
        errors.append(f"{where}：编号重复 {'、'.join(map(str, dups))}")


def ids_in_tables(doc, pattern):
    found = []
    for t in doc.tables:
        for _, cells in t.rows:
            if cells and pattern.fullmatch(cells[0]) and cells[0] not in found:
                found.append(cells[0])
    return found


def id_ranges(ids):
    """把连续编号压缩成区间，如 R01–R31、H01–H02。"""
    groups = []
    for i in ids:
        m = re.fullmatch(r"(.*?)(\d+|[a-z])", i)
        if not m:
            groups.append((None, [(None, i)]))
            continue
        suf = m.group(2)
        key = (m.group(1), len(suf), suf.isdigit())
        val = int(suf) if suf.isdigit() else ord(suf)
        if groups and groups[-1][0] == key and val == groups[-1][1][-1][0] + 1:
            groups[-1][1].append((val, i))
        else:
            groups.append((key, [(val, i)]))
    return "、".join(items[0][1] if len(items) == 1 else f"{items[0][1]}–{items[-1][1]}"
                    for _, items in groups)


# ------------------------------------------------------------ 交叉引用校验

class Refs:
    """校验“文档号 §章节名”：章节名必须是目标文档某个标题的完整文字。"""

    def __init__(self, titles):
        self.titles = titles
        self.count = 0

    def resolve(self, text, default_doc, where, errors, rewrite=False):
        out = []
        for part in SEGMENT_RE.split(text):
            if len(part) == 1 and SEGMENT_RE.fullmatch(part):
                out.append(part)
            else:
                out.append(self._segment(part, default_doc, where, errors, rewrite))
        return "".join(out)

    def _segment(self, seg, default_doc, where, errors, rewrite):
        out, pos, last = [], 0, None
        for m in REF_RE.finditer(seg):
            explicit, this_doc = m.group(1), m.group(2)
            prefix = m.group(0)
            if explicit:
                doc = explicit
            elif this_doc or last is None:
                doc = default_doc
                if rewrite:
                    prefix = f"{default_doc} §"
            else:
                doc = last
            if self._match(seg[m.end():], doc) is None:
                snippet = seg[m.start():m.end() + 20].strip()
                errors.append(f"{where}：引用“{snippet}”在 {doc} 中找不到对应的章节标题")
            else:
                self.count += 1
            last = doc
            out.append(seg[pos:m.start()])
            out.append(prefix)
            pos = m.end()
        out.append(seg[pos:])
        return "".join(out)

    def _match(self, rest, doc):
        best = None
        for title in self.titles.get(doc, ()):
            if rest.startswith(title) and (best is None or len(title) > len(best)):
                nxt = rest[len(title):len(title) + 1]
                if not nxt or nxt.isspace() or unicodedata.category(nxt)[0] in "PS":
                    best = title
        return best


def undefined_tokens(text, defined_tests, d_ids, adr_ids):
    bad = []
    for t in T_TOKEN_RE.findall(text):
        base = t if FAMILY_RE.fullmatch(t) else t.rsplit("-", 1)[0]
        if t not in defined_tests and base not in defined_tests:
            bad.append(t)
    bad += [d for d in D_TOKEN_RE.findall(text) if d not in d_ids]
    bad += [a for a in ADR_TOKEN_RE.findall(text) if a not in adr_ids]
    return bad


def walk_strings(obj, where):
    if isinstance(obj, str):
        yield where, obj
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{where}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{where}.{k}")


# ------------------------------------------------------------ 读取输入

def check_record(rec, where, fields, errors, lists=(), bools=(), optional=()):
    if not isinstance(rec, dict):
        errors.append(f"{where}：需要对象")
        return False
    extra = set(rec) - set(fields) - set(optional)
    if extra:
        errors.append(f"{where}：未知字段 {'、'.join(sorted(extra))}")
    ok = True
    for f in fields:
        v = rec.get(f)
        if f in lists:
            good = isinstance(v, list) and all(isinstance(x, str) and x for x in v) and len(set(v)) == len(v)
            need = "不重复的字符串数组"
        elif f in bools:
            good, need = isinstance(v, bool), "布尔值"
        else:
            good, need = isinstance(v, str) and bool(v.strip()), "非空字符串"
        if not good:
            errors.append(f"{where}.{f}：需要{need}")
            ok = False
    for f in optional:
        if f in rec and not (isinstance(rec[f], str) and rec[f].strip()):
            errors.append(f"{where}.{f}：需要非空字符串")
            ok = False
    return ok


def records(mp, key, fields, errors, **kw):
    v = mp.get(key)
    if not isinstance(v, list) or not v:
        errors.append(f"mapping.{key}：需要非空对象数组")
        return []
    return [r for i, r in enumerate(v) if check_record(r, f"mapping.{key}[{i}]", fields, errors, **kw)]


def keyed(mp, key, fields, errors, **kw):
    v = mp.get(key)
    if not isinstance(v, dict) or not v:
        errors.append(f"mapping.{key}：需要非空对象")
        return {}
    return {k: r for k, r in v.items() if check_record(r, f"mapping.{key}.{k}", fields, errors, **kw)}


def load_json():
    errors = []
    try:
        data = json.loads(MAP_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError([f"{rel(MAP_JSON)}：JSON 无效（{exc}）"])
    if not isinstance(data, dict):
        raise InputError([f"{rel(MAP_JSON)}：顶层必须是对象"])
    extra = set(data) - set(TOP_KEYS)
    if extra:
        errors.append(f"{rel(MAP_JSON)}：未知顶层字段 {'、'.join(sorted(extra))}")
    if data.get("schema") != SCHEMA:
        errors.append(f"{rel(MAP_JSON)}：schema 必须是 {SCHEMA}")
    for key in ("version", "note"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{rel(MAP_JSON)}.{key}：需要非空字符串")
    if not isinstance(data.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["date"]):
        errors.append(f"{rel(MAP_JSON)}.date：需要 YYYY-MM-DD")
    mp = data.get("mapping")
    if not isinstance(mp, dict):
        raise InputError(errors + [f"{rel(MAP_JSON)}：缺少 mapping 对象"])
    missing = [k for k in MAPPING_KEYS if k not in mp]
    extra = sorted(set(mp) - set(MAPPING_KEYS))
    if missing:
        errors.append(f"mapping：缺少 {'、'.join(missing)}")
    if extra:
        errors.append(f"mapping：未知字段 {'、'.join(extra)}")
    docs = records(mp, "docs", ("id", "file", "use"), errors)
    ids = [d["id"] for d in docs]
    report_dups(ids, "mapping.docs", errors)
    for need in REQUIRED_DOCS:
        if need not in ids:
            errors.append(f"mapping.docs：缺少文档 {need}")
    if errors:
        raise InputError(errors)
    return data


def load_docs(entries, errors):
    docs = {}
    for e in entries:
        name = e["file"]
        if "/" in name or "\\" in name or RETIRED_RE.search(name):
            errors.append(f"mapping.docs {e['id']}：文件名 {name} 无效或已退役")
            continue
        path = SADD / name
        if not path.is_file():
            errors.append(f"mapping.docs {e['id']}：找不到 SADD/{name}")
            continue
        doc = Doc(e["id"], name, e["use"], path.read_text(encoding="utf-8"))
        if not doc.h1:
            errors.append(f"SADD/{name}：需要恰好一个一级标题")
        elif not doc.h1.startswith(e["id"] + " "):
            errors.append(f"SADD/{name}：一级标题应以“{e['id']} ”开头")
        if not doc.fences_closed:
            errors.append(f"SADD/{name}：代码块未闭合")
        docs[e["id"]] = doc
    return docs


def parse_13(doc, errors):
    out = NS(requirements=[], r04=[], tests=[], defined=set(), subs={})
    req_t = one_table(doc, ["ID", "需求", "设计定位", "验收 ID"], errors)
    r04_t = one_table(doc, ["子项", "内容", "设计定位", "验收 ID"], errors)
    sum_t = one_table(doc, ["ID", "验收对象", "所在章节", "最早门槛"], errors)
    if sum_t:
        for no, c in sum_t.rows:
            if len(c) != 4 or not FAMILY_RE.fullmatch(c[0]):
                errors.append(f"13 §{sum_t.heading} 第 {no} 行：需要 4 列且编号形如 T-XXX")
                continue
            out.tests.append(NS(id=c[0], object=c[1], section=c[2], gate=c[3]))
    families = [t.id for t in out.tests]
    report_dups(families, "13 验收 ID 总表", errors)
    fam = set(families)
    for t in doc.tables:
        for no, c in t.rows:
            if c and TEST_ID_RE.fullmatch(c[0]):
                out.defined.add(c[0])
                if SUB_ID_RE.fullmatch(c[0]):
                    base = c[0].rsplit("-", 1)[0]
                    if base not in fam:
                        errors.append(f"13 第 {no} 行：子编号 {c[0]} 所属的 {base} 不在验收 ID 总表中")
                    subs = out.subs.setdefault(base, [])
                    if c[0] not in subs:
                        subs.append(c[0])

    def tests_of(cell, where):
        ids = split_ids(cell)
        if not ids:
            errors.append(f"{where}：没有验收 ID")
        for i in ids:
            if not FAMILY_RE.fullmatch(i):
                errors.append(f"{where}：验收 ID“{i}”格式不符")
            elif i not in fam:
                errors.append(f"{where}：验收 ID {i} 不在 13 的验收 ID 总表中")
        return ids

    if req_t:
        for no, c in req_t.rows:
            if len(c) != 4 or not REQ_ID_RE.fullmatch(c[0]):
                errors.append(f"13 §{req_t.heading} 第 {no} 行：需要 4 列且编号形如 R01")
                continue
            out.requirements.append(NS(id=c[0], title=c[1], design=c[2], tests=tests_of(c[3], f"13 {c[0]}")))
    if r04_t:
        for no, c in r04_t.rows:
            if len(c) != 4 or not R04_ID_RE.fullmatch(c[0]):
                errors.append(f"13 §{r04_t.heading} 第 {no} 行：需要 4 列且编号形如 R04.a")
                continue
            title = c[1].split("：", 1)[0].strip() if "：" in c[1] else c[1]
            out.r04.append(NS(id=c[0], title=title, content=c[1], design=c[2],
                              tests=tests_of(c[3], f"13 {c[0]}")))
    report_dups([r.id for r in out.requirements], "13 需求", errors)
    report_dups([r.id for r in out.r04], "13 R04 子项", errors)
    if out.r04 and "R04" not in {r.id for r in out.requirements}:
        errors.append("13：有 R04 子项但没有 R04 需求")
    return out


def tree_leaves(lines):
    paths, stack = [], []
    for raw in lines:
        body = raw.split("#", 1)[0].rstrip()
        if not body.strip():
            continue
        indent = len(body) - len(body.lstrip(" "))
        tokens = body.split()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else ""
        paths.extend(parent + tok for tok in tokens)
        if len(tokens) == 1 and tokens[0].endswith("/"):
            stack.append((indent, parent + tokens[0]))
    return sorted(p for p in set(paths) if not any(q != p and q.startswith(p) for q in paths))


def entity_name(cell):
    return re.sub(r"（[^）]*）|\([^)]*\)", "", cell).strip()


def parse_10(doc, errors):
    out = NS(tree=[], ports=[], semantic=[], learning=[], milestones=[])
    start = next((no for _, t, no in doc.headings if t == "推荐技术栈与初始模块"), None)
    if start is None:
        errors.append("10：找不到“推荐技术栈与初始模块”标题")
    else:
        end = next((no for _, _, no in doc.headings if no > start), len(doc.lines) + 1)
        block, inside = [], False
        for no, line, fenced in doc.lines:
            if no <= start or no >= end:
                continue
            if fenced and FENCE_RE.match(line):
                if inside:
                    break
                inside = True
                continue
            if inside:
                block.append(line)
        if not block:
            errors.append("10 §推荐技术栈与初始模块：找不到目录树代码块")
        out.tree = tree_leaves(block)
    t = one_table(doc, ["端口", "归属", "输入/输出", "失败与约束"], errors)
    if t:
        out.ports = [c[0] for _, c in t.rows if c and c[0]]
    t = one_table(doc, ["实体", "关键字段"], errors)
    if t:
        out.semantic = [entity_name(c[0]) for _, c in t.rows if c and c[0]]
    t = one_table(doc, ["实体", "关键字段与规则"], errors)
    if t:
        out.learning = [entity_name(c[0]) for _, c in t.rows if c and c[0]]
    t = one_table(doc, ["阶段", "输出", "出口条件"], errors)
    if t:
        for no, c in t.rows:
            m = MILESTONE_CELL_RE.fullmatch(c[0]) if c else None
            if not m or len(c) != 3:
                errors.append(f"10 §{t.heading} 第 {no} 行：阶段应形如“M0 名称”且有 3 列")
                continue
            out.milestones.append(NS(id=m.group(1), name=m.group(2).strip(), output=c[1], exit=c[2]))
        report_dups([ms.id for ms in out.milestones], "10 里程碑", errors)
    return out


# ------------------------------------------------------------ 模型与校验

def closure(deps, start):
    seen, todo = set(), list(deps.get(start, []))
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n)
            todo.extend(deps.get(n, []))
    return seen


def find_cycle(deps):
    color = {n: 0 for n in deps}
    for root in deps:
        if color[root]:
            continue
        color[root] = 1
        stack, path = [(root, iter(deps[root]))], [root]
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = 2
                stack.pop()
                path.pop()
            elif nxt in color and color[nxt] == 1:
                return path[path.index(nxt):] + [nxt]
            elif nxt in color and color[nxt] == 0:
                color[nxt] = 1
                stack.append((nxt, iter(deps[nxt])))
                path.append(nxt)
    return None


def first_gate(gate, milestone_ids):
    m = GATE_RE.match(gate)
    return m.group(1) if m and m.group(1) in milestone_ids else None


def build_model(data, docs, errors):
    mp = data["mapping"]
    f13 = parse_13(docs["13"], errors)
    f10 = parse_10(docs["10"], errors)
    M = NS(date=data["date"], version=data["version"], f13=f13, f10=f10, md_refs=0)
    M.d_ids = set(ids_in_tables(docs["00"], D_ID_RE))
    M.adr_ids = set(ids_in_tables(docs["09"], ADR_ID_RE))
    M.rv_ids = ids_in_tables(docs["09"], RV_ID_RE)
    M.doc_list = [NS(id=d.num, file=d.file, use=d.use, h1=d.h1) for d in docs.values()]
    titles = {num: doc.titles for num, doc in docs.items()}
    titles[OWN_DOC] = set(OWN_TITLES)
    M.refs = Refs(titles)

    layers = records(mp, "layers", ("id", "title", "short"), errors)
    modules = records(mp, "modules", ("id", "layer", "path", "responsibility", "io_rule", "depends_on", "refs"),
                      errors, lists=("depends_on",))
    forbidden = records(mp, "forbidden_dependencies", ("from", "to", "transitive", "rule"), errors,
                        lists=("from", "to"), bools=("transitive",))
    ports = records(mp, "ports", ("id", "owners", "contract"), errors, lists=("owners",), optional=("label",))
    entities = records(mp, "entities", ("id", "modules", "compute", "store", "sync", "reqs", "refs"), errors,
                       lists=("modules", "reqs"))
    req_map = keyed(mp, "requirements", ("modules", "ports", "milestone", "note"), errors, lists=("modules", "ports"))
    r04_map = keyed(mp, "r04_items", ("modules", "entities", "ports", "note"), errors,
                    lists=("modules", "entities", "ports"))
    cfs = records(mp, "client_surfaces", ("id", "title", "reqs", "modules", "android", "windows", "ohos",
                                          "tests", "refs"), errors, lists=("reqs", "modules", "tests"))
    externals = records(mp, "externals", ("id", "label", "note"), errors)
    sfs = records(mp, "server_features", ("id", "title", "contract", "client_modules", "externals", "reqs",
                                          "tests", "refs"), errors, lists=("client_modules", "externals", "reqs",
                                                                           "tests"))
    revs = records(mp, "revision_log", ("ids", "landing"), errors)
    if errors:
        raise InputError(errors)

    layer_ids = [l["id"] for l in layers]
    mod_ids = [m["id"] for m in modules]
    port_ids = [p["id"] for p in ports]
    ent_ids = [e["id"] for e in entities]
    ext_ids = [e["id"] for e in externals]
    for values, where in ((layer_ids, "mapping.layers"), (mod_ids, "mapping.modules"), (port_ids, "mapping.ports"),
                          (ent_ids, "mapping.entities"), (ext_ids, "mapping.externals"),
                          ([c["id"] for c in cfs], "mapping.client_surfaces"),
                          ([s["id"] for s in sfs], "mapping.server_features")):
        report_dups(values, where, errors)
    mods, ports_set = set(mod_ids), set(port_ids)
    req_ids = [r.id for r in f13.requirements]
    req_set = set(req_ids)
    fam = {t.id for t in f13.tests}
    milestone_ids = [ms.id for ms in f10.milestones]
    owners = {p["id"]: p["owners"] for p in ports}

    def unknown(values, known, where, what):
        for v in values:
            if v not in known:
                errors.append(f"{where}：未知{what} {v}")

    def owner_check(port_list, module_list, where):
        for p in port_list:
            if p in owners and not set(owners[p]) & set(module_list):
                errors.append(f"{where}：端口 {p} 的归属模块（{'、'.join(owners[p])}）都不在该项的模块中")

    for m in modules:
        w = f"mapping.modules {m['id']}"
        if m["layer"] not in layer_ids:
            errors.append(f"{w}.layer：未知层 {m['layer']}")
        unknown(m["depends_on"], mods - {m["id"]}, w + ".depends_on", "模块")
    for layer in layers:
        if not any(m["layer"] == layer["id"] for m in modules):
            errors.append(f"mapping.layers {layer['id']}：没有模块")
    for r in forbidden:
        unknown(r["from"], mods, f"mapping.forbidden_dependencies“{r['rule']}”.from", "模块")
        unknown([x for x in r["to"] if x != "*"], mods, f"mapping.forbidden_dependencies“{r['rule']}”.to", "模块")
    for p in ports:
        if not p["owners"]:
            errors.append(f"mapping.ports {p['id']}.owners：不能为空")
        unknown(p["owners"], mods, f"mapping.ports {p['id']}.owners", "模块")
    for e in entities:
        w = f"mapping.entities {e['id']}"
        if not e["modules"] or not e["reqs"]:
            errors.append(f"{w}：modules 与 reqs 不能为空")
        unknown(e["modules"], mods, w + ".modules", "模块")
        unknown(e["reqs"], req_set, w + ".reqs", "需求")
    missing = [i for i in req_ids if i not in req_map]
    extra = [i for i in req_map if i not in req_set]
    if missing:
        errors.append(f"mapping.requirements：缺少 13 中的 {'、'.join(missing)}")
    if extra:
        errors.append(f"mapping.requirements：13 中没有 {'、'.join(extra)}")
    for rid, r in req_map.items():
        w = f"mapping.requirements {rid}"
        if not r["modules"]:
            errors.append(f"{w}.modules：不能为空")
        unknown(r["modules"], mods, w + ".modules", "模块")
        unknown(r["ports"], ports_set, w + ".ports", "端口")
        if r["milestone"] not in milestone_ids:
            errors.append(f"{w}.milestone：{r['milestone']} 不在 10 的里程碑表中")
        owner_check(r["ports"], r["modules"], w)
    r04_ids = [x.id for x in f13.r04]
    missing = [i for i in r04_ids if i not in r04_map]
    extra = [i for i in r04_map if i not in r04_ids]
    if missing:
        errors.append(f"mapping.r04_items：缺少 13 中的 {'、'.join(missing)}")
    if extra:
        errors.append(f"mapping.r04_items：13 中没有 {'、'.join(extra)}")
    parent = req_map.get("R04", {"modules": [], "ports": []})
    for xid, x in r04_map.items():
        w = f"mapping.r04_items {xid}"
        if not x["modules"] or not x["entities"]:
            errors.append(f"{w}：modules 与 entities 不能为空")
        unknown(x["modules"], mods, w + ".modules", "模块")
        unknown(x["entities"], set(ent_ids), w + ".entities", "实体")
        unknown(x["ports"], ports_set, w + ".ports", "端口")
        owner_check(x["ports"], x["modules"], w)
        unknown(x["modules"], set(parent["modules"]), w + ".modules", "（不在 R04 映射中的）模块")
        unknown(x["ports"], set(parent["ports"]), w + ".ports", "（不在 R04 映射中的）端口")
    tests_of_req = {r.id: set(r.tests) for r in f13.requirements}
    for group, idre, mod_key in ((cfs, CF_ID_RE, "modules"), (sfs, SF_ID_RE, "client_modules")):
        for c in group:
            w = f"mapping {c['id']}"
            if not idre.fullmatch(c["id"]):
                errors.append(f"{w}：编号格式不符")
            if not c["reqs"] or not c[mod_key] or not c["tests"]:
                errors.append(f"{w}：reqs、{mod_key} 与 tests 不能为空")
            unknown(c["reqs"], req_set, w + ".reqs", "需求")
            unknown(c[mod_key], mods, f"{w}.{mod_key}", "模块")
            allowed = set().union(*(tests_of_req.get(r, set()) for r in c["reqs"])) if c["reqs"] else set()
            for t in c["tests"]:
                if t not in fam:
                    errors.append(f"{w}.tests：{t} 不在 13 的验收 ID 总表中")
                elif t not in allowed:
                    errors.append(f"{w}.tests：{t} 不是所映射需求（{'、'.join(c['reqs'])}）在 13 中的验收 ID")
    for s in sfs:
        unknown(s["externals"], set(ext_ids), f"mapping {s['id']}.externals", "外部依赖")

    # 与 10 交叉比对
    tree = set(f10.tree) - {"SADD/"}
    paths = {m["path"] for m in modules}
    if f10.tree and tree != paths:
        if tree - paths:
            errors.append(f"10 目录树中有、映射中没有的路径：{'、'.join(sorted(tree - paths))}")
        if paths - tree:
            errors.append(f"映射中有、10 目录树中没有的路径：{'、'.join(sorted(paths - tree))}")
    names = {p.get("label", p["id"]) for p in ports}
    if f10.ports and set(f10.ports) != names:
        if set(f10.ports) - names:
            errors.append(f"10 §端口契约 中有、映射中没有的端口：{'、'.join(sorted(set(f10.ports) - names))}")
        if names - set(f10.ports):
            errors.append(f"映射中有、10 §端口契约 中没有的端口：{'、'.join(sorted(names - set(f10.ports)))}")
    parts = {part.strip() for e in ent_ids for part in e.split("/")}
    missing = [n for n in f10.learning if n not in parts]
    if missing:
        errors.append(f"10 §学习域模型 中的实体未映射：{'、'.join(missing)}")
    known_entities = set(f10.semantic) | set(f10.learning)
    unknown(sorted(parts), known_entities, "mapping.entities", "（10 实体表中没有的）实体名")

    # 依赖图
    deps = {m["id"]: [d for d in m["depends_on"] if d in mods] for m in modules}
    cycle = find_cycle(deps)
    if cycle:
        errors.append(f"mapping.modules：循环依赖 {' → '.join(cycle)}")
    for r in forbidden:
        for f in r["from"]:
            reach = closure(deps, f) if r["transitive"] else set(deps.get(f, []))
            bad = reach if "*" in r["to"] else reach & set(r["to"])
            if bad:
                errors.append(f"依赖约束“{r['rule']}”被违反：{f} → {'、'.join(sorted(bad))}")
    by_layer = {lid: [m for m in modules if m["layer"] == lid] for lid in layer_ids}
    pos = {}
    for li, lid in enumerate(layer_ids):
        for i, m in enumerate(by_layer[lid]):
            pos[m["id"]] = (li, i)
    for m in modules:
        for d in deps[m["id"]]:
            (la, ia), (lb, ib) = pos[m["id"]], pos[d]
            if not (lb == la + 1 or (lb == la and abs(ia - ib) == 1)):
                errors.append(f"依赖 {m['id']} → {d}：总览图只画相邻层或同层相邻模块，请调整层或模块顺序")

    # 13 文字：补全省略文档号的章节引用，并校验
    for r in f13.requirements:
        r.title = M.refs.resolve(r.title, "13", f"13 {r.id} 需求", errors, rewrite=True)
        r.design = M.refs.resolve(r.design, "13", f"13 {r.id} 设计定位", errors, rewrite=True)
    for x in f13.r04:
        x.content = M.refs.resolve(x.content, "13", f"13 {x.id} 内容", errors, rewrite=True)
        x.title = x.content.split("：", 1)[0].strip() if "：" in x.content else x.content
        x.design = M.refs.resolve(x.design, "13", f"13 {x.id} 设计定位", errors, rewrite=True)
    for t in f13.tests:
        t.object = M.refs.resolve(t.object, "13", f"13 {t.id} 验收对象", errors, rewrite=True)
        t.section = M.refs.resolve(t.section, "13", f"13 {t.id} 所在章节", errors, rewrite=True)
        t.gate = M.refs.resolve(t.gate, "13", f"13 {t.id} 最早门槛", errors, rewrite=True)
        g = GATE_RE.match(t.gate)
        if g and g.group(1) not in milestone_ids:
            errors.append(f"13 {t.id}：最早门槛 {g.group(1)} 不在 10 的里程碑表中")
    for where, s in walk_strings(mp, "mapping"):
        M.refs.resolve(s, OWN_DOC, where, errors)
        bad = undefined_tokens(s, f13.defined, M.d_ids, M.adr_ids)
        if bad:
            errors.append(f"{where}：未定义的编号 {'、'.join(bad)}")

    # 合并视图与反查
    M.layers, M.modules, M.forbidden, M.ports = layers, modules, forbidden, ports
    M.entities, M.cfs, M.externals, M.sfs, M.revs = entities, cfs, externals, sfs, revs
    M.milestones = f10.milestones
    M.layer_short = {l["id"]: l["short"] for l in layers}
    M.modules_by_layer = by_layer
    M.module_path = {m["id"]: m["path"] for m in modules}
    M.port_name = {p["id"]: p.get("label", p["id"]) for p in ports}
    M.ext_label = {e["id"]: e["label"] for e in externals}
    M.subs = f13.subs
    M.tests = f13.tests
    M.reqs = []
    for r in f13.requirements:
        mm = req_map.get(r.id, {"modules": [], "ports": [], "milestone": "", "note": ""})
        M.reqs.append(NS(id=r.id, title=r.title, design=r.design, tests=r.tests, modules=mm["modules"],
                         ports=mm["ports"], milestone=mm["milestone"], note=mm["note"]))
    M.r04 = []
    for x in f13.r04:
        mm = r04_map.get(x.id, {"modules": [], "entities": [], "ports": [], "note": ""})
        M.r04.append(NS(id=x.id, title=x.title, content=x.content, design=x.design, tests=x.tests,
                        modules=mm["modules"], entities=mm["entities"], ports=mm["ports"], note=mm["note"]))
    M.module_reqs = {m: [r.id for r in M.reqs if m in r.modules] for m in mod_ids}
    M.module_r04 = {m: [x.id for x in M.r04 if m in x.modules] for m in mod_ids}
    M.port_reqs = {p: [r.id for r in M.reqs if p in r.ports] for p in port_ids}
    M.port_r04 = {p: [x.id for x in M.r04 if p in x.ports] for p in port_ids}
    M.entity_r04 = {e: [x.id for x in M.r04 if e in x.entities] for e in ent_ids}
    M.test_reqs = {t.id: [r.id for r in M.reqs if t.id in r.tests] for t in M.tests}
    M.test_r04 = {t.id: [x.id for x in M.r04 if t.id in x.tests] for t in M.tests}
    M.test_cf = {t.id: [c["id"] for c in cfs if t.id in c["tests"]] for t in M.tests}
    M.test_sf = {t.id: [s["id"] for s in sfs if t.id in s["tests"]] for t in M.tests}
    M.ms_reqs = {ms.id: [r.id for r in M.reqs if r.milestone == ms.id] for ms in M.milestones}
    M.ms_tests = {ms.id: [t.id for t in M.tests if first_gate(t.gate, milestone_ids) == ms.id]
                  for ms in M.milestones}
    M.loose_tests = [t for t in M.tests if first_gate(t.gate, milestone_ids) is None]
    M.ext_users = {e: [s["id"] for s in sfs if e in s["externals"]] for e in ext_ids}
    for m in mod_ids:
        if not M.module_reqs[m]:
            errors.append(f"mapping.modules {m}：没有任何需求引用该模块")
    for p in port_ids:
        if not M.port_reqs[p]:
            errors.append(f"mapping.ports {p}：没有任何需求引用该端口")
    for e in ext_ids:
        if not M.ext_users[e]:
            errors.append(f"mapping.externals {e}：没有服务端功能使用")
    sf_index = {s["id"]: i for i, s in enumerate(sfs)}

    def bary_order(items, users):
        first = {}
        for s in sfs:
            for it in users(s):
                first.setdefault(it, len(first))
        def key(it):
            idx = [sf_index[s["id"]] for s in sfs if it in users(s)]
            return (sum(idx) / len(idx), first[it])
        return sorted(items, key=key)

    clients = []
    for s in sfs:
        for c in s["client_modules"]:
            if c not in clients:
                clients.append(c)
    M.backend_clients = bary_order(clients, lambda s: s["client_modules"])
    M.backend_externals = bary_order([e for e in ext_ids if M.ext_users[e]], lambda s: s["externals"])
    return M


def build_derived(M):
    return {
        "counts": counts(M),
        "requirements": [{"id": r.id, "title": r.title, "design": r.design, "tests": r.tests} for r in M.reqs],
        "r04_items": [{"id": x.id, "title": x.title, "content": x.content, "design": x.design, "tests": x.tests}
                      for x in M.r04],
        "tests": [{"id": t.id, "object": t.object, "section": t.section, "gate": t.gate,
                   "sub_ids": M.subs.get(t.id, []), "requirements": M.test_reqs[t.id],
                   "r04_items": M.test_r04[t.id], "client_surfaces": M.test_cf[t.id],
                   "server_features": M.test_sf[t.id]} for t in M.tests],
        "milestones": [{"id": ms.id, "name": ms.name, "requirements": M.ms_reqs[ms.id],
                        "first_tests": M.ms_tests[ms.id]} for ms in M.milestones],
        "module_requirements": {m["id"]: M.module_reqs[m["id"]] for m in M.modules},
        "port_requirements": {p["id"]: M.port_reqs[p["id"]] for p in M.ports},
    }


def counts(M):
    return {
        "requirements": len(M.reqs), "r04_items": len(M.r04), "tests": len(M.tests),
        "sub_ids": sum(len(v) for v in M.subs.values()), "modules": len(M.modules), "ports": len(M.ports),
        "entities": len(M.entities), "client_surfaces": len(M.cfs), "server_features": len(M.sfs),
        "externals": len(M.externals),
    }


def stats_text(M):
    c = counts(M)
    return (f"{c['requirements']} 条需求、{c['r04_items']} 个 R04 子项、{c['tests']} 个验收 ID（另有 {c['sub_ids']} 个子编号）、"
            f"{c['modules']} 个计划模块、{c['ports']} 个端口、{c['entities']} 个实体、{c['client_surfaces']} 个客户端功能面、"
            f"{c['server_features']} 个服务端功能、{c['externals']} 个外部依赖")


# ------------------------------------------------------------ 共用文字

def prose(M):
    return {
        "overview": (f"计划模块分为 {len(M.layers)} 层。实线箭头是编译期依赖，只允许自上而下；同层箭头是同一层内的装配关系；"
                     "虚线框中的模块不在客户端依赖链内。框内“需求”由需求映射反查得到。"),
        "modules": ("目录与职责同 10 §推荐技术栈与初始模块、§分层与职责归属。Rust crate 不直接做 I/O：网络、文件选择、通知与平台密钥"
                    "由 platform_io 执行核心下发的命令（09 ADR-009）。“承载需求”由需求映射反查得到。"),
        "deps_tail": ("生成器按以上规则检查映射数据中的 depends_on，并拒绝循环依赖；实现阶段由 CI 检查 crate 依赖图与 Dart 包导入"
                      "（10 §分层与职责归属、§错误码与可维护性度量）。"),
        "ports": "端口名与归属同 10 §端口契约，契约摘要只列输入与输出，失败语义以 10 为准；“用到的需求”与“用到的 R04 子项”由映射反查得到。",
        "entities": ("实体名同 10 §单一语义源、§学习域模型，不使用别名；存储表同 10 §本地数据模型，合并规则同 11 §同步协议；"
                     "“R04 子项”由子项映射反查得到。"),
        "trace": ("需求、设计定位与验收 ID 原样取自 13 §原始需求追踪，13 中以“本文”指代自身的章节引用在此写作以 13 开头；"
                  "模块、端口、落地里程碑与说明来自映射数据。落地里程碑指主要功能首次交付的阶段，各验收 ID 的最早门槛见 §验收 ID 反查。"),
        "r04": ("子项内容、设计定位与验收 ID 取自 13 §R04 功能近似子项，条款原文见 00 §功能近似条款（R04 子项）；"
                "实体、模块、端口与说明来自映射数据。"),
        "tests": ("验收对象、所在章节与最早门槛取自 13 §验收 ID 总表与里程碑，子编号是 13 中定义的细分用例；"
                  "需求、R04 子项、客户端功能面与服务端功能由映射反查得到。"),
        "client": ("Android 与 Windows 共用 Flutter 界面与 Rust 核心，平台差异集中在 platform_io 与安装分发"
                   "（10 §平台实现与生命周期）；鸿蒙为预留路线，M0 纵切后定路线（00 D-04）。功能面的验收 ID 只取所映射需求在 13 中的验收 ID。"),
        "server": ("server/ 是模块化单体（09 ADR-003），同步只接收密文（09 ADR-004），游客数据不进入任何上传端口。"
                   "下图左列是调用服务端的客户端模块，右列是外部依赖。"),
        "milestones": ("阶段名同 10 §版本、里程碑与交付；“落地的需求”按映射中的落地里程碑归类，"
                       "“首次提交证据的验收 ID”按 13 最早门槛中的第一个阶段归类。"),
        "loose": ("不按单一阶段归类的验收 ID：" + "；".join(f"{t.id}（{t.gate}）" for t in M.loose_tests) + "。")
        if M.loose_tests else "",
    }


def feature_summary(M):
    layers = "；".join(f"{l['short']}：{'、'.join(m['id'] for m in M.modules_by_layer[l['id']])}" for l in M.layers)
    edges = "、".join(f"{m['id']} → {d}" for m in M.modules for d in m["depends_on"])
    return f"计划模块自上而下分层，{layers}。编译期依赖：{edges}。"


def backend_summary(M):
    parts = []
    for s in M.sfs:
        ext = "、".join(M.ext_label[e] for e in s["externals"])
        parts.append(f"{s['id']} {s['title']}，调用方 {'、'.join(s['client_modules'])}，外部依赖 {ext}")
    return "服务端功能与外部依赖：" + "；".join(parts) + "。"


# ------------------------------------------------------------ Markdown 输出

def ids(items):
    return "、".join(items) if items else "—"


def mdc(text):
    s = (text or "").replace("|", "\\|").replace("\n", " ").strip()
    return s or "—"


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(mdc(c) for c in r) + " |" for r in rows]
    return out


def mid(prefix, value):
    return prefix + "_" + re.sub(r"[^0-9A-Za-z]", "_", value)


def mlabel(text):
    return text.replace('"', "＂")


def render_md(M, stats):
    P = prose(M)
    L = []
    add = L.append

    def h2(key):
        add(f"## {H2[key][0]} {H2[key][1]}")
        add("")

    def h3(key):
        add(f"### {H3[key]}")
        add("")

    def table(header, rows):
        L.extend(md_table(header, rows))
        add("")

    add(f"# {TITLE}")
    add("")
    add(f"_BubeiGongshi · {M.date} · {TAGLINE}_")
    add("")
    add("---")
    add("")

    h2("purpose")
    add("- 本文说明每条需求由哪些计划模块、端口和实体承载、以哪些验收 ID 证明，并给出客户端功能面、服务端功能与里程碑落地顺序。")
    add("- 需求原文、设计定位与验收 ID 取自 13 §原始需求追踪、§R04 功能近似子项 与 §验收 ID 总表与里程碑；模块划分、依赖方向与端口以"
        " 10 §分层与职责归属、§推荐技术栈与初始模块、§端口契约 为准。本文与 13、10 不一致时以 13、10 为准，修改映射数据后重新生成。")
    add("- 目录树中的路径都是未来实现规划；仓库当前只有架构文档与工具，不含应用源码。")
    add("- 本文、[功能代码映射图.html](功能代码映射图.html)、[diagrams/feature-module-map.svg](diagrams/feature-module-map.svg)、"
        "[diagrams/backend-module-map.svg](diagrams/backend-module-map.svg) 以及 [resources/feature-code-map.json]"
        f"(resources/feature-code-map.json) 的 derived 部分由 {BT}tools/generate-feature-map.py{BT} 生成，不要手改；"
        "映射关系只在该 JSON 的 mapping 部分维护。")
    line = (f"- 编号：{id_ranges([r.id for r in M.reqs])} 与 {id_ranges([x.id for x in M.r04])} 同 13，其中 A 编号是验收约束")
    if M.rv_ids:
        line += f"，与 09 的复审缺陷编号 {id_ranges(M.rv_ids)} 无关"
    line += (f"；{id_ranges([c['id'] for c in M.cfs])} 是客户端功能面，{id_ranges([s['id'] for s in M.sfs])} 是服务端功能，"
             "只在本文与映射图中使用；D 编号是 00 §待决事项与默认策略 中的待决事项，ADR 编号是 09 §架构决策（ADR） 中的决策。")
    add(line)
    add("")
    table(["文档", "本文使用的内容"], [[f"[{d.h1}]({d.file})", d.use] for d in M.doc_list])

    h2("overview")
    add(P["overview"])
    add("")
    add(MD_FENCE + "mermaid")
    add("flowchart TB")
    add("  accTitle: 功能—模块总览")
    add("  accDescr: " + feature_summary(M))
    for layer in M.layers:
        add(f'  subgraph {mid("L", layer["id"])} ["{mlabel(layer["title"])}"]')
        for m in M.modules_by_layer[layer["id"]]:
            add(f'    {mid("M", m["id"])}["{mlabel(m["id"])}"]')
        add("  end")
    for m in M.modules:
        for d in m["depends_on"]:
            add(f"  {mid('M', m['id'])} --> {mid('M', d)}")
    add(MD_FENCE)
    add("")
    add("![功能—模块总览图：分层计划模块、编译期依赖与承载需求](diagrams/feature-module-map.svg)")
    add("")

    h2("modules")
    add(P["modules"])
    add("")
    table(["模块", "层", "计划路径", "职责", "I/O 规则", "直接依赖", "承载需求", "设计定位"],
          [[m["id"], M.layer_short[m["layer"]], f"{BT}{m['path']}{BT}", m["responsibility"], m["io_rule"],
            ids(m["depends_on"]), ids(M.module_reqs[m["id"]]), m["refs"]] for m in M.modules])
    h3("deps")
    for r in M.forbidden:
        add(f"- {r['rule']}（{'含传递依赖' if r['transitive'] else '只限直接依赖'}）。")
    add("- " + P["deps_tail"])
    add("")

    h2("ports")
    add(P["ports"])
    add("")
    table(["端口", "归属模块", "契约摘要", "用到的需求", "用到的 R04 子项"],
          [[M.port_name[p["id"]], ids(p["owners"]), p["contract"], ids(M.port_reqs[p["id"]]),
            ids(M.port_r04[p["id"]])] for p in M.ports])

    h2("entities")
    add(P["entities"])
    add("")
    table(["实体", "计算与规则", "本地存储", "同步", "模块", "需求", "R04 子项", "设计定位"],
          [[e["id"], e["compute"], e["store"], e["sync"], ids(e["modules"]), ids(e["reqs"]),
            ids(M.entity_r04[e["id"]]), e["refs"]] for e in M.entities])

    h2("trace")
    add(P["trace"])
    add("")
    table(["ID", "需求", "设计定位", "模块", "端口", "落地里程碑", "验收 ID", "说明"],
          [[r.id, r.title, r.design, ids(r.modules), ids([M.port_name[p] for p in r.ports]), r.milestone,
            ids(r.tests), r.note] for r in M.reqs])
    h3("r04")
    add(P["r04"])
    add("")
    table(["子项", "内容", "设计定位", "实体", "模块", "端口", "验收 ID", "说明"],
          [[x.id, x.content, x.design, ids(x.entities), ids(x.modules), ids([M.port_name[p] for p in x.ports]),
            ids(x.tests), x.note] for x in M.r04])
    h3("tests")
    add(P["tests"])
    add("")
    table(["验收 ID", "子编号", "验收对象", "所在章节", "最早门槛", "需求", "R04 子项", "客户端功能面", "服务端功能"],
          [[t.id, ids(M.subs.get(t.id, [])), t.object, t.section, t.gate, ids(M.test_reqs[t.id]),
            ids(M.test_r04[t.id]), ids(M.test_cf[t.id]), ids(M.test_sf[t.id])] for t in M.tests])

    h2("client")
    add(P["client"])
    add("")
    table(["编号", "功能面", "需求", "模块", "Android", "Windows", "鸿蒙（预留）", "验收 ID", "设计定位"],
          [[c["id"], c["title"], ids(c["reqs"]), ids(c["modules"]), c["android"], c["windows"], c["ohos"],
            ids(c["tests"]), c["refs"]] for c in M.cfs])

    h2("server")
    add(P["server"])
    add("")
    add(MD_FENCE + "mermaid")
    add("flowchart LR")
    add("  accTitle: 服务端功能与外部依赖")
    add("  accDescr: " + backend_summary(M))
    add('  subgraph G_client ["客户端模块"]')
    for c in M.backend_clients:
        add(f'    {mid("C", c)}["{mlabel(c)}"]')
    add("  end")
    add('  subgraph G_server ["服务端（server/）"]')
    for s in M.sfs:
        add(f'    {mid("S", s["id"])}["{mlabel(s["id"] + " " + s["title"])}"]')
    add("  end")
    add('  subgraph G_external ["外部依赖"]')
    for e in M.backend_externals:
        add(f'    {mid("X", e)}["{mlabel(M.ext_label[e])}"]')
    add("  end")
    for s in M.sfs:
        for c in s["client_modules"]:
            add(f"  {mid('C', c)} --> {mid('S', s['id'])}")
    for s in M.sfs:
        for e in s["externals"]:
            add(f"  {mid('S', s['id'])} --> {mid('X', e)}")
    add(MD_FENCE)
    add("")
    add("![服务端功能与外部依赖图：调用方模块、服务端功能与外部依赖](diagrams/backend-module-map.svg)")
    add("")
    table(["编号", "服务端功能", "契约", "客户端模块", "外部依赖", "需求", "验收 ID", "设计定位"],
          [[s["id"], s["title"], s["contract"], ids(s["client_modules"]), ids([M.ext_label[e] for e in s["externals"]]),
            ids(s["reqs"]), ids(s["tests"]), s["refs"]] for s in M.sfs])
    h3("externals")
    table(["外部依赖", "说明", "使用方"], [[e["label"], e["note"], ids(M.ext_users[e["id"]])] for e in M.externals])

    h2("milestones")
    add(P["milestones"])
    add("")
    table(["里程碑", "落地的需求", "首次提交证据的验收 ID"],
          [[f"{ms.id} {ms.name}", ids(M.ms_reqs[ms.id]), ids(M.ms_tests[ms.id])] for ms in M.milestones])
    if P["loose"]:
        add(P["loose"])
        add("")

    h2("repro")
    add(f"- 运行 {BT}python tools/generate-feature-map.py{BT} 写出有变化的文件；运行 {BT}python tools/generate-feature-map.py --check{BT}"
        " 只在内存中生成并逐字节比对，不写盘。退出码：0 表示一致；1 表示存在漂移，或 diagrams/ 中有非生成文件；2 表示输入无效或校验失败，"
        f"此时不写任何文件。修改 10–13 或映射数据后先重新生成，再运行 {BT}node tools/verify-sadd.mjs{BT}。")
    add("- 输入：映射数据（JSON 的 mapping 部分），以及 00、09、10、11、12、13 的标题与表格。需求、R04 子项与验收 ID 总表来自 13；"
        "目录树、端口表、实体表与里程碑表来自 10，并与映射数据逐项比对。")
    add("- 生成时校验，任一失败即退出码 2：")
    add("  - 需求与 R04 子项的集合与 13 一致；引用的验收 ID 都在 13 的验收 ID 总表中，子编号所属的验收 ID 也在其中；")
    add("  - 计划路径与 10 的目录树一致，端口与 10 的端口表一致，实体名都出现在 10 的实体表中；")
    add("  - 每个端口至少有一个归属模块属于引用它的需求或子项；R04 子项的模块与端口包含在 R04 的映射中；"
        "每个模块、端口和外部依赖都至少被引用一次；")
    add("  - 客户端功能面与服务端功能的验收 ID 只取所映射需求在 13 中的验收 ID；")
    add("  - 依赖无环并满足 §代码模块与职责 中的依赖约束；总览图只连接相邻层或同层相邻模块；")
    add("  - 交叉引用写成文档号加章节名（如 10 §端口契约），逐条对照目标文档的标题；13 中省略文档号的章节引用补为以 13 开头；"
        "T、D、ADR 编号都在 13、00、09 中有定义。")
    add("- 输出约定：UTF-8、LF、文件以换行结尾；不含控制字符、行号锚点、行号引用与外部请求；HTML 带内容安全策略"
        "（default-src 'none'，样式与脚本按哈希放行），筛选按编号精确匹配、其他文字按包含匹配，表格区域可用键盘聚焦并滚动。")
    add("- SVG 不读取字体文件：字体依次回退 Microsoft YaHei、Noto Sans CJK SC、系统无衬线字体；换行按固定字宽表估算，字宽取常见中文字体的上界，"
        "同一输入在任何平台生成相同字节。")
    add(f"- 规模：{stats}。")
    add("- 环境：Python 3.9 及以上，只用标准库。")
    add("")

    h2("revisions")
    table(["采纳的审查编号", "本文落点"], [[r["ids"], r["landing"]] for r in M.revs])
    return "\n".join(L).rstrip("\n") + "\n"


# ------------------------------------------------------------ SVG

FONT_STACK = ("'Microsoft YaHei','微软雅黑','Noto Sans CJK SC','Noto Sans SC','Source Han Sans SC',"
              "'PingFang SC','Hiragino Sans GB',sans-serif")
C_DARK, C_MUTED, C_ACCENT, C_GREEN = "#0f172a", "#475569", "#1d4ed8", "#166534"
C_BAND = ("#f8fafc", "#eef2f7")
C_BOX_STROKE, C_EDGE, C_DASH = "#64748b", "#475569", "#94a3b8"
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:+#@%-]+|\s+|.", re.S)
NO_START = set("，。、；：！？）」』】〉》”’,.;:!?)]}%")
NO_END = set("（「『【〈《“‘([{")


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def char_em(ch):
    """字宽上界（单位 em）：Microsoft YaHei、等线与 Noto Sans SC 的常规体和粗体（除以 1.06）实测取最大值。"""
    if ch == " ":
        return 0.33
    if ord(ch) < 0x80:
        if ch in "il.,:;!|'":
            return 0.35
        if ch in "fjrt()[]{}/\\":
            return 0.45
        if ch in "-\"":
            return 0.55
        if ch in "mwMW@%&":
            return 1.05
        if ch in "+<=>^~#*":
            return 0.75
        if "A" <= ch <= "Z":
            return 0.83
        return 0.65
    if unicodedata.combining(ch):
        return 0.0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return 1.0
    if eaw == "A":
        return 1.1
    return 0.75


def text_width(text, size, bold=False):
    return sum(char_em(ch) for ch in text) * size * (1.06 if bold else 1.0)


def wrap(text, size, max_w, bold=False):
    def width(tokens):
        return text_width("".join(tokens), size, bold)

    lines, cur = [], []
    for tok in TOKEN_RE.findall(text):
        if tok.isspace():
            if cur:
                cur.append(" ")
            continue
        if width(cur + [tok]) <= max_w:
            cur.append(tok)
            continue
        if text_width(tok, size, bold) > max_w:
            for ch in tok:
                if cur and width(cur + [ch]) > max_w:
                    lines.append(cur)
                    cur = []
                cur.append(ch)
            continue
        while cur and cur[-1] == " ":
            cur.pop()
        carry = []
        if tok in NO_START and len(cur) > 1 and width([cur[-1], tok]) <= max_w:
            carry = [cur.pop()]
        while len(cur) > 1 and cur[-1] in NO_END:
            carry.insert(0, cur.pop())
        if cur:
            lines.append(cur)
        cur = carry + [tok]
    if cur:
        lines.append(cur)
    return [s for s in ("".join(l).strip() for l in lines) if s]


def block(spec, inner_w):
    out = []
    for text, size, bold, fill, gap in spec:
        for i, part in enumerate(wrap(text, size, inner_w, bold)):
            out.append((part, size, bold, fill, gap if i == 0 else 0))
    return out


def block_h(lines):
    return sum(gap + round(1.5 * size) for _, size, _, _, gap in lines)


def draw_lines(out, x, y, lines):
    for text, size, bold, fill, gap in lines:
        y += gap
        weight = ' font-weight="700"' if bold else ""
        out.append(f'<text x="{x}" y="{y + round(1.12 * size)}" font-size="{size}"{weight} fill="{fill}">{esc(text)}</text>')
        y += round(1.5 * size)
    return y


def svg_line(x1, y1, x2, y2, prefix):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C_EDGE}" stroke-width="1.6" '
            f'marker-end="url(#{prefix}-arrow)"/>')


def svg_document(W, H, prefix, title, desc, parts):
    head = [
        f'<svg xmlns="{SVG_NS}" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-labelledby="{prefix}-title {prefix}-desc" font-family="{esc(FONT_STACK)}">',
        f'<title id="{prefix}-title">{esc(title)}</title>',
        f'<desc id="{prefix}-desc">{esc(desc)}</desc>',
        "<defs>",
        f'<marker id="{prefix}-arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{C_EDGE}"/></marker>',
        "</defs>",
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>',
    ]
    return "\n".join(head + parts + ["</svg>"]) + "\n"


def render_feature_svg(M):
    W, MG, LABEL_W, GAP, PAD, BAND_PAD, BAND_GAP, BOX_MAX = 1700, 40, 170, 36, 14, 18, 48, 520
    AX = MG + LABEL_W + 24
    avail = W - AX - MG - BAND_PAD
    title = "功能—模块总览"
    subtitle = ("计划模块，仓库当前不含应用源码。实线箭头：编译期依赖，只允许自上而下；同层箭头：装配关系；"
                "虚线框：不在客户端依赖链内；框内“需求”为承载的需求编号。")
    head = block([(title, 22, True, C_DARK, 0), (subtitle, 14, False, C_MUTED, 6)], W - 2 * MG)
    texts, bands, boxes, edges = [], [], [], []
    draw_lines(texts, MG, MG, head)
    y = MG + block_h(head) + 24
    linked = set()
    for m in M.modules:
        if m["depends_on"]:
            linked.add(m["id"])
            linked.update(m["depends_on"])
    geo = {}
    for li, layer in enumerate(M.layers):
        mods = M.modules_by_layer[layer["id"]]
        n = len(mods)
        bw = min(BOX_MAX, (avail - GAP * (n - 1)) // n)
        x0 = AX + (avail - (bw * n + GAP * (n - 1))) // 2
        contents = []
        for m in mods:
            reqs = M.module_reqs[m["id"]]
            contents.append(block([
                (m["id"], 17, True, C_DARK, 0),
                (m["path"], 13, False, C_MUTED, 2),
                (m["responsibility"], 14, False, C_DARK, 8),
                ("需求：" + ("、".join(reqs) if reqs else "—"), 13, False, C_ACCENT, 8),
            ], bw - 2 * PAD))
        box_h = max(block_h(c) for c in contents) + 2 * PAD
        label = block([(layer["title"], 15, True, C_DARK, 0)], LABEL_W - 16)
        band_h = max(box_h, block_h(label)) + 2 * BAND_PAD
        dashed = not any(m["id"] in linked for m in mods)
        stroke = f' stroke="{C_DASH}" stroke-width="1.5" stroke-dasharray="8 6"' if dashed else ""
        bands.append(f'<rect x="{MG}" y="{y}" width="{W - 2 * MG}" height="{band_h}" rx="12" '
                     f'fill="{C_BAND[li % 2]}"{stroke}/>')
        draw_lines(bands, MG + 14, y + BAND_PAD, label)
        for i, m in enumerate(mods):
            bx, by = x0 + i * (bw + GAP), y + BAND_PAD
            geo[m["id"]] = (bx, by, bw, box_h, li)
            boxes.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{box_h}" rx="8" fill="#ffffff" '
                         f'stroke="{C_BOX_STROKE}" stroke-width="1.2"/>')
            draw_lines(boxes, bx + PAD, by + PAD, contents[i])
        y += band_h + BAND_GAP
    y = y - BAND_GAP + 20
    legend = block([("依赖规则、端口与需求追踪见 14 功能与代码模块映射；本图由 tools/generate-feature-map.py 从映射数据生成。",
                     13, False, C_MUTED, 0)], W - 2 * MG)
    draw_lines(texts, MG, y, legend)
    H = y + block_h(legend) + MG

    def cx(mod):
        return geo[mod][0] + geo[mod][2] // 2

    vertical, horizontal = [], []
    for m in M.modules:
        for d in m["depends_on"]:
            (horizontal if geo[m["id"]][4] == geo[d][4] else vertical).append((m["id"], d))
    outs, ins = {}, {}
    for s, t in vertical:
        outs.setdefault(s, []).append(t)
        ins.setdefault(t, []).append(s)
    for k in outs:
        outs[k].sort(key=lambda t: (cx(t), t))
    for k in ins:
        ins[k].sort(key=lambda s: (cx(s), s))
    for s, t in vertical:
        gs, gt = geo[s], geo[t]
        k, n = outs[s].index(t), len(outs[s])
        j, c = ins[t].index(s), len(ins[t])
        edges.append(svg_line(gs[0] + gs[2] * (k + 1) // (n + 1), gs[1] + gs[3],
                              gt[0] + gt[2] * (j + 1) // (c + 1), gt[1] - 2, "fm"))
    for s, t in horizontal:
        gs, gt = geo[s], geo[t]
        yy = gs[1] + gs[3] // 2
        if gt[0] > gs[0]:
            edges.append(svg_line(gs[0] + gs[2], yy, gt[0] - 2, yy, "fm"))
        else:
            edges.append(svg_line(gs[0], yy, gt[0] + gt[2] + 2, yy, "fm"))
    return svg_document(W, H, "fm", title, feature_summary(M), bands + texts + boxes + edges)


def place_column(items, contents, x, w, top, bottom, pad, min_gap=16, max_gap=72):
    hs = [block_h(contents[i]) + 2 * pad for i in items]
    n = len(items)
    free = (bottom - top) - sum(hs)
    gap = min_gap
    if n > 1 and free > min_gap * (n - 1):
        gap = min(max_gap, free // (n - 1))
    total = sum(hs) + gap * (n - 1)
    y = top + max(0, ((bottom - top) - total) // 2)
    geo = {}
    for item, h in zip(items, hs):
        geo[item] = (x, y, w, h)
        y += h + gap
    return geo


def render_backend_svg(M):
    W, MG, PAD = 1700, 40, 14
    LX, LW, SX, SW, RX, RW = 40, 360, 550, 600, 1300, 360
    title = "服务端功能与外部依赖"
    subtitle = ("左：调用服务端的客户端模块；中：server/ 模块化单体中的服务端功能；右：外部依赖。"
                "同步只接收密文，游客数据不进入上传端口。")
    head = block([(title, 22, True, C_DARK, 0), (subtitle, 14, False, C_MUTED, 6)], W - 2 * MG)
    texts, boxes, edges = [], [], []
    draw_lines(texts, MG, MG, head)
    y = MG + block_h(head) + 24
    for x0, label in ((LX, "客户端模块"), (SX, "服务端功能（server/）"), (RX, "外部依赖")):
        texts.append(f'<text x="{x0}" y="{y + 17}" font-size="15" font-weight="700" fill="{C_MUTED}">{esc(label)}</text>')
    y += 36
    top = y
    sgeo = {}
    for s in M.sfs:
        content = block([
            (f"{s['id']} {s['title']}", 16, True, C_DARK, 0),
            (s["contract"], 13, False, C_DARK, 6),
            ("需求：" + "、".join(s["reqs"]), 13, False, C_ACCENT, 6),
            ("验收：" + "、".join(s["tests"]), 13, False, C_GREEN, 2),
        ], SW - 2 * PAD)
        h = block_h(content) + 2 * PAD
        sgeo[s["id"]] = (SX, y, SW, h)
        boxes.append(f'<rect x="{SX}" y="{y}" width="{SW}" height="{h}" rx="8" fill="#ffffff" '
                     f'stroke="{C_BOX_STROKE}" stroke-width="1.2"/>')
        draw_lines(boxes, SX + PAD, y + PAD, content)
        y += h + 22
    bottom = y - 22
    left = {c: block([(c, 16, True, C_DARK, 0), (M.module_path[c], 13, False, C_MUTED, 2)], LW - 2 * PAD)
            for c in M.backend_clients}
    right = {e: block([(M.ext_label[e], 15, True, C_DARK, 0),
                       (next(x["note"] for x in M.externals if x["id"] == e), 13, False, C_MUTED, 4)], RW - 2 * PAD)
             for e in M.backend_externals}
    lgeo = place_column(M.backend_clients, left, LX, LW, top, bottom, PAD)
    rgeo = place_column(M.backend_externals, right, RX, RW, top, bottom, PAD)
    for geo, contents in ((lgeo, left), (rgeo, right)):
        for key, (x0, y0, w, h) in geo.items():
            boxes.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="8" fill="#f8fafc" '
                         f'stroke="{C_BOX_STROKE}" stroke-width="1.2"/>')
            draw_lines(boxes, x0 + PAD, y0 + PAD, contents[key])

    def cy(g):
        return g[1] + g[3] // 2

    pairs_l = [(c, s["id"]) for s in M.sfs for c in s["client_modules"]]
    pairs_r = [(s["id"], e) for s in M.sfs for e in s["externals"]]
    for pairs, ga, gb in ((pairs_l, lgeo, sgeo), (pairs_r, sgeo, rgeo)):
        outs, ins = {}, {}
        for a, b in pairs:
            outs.setdefault(a, []).append(b)
            ins.setdefault(b, []).append(a)
        for a in outs:
            outs[a].sort(key=lambda b: (cy(gb[b]), b))
        for b in ins:
            ins[b].sort(key=lambda a: (cy(ga[a]), a))
        for a, b in pairs:
            g1, g2 = ga[a], gb[b]
            k, n = outs[a].index(b), len(outs[a])
            j, c = ins[b].index(a), len(ins[b])
            edges.append(svg_line(g1[0] + g1[2], g1[1] + g1[3] * (k + 1) // (n + 1),
                                  g2[0] - 2, g2[1] + g2[3] * (j + 1) // (c + 1), "bm"))
    end = max([bottom] + [g[1] + g[3] for g in list(lgeo.values()) + list(rgeo.values())])
    legend = block([("箭头表示调用或依赖方向；需求与验收 ID 的完整追踪见 14 功能与代码模块映射。", 13, False, C_MUTED, 0)],
                   W - 2 * MG)
    draw_lines(texts, MG, end + 24, legend)
    H = end + 24 + block_h(legend) + MG
    return svg_document(W, H, "bm", title, backend_summary(M), texts + boxes + edges)


# ------------------------------------------------------------ HTML

CSS = """*{box-sizing:border-box}
html{scroll-padding-top:8rem}
body{margin:0;font-family:"Microsoft YaHei","微软雅黑","Noto Sans CJK SC","Noto Sans SC","Source Han Sans SC","PingFang SC","Hiragino Sans GB",sans-serif;font-size:16px;line-height:1.6;color:#1f2937;background:#ffffff}
a{color:#1d4ed8;text-underline-offset:2px}
a:focus-visible,button:focus-visible,input:focus-visible,.table-scroll:focus-visible,main:focus-visible{outline:3px solid #1d4ed8;outline-offset:2px}
.skip{position:absolute;left:-10000px;top:0;padding:8px 12px;background:#ffffff;border:2px solid #1d4ed8;z-index:20}
.skip:focus{left:12px;top:12px}
header,main,footer{max-width:1280px;margin:0 auto;padding:0 20px}
header{padding-top:24px}
h1{font-size:28px;line-height:1.3;margin:0 0 8px}
h2{font-size:22px;line-height:1.35;margin:40px 0 12px;padding-top:12px;border-top:1px solid #d5dce6}
h3{font-size:18px;margin:28px 0 10px}
.meta,.note,.help,.count,figcaption{color:#4b5563}
nav ul{display:flex;flex-wrap:wrap;gap:6px 18px;list-style:none;margin:12px 0 0;padding:0}
.filter{position:sticky;top:0;z-index:10;background:#ffffff;border-bottom:1px solid #d5dce6;margin-top:16px}
.filter-inner{max-width:1280px;margin:0 auto;padding:10px 20px;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.filter label{font-weight:700}
.filter input{font:inherit;min-width:18rem;padding:6px 10px;border:2px solid #6b7c93;border-radius:6px;color:#1f2937;background:#ffffff}
.filter button{font:inherit;padding:6px 14px;border:2px solid #6b7c93;border-radius:6px;color:#1f2937;background:#f4f7fb;cursor:pointer}
.filter .help,.filter .status{margin:0;flex-basis:100%;font-size:14px}
.filter .status{color:#1f2937}
figure{margin:16px 0}
figure svg{display:block;width:100%;height:auto;border:1px solid #d5dce6;border-radius:8px}
.table-scroll{overflow-x:auto;margin:12px 0 24px;border:1px solid #d5dce6;border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:1100px;font-size:14px;line-height:1.55}
caption{caption-side:top;text-align:left;font-weight:700;padding:8px 10px}
th,td{border-top:1px solid #d5dce6;padding:6px 10px;text-align:left;vertical-align:top}
thead th{background:#eef2f7;white-space:nowrap}
tbody th{font-weight:700;white-space:nowrap}
tbody tr:nth-child(even){background:#f8fafc}
code{font-family:Consolas,"Cascadia Mono","Noto Sans Mono",monospace;font-size:0.92em}
@media print{.filter,.skip,nav{display:none}.table-scroll{overflow:visible}table{min-width:0}}
"""

JS = r"""(function () {
  'use strict';
  var box = document.getElementById('filter');
  var input = document.getElementById('q');
  var clear = document.getElementById('q-clear');
  var status = document.getElementById('q-status');
  if (!box || !input || !clear || !status) { return; }
  var tables = Array.prototype.slice.call(document.querySelectorAll('table[data-filter]'));
  var idPattern = /^(?:r\d{2}(?:\.[a-j])?|[ha]\d{2}|t-[a-z]+(?:-\d{2})?|cf-\d{2}|sf-\d{2}|m\d|d-\d{2}|adr-\d{3})$/;
  function matches(row, terms) {
    var ids = ' ' + (row.getAttribute('data-ids') || '').toLowerCase() + ' ';
    var text = row.textContent.toLowerCase();
    for (var i = 0; i < terms.length; i += 1) {
      var term = terms[i];
      var hit = idPattern.test(term) ? ids.indexOf(' ' + term + ' ') !== -1 : text.indexOf(term) !== -1;
      if (!hit) { return false; }
    }
    return true;
  }
  function apply() {
    var terms = input.value.toLowerCase().split(/\s+/).filter(function (t) { return t.length > 0; });
    var shown = 0;
    var total = 0;
    tables.forEach(function (table) {
      var rows = table.tBodies[0].rows;
      var visible = 0;
      for (var i = 0; i < rows.length; i += 1) {
        var ok = terms.length === 0 || matches(rows[i], terms);
        rows[i].hidden = !ok;
        if (ok) { visible += 1; }
      }
      var counter = document.getElementById(table.id + '-count');
      if (counter) {
        counter.textContent = terms.length === 0 ? '共 ' + rows.length + ' 行' : '显示 ' + visible + ' / ' + rows.length + ' 行';
      }
      shown += visible;
      total += rows.length;
    });
    status.textContent = terms.length === 0 ? '未筛选，共 ' + total + ' 行。' : '筛选后显示 ' + shown + ' / ' + total + ' 行。';
  }
  box.hidden = false;
  input.addEventListener('input', apply);
  clear.addEventListener('click', function () { input.value = ''; apply(); input.focus(); });
  apply();
})();
"""


def csp_hash(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


def code(text):
    return f"<code>{esc(text)}</code>"


def txt(text):
    return esc(text) if text else "—"


def ids_html(items):
    return esc("、".join(items)) if items else "—"


def row_ids(M, explicit, texts):
    found = set(explicit)
    for t in texts:
        found.update(ROW_ID_RE.findall(t))
    out = set()
    for i in found:
        out.add(i)
        if R04_ID_RE.fullmatch(i):
            out.add("R04")
        if SUB_ID_RE.fullmatch(i):
            out.add(i.rsplit("-", 1)[0])
        if i in M.subs:
            out.update(M.subs[i])
    return sorted(out)


def render_html(M, stats, feature_svg, backend_svg):
    P = prose(M)
    csp = (f"default-src 'none'; style-src {csp_hash(CSS)}; script-src {csp_hash(JS)}; "
           "base-uri 'none'; form-action 'none'")
    H = []
    add = H.append

    def section(key):
        add(f'<section aria-labelledby="sec-{key}">')
        add(f'<h2 id="sec-{key}">{esc(H2[key][1])}</h2>')

    def h3(key):
        add(f'<h3 id="sub-{key}">{esc(H3[key])}</h3>')

    def para(text):
        add(f"<p>{esc(text)}</p>")

    def table(tid, caption, header, rows):
        add(f'<div class="table-scroll" role="region" tabindex="0" aria-labelledby="{tid}-cap">')
        add(f'<table id="{tid}" data-filter="">')
        add(f'<caption id="{tid}-cap">{esc(caption)} <span class="count" id="{tid}-count">共 {len(rows)} 行</span></caption>')
        add("<thead><tr>" + "".join(f'<th scope="col">{esc(h)}</th>' for h in header) + "</tr></thead>")
        add("<tbody>")
        for cells, row in rows:
            add(f'<tr data-ids="{esc(" ".join(row))}"><th scope="row">{cells[0]}</th>'
                + "".join(f"<td>{c}</td>" for c in cells[1:]) + "</tr>")
        add("</tbody>")
        add("</table>")
        add("</div>")

    def figure(svg, cid, caption, href):
        add(f'<figure aria-labelledby="{cid}">')
        add(svg.rstrip("\n"))
        add(f'<figcaption id="{cid}">{esc(caption)} <a href="{href}">单独打开 SVG</a></figcaption>')
        add("</figure>")

    add("<!DOCTYPE html>")
    add('<html lang="zh-CN">')
    add("<head>")
    add('<meta charset="utf-8">')
    add(f'<meta http-equiv="Content-Security-Policy" content="{esc(csp)}">')
    add('<meta name="viewport" content="width=device-width, initial-scale=1">')
    add('<meta name="referrer" content="no-referrer">')
    add(f"<title>{esc(TITLE)} · BubeiGongshi</title>")
    add("<style>" + CSS + "</style>")
    add("</head>")
    add("<body>")
    add('<a class="skip" href="#main">跳到正文</a>')
    add("<header>")
    add(f"<h1>{esc(TITLE)}</h1>")
    add(f'<p class="meta">BubeiGongshi · {esc(M.date)} · {esc(TAGLINE)}</p>')
    add('<nav aria-label="本页目录"><ul>')
    for key in HTML_SECTIONS:
        add(f'<li><a href="#sec-{key}">{esc(H2[key][1])}</a></li>')
    add("</ul></nav>")
    add("</header>")
    add('<div class="filter" id="filter" role="search" hidden>')
    add('<div class="filter-inner">')
    add('<label for="q">筛选</label>')
    add('<input id="q" type="search" autocomplete="off" spellcheck="false" aria-describedby="q-help">')
    add('<button type="button" id="q-clear">清除</button>')
    add('<p id="q-help" class="help">输入编号（如 R04.c、T-GC、CF-06、M2、D-04）按编号精确匹配，输入其他文字按包含匹配；'
        '多个词用空格分隔，需同时满足。筛选作用于本页全部表格。</p>')
    add('<p id="q-status" class="status" role="status" aria-live="polite"></p>')
    add("</div>")
    add("</div>")
    add('<main id="main" tabindex="-1">')

    section("purpose")
    add(f'<p>本页是 <a href="{esc(OUT_MD.name)}">{esc(TITLE)}</a> 的离线浏览版本，内容相同：每条需求由哪些计划模块、端口和实体承载，'
        '以哪些验收 ID 证明。需求、设计定位与验收 ID 取自 13，模块、依赖与端口以 10 为准；路径都是未来实现规划，仓库当前不含应用源码。</p>')
    add('<p>映射数据见 <a href="resources/feature-code-map.json">resources/feature-code-map.json</a>（mapping 人工维护，derived 由生成器回填）；'
        '本页、14 文档与两张 SVG 由 <code>tools/generate-feature-map.py</code> 生成，不要手改。</p>')
    add("<ul>")
    for d in M.doc_list:
        add(f'<li><a href="{esc(d.file)}">{esc(d.h1)}</a>：{esc(d.use)}</li>')
    add("</ul>")
    add("</section>")

    section("overview")
    para(P["overview"])
    figure(feature_svg, "fig-feature", "功能—模块总览，与 14 文档中的图相同。", "diagrams/feature-module-map.svg")
    add("</section>")

    section("modules")
    para(P["modules"])
    table("tbl-modules", "代码模块与职责", ["模块", "层", "计划路径", "职责", "I/O 规则", "直接依赖", "承载需求", "设计定位"],
          [([code(m["id"]), txt(M.layer_short[m["layer"]]), code(m["path"]), txt(m["responsibility"]), txt(m["io_rule"]),
             ids_html(m["depends_on"]), ids_html(M.module_reqs[m["id"]]), txt(m["refs"])],
            row_ids(M, M.module_reqs[m["id"]] + M.module_r04[m["id"]], [m["refs"], m["responsibility"]]))
           for m in M.modules])
    h3("deps")
    add("<ul>")
    for r in M.forbidden:
        add(f"<li>{esc(r['rule'])}（{'含传递依赖' if r['transitive'] else '只限直接依赖'}）。</li>")
    add(f"<li>{esc(P['deps_tail'])}</li>")
    add("</ul>")
    add("</section>")

    section("ports")
    para(P["ports"])
    table("tbl-ports", "端口与归属", ["端口", "归属模块", "契约摘要", "用到的需求", "用到的 R04 子项"],
          [([esc(M.port_name[p["id"]]), ids_html(p["owners"]), txt(p["contract"]), ids_html(M.port_reqs[p["id"]]),
             ids_html(M.port_r04[p["id"]])],
            row_ids(M, M.port_reqs[p["id"]] + M.port_r04[p["id"]], [p["contract"]])) for p in M.ports])
    add("</section>")

    section("entities")
    para(P["entities"])
    table("tbl-entities", "学习域与公式语义实体", ["实体", "计算与规则", "本地存储", "同步", "模块", "需求", "R04 子项", "设计定位"],
          [([esc(e["id"]), txt(e["compute"]), txt(e["store"]), txt(e["sync"]), ids_html(e["modules"]),
             ids_html(e["reqs"]), ids_html(M.entity_r04[e["id"]]), txt(e["refs"])],
            row_ids(M, e["reqs"] + M.entity_r04[e["id"]], [e["refs"], e["sync"]])) for e in M.entities])
    add("</section>")

    section("trace")
    para(P["trace"])
    table("tbl-requirements", "需求—模块—验收追踪", ["ID", "需求", "设计定位", "模块", "端口", "落地里程碑", "验收 ID", "说明"],
          [([esc(r.id), txt(r.title), txt(r.design), ids_html(r.modules), ids_html([M.port_name[p] for p in r.ports]),
             txt(r.milestone), ids_html(r.tests), txt(r.note)],
            row_ids(M, [r.id, r.milestone] + r.tests, [r.design, r.note])) for r in M.reqs])
    h3("r04")
    para(P["r04"])
    table("tbl-r04", "R04 功能近似子项落点", ["子项", "内容", "设计定位", "实体", "模块", "端口", "验收 ID", "说明"],
          [([esc(x.id), txt(x.content), txt(x.design), ids_html(x.entities), ids_html(x.modules),
             ids_html([M.port_name[p] for p in x.ports]), ids_html(x.tests), txt(x.note)],
            row_ids(M, [x.id] + x.tests, [x.design, x.note])) for x in M.r04])
    h3("tests")
    para(P["tests"])
    table("tbl-tests", "验收 ID 反查", ["验收 ID", "子编号", "验收对象", "所在章节", "最早门槛", "需求", "R04 子项", "客户端功能面", "服务端功能"],
          [([esc(t.id), ids_html(M.subs.get(t.id, [])), txt(t.object), txt(t.section), txt(t.gate),
             ids_html(M.test_reqs[t.id]), ids_html(M.test_r04[t.id]), ids_html(M.test_cf[t.id]), ids_html(M.test_sf[t.id])],
            row_ids(M, [t.id] + M.test_reqs[t.id] + M.test_r04[t.id] + M.test_cf[t.id] + M.test_sf[t.id],
                    [t.object, t.gate])) for t in M.tests])
    add("</section>")

    section("client")
    para(P["client"])
    table("tbl-client", "客户端功能面与平台差异", ["编号", "功能面", "需求", "模块", "Android", "Windows", "鸿蒙（预留）", "验收 ID", "设计定位"],
          [([esc(c["id"]), txt(c["title"]), ids_html(c["reqs"]), ids_html(c["modules"]), txt(c["android"]),
             txt(c["windows"]), txt(c["ohos"]), ids_html(c["tests"]), txt(c["refs"])],
            row_ids(M, [c["id"]] + c["reqs"] + c["tests"], [c["refs"], c["ohos"]])) for c in M.cfs])
    add("</section>")

    section("server")
    para(P["server"])
    figure(backend_svg, "fig-backend", "服务端功能与外部依赖，与 14 文档中的图相同。", "diagrams/backend-module-map.svg")
    table("tbl-server", "服务端功能", ["编号", "服务端功能", "契约", "客户端模块", "外部依赖", "需求", "验收 ID", "设计定位"],
          [([esc(s["id"]), txt(s["title"]), txt(s["contract"]), ids_html(s["client_modules"]),
             ids_html([M.ext_label[e] for e in s["externals"]]), ids_html(s["reqs"]), ids_html(s["tests"]), txt(s["refs"])],
            row_ids(M, [s["id"]] + s["reqs"] + s["tests"], [s["refs"], s["contract"]])) for s in M.sfs])
    h3("externals")
    table("tbl-externals", "外部依赖", ["外部依赖", "说明", "使用方"],
          [([esc(e["label"]), txt(e["note"]), ids_html(M.ext_users[e["id"]])],
            row_ids(M, M.ext_users[e["id"]], [e["note"]])) for e in M.externals])
    add("</section>")

    section("milestones")
    para(P["milestones"])
    table("tbl-milestones", "里程碑落地顺序", ["里程碑", "落地的需求", "首次提交证据的验收 ID"],
          [([esc(f"{ms.id} {ms.name}"), ids_html(M.ms_reqs[ms.id]), ids_html(M.ms_tests[ms.id])],
            row_ids(M, [ms.id] + M.ms_reqs[ms.id] + M.ms_tests[ms.id], [])) for ms in M.milestones])
    if P["loose"]:
        add(f'<p class="note">{esc(P["loose"])}</p>')
    add("</section>")

    section("repro")
    add("<ul>")
    add("<li>运行 <code>python tools/generate-feature-map.py</code> 写出有变化的文件；加 <code>--check</code> 只比对不写盘，"
        "退出码 0 表示一致、1 表示漂移、2 表示输入无效。</li>")
    add("<li>生成时对照 13 与 10 校验需求、R04 子项、验收 ID、目录树、端口与实体，并逐条校验文档号加章节名的交叉引用。</li>")
    add("<li>本页可离线使用：内容安全策略禁止一切外部请求，样式与脚本按哈希放行；不运行脚本时表格照常完整显示。</li>")
    add(f"<li>规模：{esc(stats)}。</li>")
    add("</ul>")
    add("</section>")
    add("</main>")
    add("<footer>")
    add(f'<p class="note">由 <code>tools/generate-feature-map.py</code> 从 13、10 与映射数据生成；文字版见 '
        f'<a href="{esc(OUT_MD.name)}">{esc(TITLE)}</a>。</p>')
    add("</footer>")
    add("<script>" + JS + "</script>")
    add("</body>")
    add("</html>")
    return "\n".join(H) + "\n"


# ------------------------------------------------------------ 输出自检

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class HtmlCheck(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.hrefs, self.refs = [], [], [], [], []

    def handle_starttag(self, tag, attrs):
        self._attrs(tag, attrs)
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self._attrs(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"HTML：结束标签 </{tag}> 与 <{self.stack[-1] if self.stack else '—'}> 不匹配")
            if tag in self.stack:
                while self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()

    def _attrs(self, tag, attrs):
        for k, v in attrs:
            v = v or ""
            if k == "id":
                self.ids.append(v)
            elif k == "href":
                self.hrefs.append(v)
            elif k in ("aria-labelledby", "aria-describedby"):
                self.refs.extend(v.split())
            elif k == "for":
                self.refs.append(v)
            elif k == "style" or k.startswith("on"):
                self.errors.append(f"HTML：<{tag}> 不允许 {k} 属性")
            elif k in ("src", "srcset", "action", "formaction"):
                self.errors.append(f"HTML：<{tag}> 不允许 {k} 属性")


def local_target_ok(target):
    path = (SADD / target).resolve()
    return path in {p.resolve() for p in OUTPUT_PATHS} or path.exists()


def guard_md(text, M):
    errs = []
    lines, closed = scan_lines(text)
    raw = text.split("\n")
    if not closed:
        errs.append("代码块未闭合")
    if raw[0] != f"# {TITLE}" or sum(1 for _, l, f in lines if not f and l.startswith("# ")) != 1:
        errs.append("一级标题必须唯一且位于第一行")
    if len(raw) < 5 or not re.fullmatch(r"_BubeiGongshi · \d{4}-\d{2}-\d{2} · .+_", raw[2]) or raw[4] != "---":
        errs.append("文件头格式不符")
    h2s = [l[3:] for _, l, f in lines if not f and l.startswith("## ")]
    for h in h2s:
        if unicodedata.category(h[0]) != "So":
            errs.append(f"二级标题“{h}”应以 emoji 开头")
    if not h2s or h2s[-1] != "🔁 v4 修订记录":
        errs.append("最后一个二级标题必须是“🔁 v4 修订记录”")
    body, inside = [], False
    for _, line, fenced in lines:
        if fenced and FENCE_RE.match(line):
            if not inside and line.strip() == MD_FENCE + "mermaid":
                inside, body = True, []
            elif inside:
                joined = "\n".join(body)
                if "accTitle:" not in joined or "accDescr:" not in joined:
                    errs.append("mermaid 图缺少 accTitle 或 accDescr")
                inside = False
        elif inside:
            body.append(line)
    refs = Refs(M.refs.titles)
    for no, line, fenced in lines:
        if fenced:
            continue
        for m in LINE_REF_RE.finditer(line):
            errs.append(f"第 {no} 行：行号引用 {m.group(0)}")
        for m in MD_LINK_RE.finditer(line):
            target = m.group(1)
            if re.match(r"(?:https?:|mailto:|#)", target):
                continue
            file_part = target.split("#", 1)[0]
            if RETIRED_RE.search(file_part.split("/")[-1]):
                errs.append(f"第 {no} 行：链接到已退役文件 {target}")
            elif not local_target_ok(file_part):
                errs.append(f"第 {no} 行：链接目标不存在 {target}")
        refs.resolve(line, OWN_DOC, f"第 {no} 行", errs)
    M.md_refs = refs.count
    return ["14：" + e for e in errs]


def guard_html(text):
    errs = []
    for url in URL_RE.findall(text):
        if url != SVG_NS:
            errs.append(f"不允许外部地址 {url}")
    if re.search(r"<(?:link|img|iframe|object|embed|base|audio|video|source)\b", text, re.I):
        errs.append("不允许加载外部资源的元素")
    if re.search(r"@import|url\((?!#)", text):
        errs.append("不允许外部样式资源")
    if 'http-equiv="Content-Security-Policy"' not in text:
        errs.append("缺少内容安全策略")
    chk = HtmlCheck()
    chk.feed(text)
    chk.close()
    errs += chk.errors
    if chk.stack:
        errs.append(f"未闭合标签 {'、'.join(chk.stack)}")
    seen = set()
    for i in chk.ids:
        if i in seen:
            errs.append(f"id 重复 {i}")
        seen.add(i)
    for r in chk.refs:
        if r not in seen:
            errs.append(f"引用了不存在的 id {r}")
    for href in chk.hrefs:
        if href.startswith("#"):
            if href[1:] not in seen:
                errs.append(f"页内链接目标不存在 {href}")
        elif re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", href):
            errs.append(f"不允许外部链接 {href}")
        elif not local_target_ok(href.split("#", 1)[0]):
            errs.append(f"链接目标不存在 {href}")
    return ["HTML：" + e for e in errs]


def guard_svg(text, name):
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return [f"{name}：XML 无效（{exc}）"]
    errs = []
    if root.tag != "{%s}svg" % SVG_NS:
        errs.append("根元素不是 svg")
    seen = set()
    for el in root.iter():
        i = el.get("id")
        if i:
            if i in seen:
                errs.append(f"id 重复 {i}")
            seen.add(i)
    for url in URL_RE.findall(text):
        if url != SVG_NS:
            errs.append(f"不允许外部地址 {url}")
    if "style=" in text or "<style" in text:
        errs.append("不允许 style（HTML 内联时受 CSP 限制）")
    return [f"{name}：{e}" for e in errs]


def guard(outputs, M):
    errs = []
    for path, text in outputs.items():
        name = rel(path)
        if "\r" in text:
            errs.append(f"{name}：含 CR")
        if not text.endswith("\n") or text.endswith("\n\n"):
            errs.append(f"{name}：必须以单个换行结尾")
        if CONTROL_RE.search(text):
            errs.append(f"{name}：含控制字符")
        if LINE_ANCHOR_RE.search(text):
            errs.append(f"{name}：含行号锚点")
        for no, line in enumerate(text.split("\n"), 1):
            if YOLO_RE.search(line):
                errs.append(f"{name} 第 {no} 行：含只允许出现在实验分支的内容")
        bad = sorted(set(undefined_tokens(text, M.f13.defined, M.d_ids, M.adr_ids)))
        if bad:
            errs.append(f"{name}：未定义的编号 {'、'.join(bad)}")
    errs += guard_md(outputs[OUT_MD], M)
    errs += guard_html(outputs[OUT_HTML])
    for p in (OUT_FEATURE_SVG, OUT_BACKEND_SVG):
        errs += guard_svg(outputs[p], rel(p))
    return errs


# ------------------------------------------------------------ 主流程

def build_outputs():
    data = load_json()
    errors = []
    docs = load_docs(data["mapping"]["docs"], errors)
    if errors:
        raise InputError(errors)
    M = build_model(data, docs, errors)
    if errors:
        raise InputError(errors)
    stats = stats_text(M)
    feature_svg = render_feature_svg(M)
    backend_svg = render_backend_svg(M)
    out_json = json.dumps({
        "schema": data["schema"], "version": data["version"], "date": data["date"], "note": data["note"],
        "mapping": data["mapping"], "derived": build_derived(M),
    }, ensure_ascii=False, indent=2) + "\n"
    outputs = {
        OUT_MD: render_md(M, stats),
        OUT_HTML: render_html(M, stats, feature_svg, backend_svg),
        OUT_FEATURE_SVG: feature_svg,
        OUT_BACKEND_SVG: backend_svg,
        MAP_JSON: out_json,
    }
    problems = guard(outputs, M)
    if problems:
        raise InputError(["生成结果未通过自检：" + p for p in problems])
    return {path: text.encode("utf-8") for path, text in outputs.items()}, M


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="生成 SADD 功能与代码模块映射：14 文档、HTML、两张 SVG 与 JSON 的 derived 部分。")
    parser.add_argument("--check", action="store_true",
                        help="只在内存中生成并与磁盘逐字节比对，不写文件；有差异或 diagrams/ 中有非生成文件时退出码 1")
    args = parser.parse_args(argv)
    try:
        outputs, M = build_outputs()
    except InputError as exc:
        for line in exc.errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"失败：{len(exc.errors)} 处错误，未写任何文件。", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        if os.environ.get("FEATURE_MAP_DEBUG"):
            raise
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    c = counts(M)
    summary = " ".join(f"{k}={v}" for k, v in c.items()) + f" refs_checked={M.refs.count + M.md_refs}"
    stale = sorted(p for p in DIAGRAMS.iterdir() if p.is_file() and p not in outputs) if DIAGRAMS.is_dir() else []
    if args.check:
        drift = []
        for path, data in outputs.items():
            same = path.is_file() and path.read_bytes() == data
            print(f"{'ok' if same else 'drift'}: {rel(path)}")
            if not same:
                drift.append(path)
        for p in stale:
            print(f"stale: {rel(p)}（不是生成物）")
        print(summary)
        if drift or stale:
            print(f"检查失败：{len(drift)} 个文件与生成结果不一致，{len(stale)} 个非生成文件；"
                  "运行 python tools/generate-feature-map.py 并删除非生成文件后复查。", file=sys.stderr)
            return 1
        return 0
    try:
        for path, data in outputs.items():
            if path.is_file() and path.read_bytes() == data:
                print(f"unchanged: {rel(path)}")
            else:
                write_atomic(path, data)
                print(f"wrote: {rel(path)}")
    except OSError as exc:
        print(f"error: 写入失败：{exc}", file=sys.stderr)
        return 2
    for p in stale:
        print(f"warning: {rel(p)} 不是生成物，请删除；--check 会因它失败。", file=sys.stderr)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
