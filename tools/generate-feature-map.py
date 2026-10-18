#!/usr/bin/env python3
"""Render traceable design-only feature maps; never create application modules.

Run with the bundled Python (Pillow is supplied by DSH):
    python tools/generate-feature-map.py
Inputs: SADD/resources/feature-code-map.json plus the referenced local Markdown.
Outputs: a Markdown report, an offline HTML report, and SVG/PNG diagrams.
The current script writes only these explicit documentation outputs.
"""
from pathlib import Path
from functools import lru_cache
from html import escape
import json
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SADD = ROOT / 'SADD'
DATA_PATH = SADD / 'resources/feature-code-map.json'
DATA = json.loads(DATA_PATH.read_text(encoding='utf-8'))
MODULES = {m['id']: m for m in DATA['modules']}
OUT = SADD / 'diagrams'
OUT.mkdir(exist_ok=True)
FONT = Path('C:/Windows/Fonts/msyh.ttc')
BOLD = Path('C:/Windows/Fonts/msyhbd.ttc')
if not FONT.is_file() or not BOLD.is_file():
    raise SystemExit('Chinese font required: Microsoft YaHei (msyh.ttc / msyhbd.ttc).')
BG, INK, MUTED = '#f4f7fb', '#20334e', '#62728a'
BLUE, TEAL, PURPLE = '#205ea3', '#16726b', '#6c4a98'
AMBER, AMBER_BG, BORDER = '#946116', '#fff2d7', '#dbe3ef'

@lru_cache(maxsize=None)
def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)

def wrap(text, width, size=23, bold=False):
    # Real glyph metrics: every written line fits its explicit cell width.
    result = []
    for paragraph in str(text).split('\n'):
        line = ''
        for char in paragraph:
            if line and font(size, bold).getlength(line + char) > width:
                result.append(line)
                line = char
            else:
                line += char
        result.append(line)
    return result

class Canvas:
    def __init__(self, width, height, title, description):
        self.w, self.h = width, height
        self.image = Image.new('RGB', (width, height), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
                    f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                    f'<rect width="{width}" height="{height}" fill="{BG}"/>']
        self.layout_checks = 0

    def rect(self, x, y, w, h, fill='white', stroke=None, radius=16):
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius, fill, outline=stroke, width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or fill}" stroke-width="2"/>')

    def text(self, x, y, text, size=23, color=INK, bold=False):
        f = font(size, bold)
        self.draw.text((x, y), str(text), font=f, fill=color)
        baseline = y + f.getmetrics()[0]
        weight = '700' if bold else '400'
        self.svg.append(f'<text x="{x}" y="{baseline}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(str(text))}</text>')

    def block(self, x, y, text, width, size=23, color=INK, bold=False, line_height=None, bottom=None):
        line_height = line_height or round(size * 1.45)
        lines = wrap(text, width, size, bold)
        end = y + len(lines) * line_height
        if bottom is not None and end > bottom:
            raise ValueError(f'Overflow: {text!r}: ends {end}, limit {bottom}')
        for i, line in enumerate(lines):
            self.text(x, y+i*line_height, line, size, color, bold)
        self.layout_checks += 1
        return end

    def line(self, points, color=BORDER, width=3, arrow=False, dashed=False):
        self.draw.line(points, fill=color, width=width, joint='curve')
        self.svg.append('<polyline points="' + ' '.join(f'{x},{y}' for x,y in points) + f'" fill="none" stroke="{color}" stroke-width="{width}"' + (' stroke-dasharray="9 6"' if dashed else '') + '/>')
        if arrow:
            x0,y0 = points[-2]; x,y = points[-1]
            import math
            angle = math.atan2(y-y0, x-x0)
            a = [(x,y), (x-13*math.cos(angle-.46), y-13*math.sin(angle-.46)), (x-13*math.cos(angle+.46), y-13*math.sin(angle+.46))]
            self.draw.polygon(a, fill=color)
            self.svg.append('<polygon points="'+' '.join(f'{p:.1f},{q:.1f}' for p,q in a)+f'" fill="{color}"/>')

    def save(self, stem):
        svg = OUT / (stem+'.svg')
        svg.write_text('\n'.join(self.svg+['</svg>'])+'\n', encoding='utf-8')
        ET.parse(svg)
        png = OUT / (stem+'.png')
        self.image.save(png, optimize=True)
        with Image.open(png) as im:
            assert im.size == (self.w, self.h)
            im.verify()
        return {'svg': svg.relative_to(ROOT).as_posix(), 'png': png.relative_to(ROOT).as_posix(), 'width': self.w, 'height': self.h, 'text_blocks_checked': self.layout_checks}

def overview():
    c = Canvas(2040, 2020, '预计功能与规划代码模块对应关系', '现行 v3 的十二组功能映射；全部产品模块待实现。目录缩写只代表设计中的未来路径。')
    c.text(60, 38, '预计功能 → 规划代码模块', 52, bold=True)
    c.text(62, 112, 'BubeiGongshi  ·  main@'+DATA['audit_commit']+'  ·  '+DATA['date'], 23, MUTED)
    c.rect(60, 168, 1920, 78, AMBER_BG)
    c.text(82, 187, '设计覆盖 ≠ 实现完成：37 项需求均已映射；应用、Rust 核心和服务端源码均未落地。', 27, AMBER, True)
    xs = [60, 420, 800, 1170, 1560]
    ws = [360, 380, 370, 390, 420]
    heads = ['功能 / 需求编号', '客户端层 / 用例入口', 'Rust 核心 / 本地服务', '存储 / 包 / 平台支撑', '后台或边界']
    colors = [INK, BLUE, BLUE, TEAL, PURPLE]
    for x,w,t,col in zip(xs,ws,heads,colors):
        c.rect(x, 278, w-8, 58, col, radius=9)
        c.text(x+17, 289, t, 23, '#ffffff', True)
    y = 350
    for i,g in enumerate(DATA['groups']):
        c.rect(60, y, 1920, 123, '#ffffff' if i%2==0 else '#edf2f9', radius=9)
        c.rect(60, y+7, 6, 109, BLUE, radius=2)
        c.block(79,y+10,g['title'],326,26,bold=True,bottom=y+51)
        c.block(79,y+53,g['ids'],326,19,color=MUTED,line_height=26,bottom=y+115)
        values=[g['client'],g['core'],g['support'],g['server']]
        for x,w,val,col in zip(xs[1:],ws[1:],values,colors[1:]):
            c.block(x+17,y+20,val,w-38,23,color=col,line_height=33,bottom=y+116)
        y+=129
    c.block(62,1932,'读法：同一行是同一功能的职责映射，并非每行都会调用后台。完整未来目录、37 项逐条验收引用及后台专属职责见配套 HTML / Markdown。',1910,22,MUTED,line_height=32,bottom=2015)
    return c.save('feature-module-map')

def box(c, x,y,w,h,title,body,color=INK,size=23):
    c.rect(x,y,w,h,'#ffffff',BORDER)
    c.text(x+22,y+15,title,26,color,True)
    c.block(x+22,y+64,body,w-44,size,line_height=32,bottom=y+h-10)

def backend():
    c=Canvas(2040,1800,'后台能力、数据平面与客户端边界','九组后台或后台配套职责全部待实现；端到端加密同步、云识别临时明文与公开资源分发相互隔离。')
    c.text(60,38,'后台能力映射与数据边界',52,bold=True)
    c.text(62,112,'server/ 为拟建模块化单体 + 受限 worker；B01–B09 是职责标签，不是现存目录。',25,MUTED)
    c.rect(60,168,1920,72,AMBER_BG)
    c.text(82,185,'所有后台职责均未实现；云识别并不提供同步 E2EE 的明文保密性。',27,AMBER,True)
    c.rect(60,276,1920,150,'#eaf1fc',radius=18)
    c.text(84,291,'客户端：presentation/ → application/ → adapters/ + fml-ffi/',28,BLUE,True)
    c.block(84,346,'账户门禁 / 逐次图像授权 / E2EE 加解密 / job_id 恢复；本机库密钥与识别历史不上云；候选仍经本地解析、量纲校验和人工确认。',1870,24,line_height=35,bottom=418)
    box(c,60,478,520,202,'B01  身份与账户绑定','OIDC / PKCE / token 校验\nowner 必须来自可信 token\n游客不能调用云识别',BLUE)
    box(c,626,478,664,202,'B02  恢复包装 / 设备 / 删除','仅保存加密包装、参数与版本\n原始恢复码、本机密钥不上传\n撤销 / epoch / 账户删除与备份清单',BLUE)
    box(c,1336,478,644,202,'B09  公开资源签名发布','tools/content/ → 双审 / 签名包\nTUF 元数据 → 公开分发 → fml-assets\n不是私有内容同步或学习数据上传',TEAL)
    c.line([(310,426),(310,466)],BLUE,3,True)
    c.line([(950,426),(950,466)],BLUE,3,True)
    c.line([(1660,478),(1660,438)],TEAL,3,True,dashed=True)
    c.text(1680,435,'公开包下载',19,TEAL)
    c.rect(60,737,930,515,'#e9f4f1',radius=18)
    c.text(84,755,'数据平面 A：端到端加密同步',28,TEAL,True)
    box(c,86,824,400,238,'B03  同步网关','Push / Pull（路由待冻结）\nop_id / epoch 去重\nserver_seq / cursor / ACK\n拒绝旧 epoch；不解密正文',TEAL,22)
    box(c,548,824,416,238,'PostgreSQL / 密文事件','版本修订 / 复习事件\n加密包装 / 墓碑 / 游标\n客户端解密、校验、事务落库\n不收识别图片 / 本机历史',TEAL,22)
    c.line([(489,937),(536,937)],TEAL,3,True)
    c.line([(310,680),(310,705),(73,705),(73,801),(286,801),(286,812)],TEAL,3,True)
    c.line([(950,680),(950,705),(976,705),(976,801),(756,801),(756,812)],TEAL,3,True)
    c.block(87,1103,'客户端保存 outbox 并在持久 ACK 后推进；冲突头与复习重放按契约处理。服务端无法代做私有公式语义校验。',870,23,TEAL,line_height=34,bottom=1238)
    c.rect(1030,737,950,515,'#f0ebf8',radius=18)
    c.text(1054,755,'数据平面 B：逐次授权云识别',28,PURPLE,True)
    box(c,1056,824,398,194,'B04  识别任务 API','POST 创建 / GET 查询\nPOST cancel；owner 隔离\n图像 hash / 授权 / 预算',PURPLE,22)
    box(c,1515,824,439,194,'B05  受限 worker','任务状态 / 供应商白名单\n供应商密钥仅在服务端\n响应预算；候选视为不可信',PURPLE,22)
    c.line([(1457,916),(1503,916)],PURPLE,3,True)
    c.line([(1980,352),(2005,352),(2005,708),(1968,708),(1968,801),(1254,801),(1254,812)],PURPLE,3,True)
    box(c,1056,1060,398,164,'B06  幂等 / 配额 / 费用','同键换图 409；预留与结算\nUNKNOWN 不自动重复付费',PURPLE,22)
    box(c,1515,1060,439,164,'外部视觉供应商','授权图像会以明文用于推理\n上游留存政策必须另行核实',PURPLE,22)
    c.line([(1734,1018),(1734,1048)],PURPLE,3,True)
    c.line([(1254,1018),(1254,1048)],PURPLE,3,True)
    box(c,60,1302,930,214,'B08  服务运维 / 安全 / 备份恢复','TLS、限流、参数化查询、容量 / 成本控制、依赖审计\nPostgreSQL / 受控存储备份与恢复；重放账户删除清单\nRPO / RTO 为验收目标，不是已完成能力',TEAL,23)
    box(c,1030,1302,950,214,'B07  临时图 / 结果 / 费用墓碑清理','终态清图目标 ≤60s；崩溃 TTL ≤1h；结果 ≤24h\n最小费用墓碑初始 30 天；媒体正文不进日志 / APM / 备份\n本机 N 次保留、网关 TTL 和供应商留存是三个不同边界',PURPLE,23)
    c.line([(1505,1252),(1505,1290)],PURPLE,3,True)
    c.rect(60,1570,1920,164,'#e8edf5',radius=18)
    c.text(84,1585,'实现边界',27,bold=True)
    c.block(84,1634,'后台内部物理子目录、同步 HTTP 路由和部署配置尚未冻结；图示只给出设计职责。公开内容发布为后台配套工作，不要求新增私有微服务；不把现有文档检查脚本当作应用后端。',1865,24,line_height=35,bottom=1728)
    return c.save('backend-module-map')

ARCH_MERMAID = '''flowchart TB
    accTitle: 预计功能到规划代码模块的分层映射
    accDescr: 所有应用节点都尚未实现。页面通过应用用例和端口调用适配器，FFI连接Rust服务，纯核心无I/O；云能力由server提供。
    U[编辑 / 库 / 计算 / 代入 / 复习 / 识别 / 账户 / 包管理] --> P[presentation/ 页面与ViewModel]
    P --> A[application/ 共享用例与端口]
    C[composition/ 账户作用域与依赖装配] -. 装配 .-> A
    A --> D[adapters/ 平台 / HTTP / FFI / FormulaView]
    D --> F[fml-ffi 版本化DTO与任务边界]
    F --> K[fml-core: ast / latex / types / units / eval / study]
    F --> S[fml-store: 加密仓储 / 历史 / 任务 / outbox]
    F --> R[fml-recognition: 解码 / 增强 / 本地模型 / 候选校验]
    F --> B[fml-assets: 验签 / 解包 / 激活 / 回退]
    D --> O[Android / Windows 原生端口: 文件 / 密钥 / 通知 / 生命周期]
    D --> V[server/: 身份 / 密文同步 / 云识别 / 配额 / 审计]
    T[tools/content/: 来源 / 校验 / 双审 / 签名] --> B
    R -. 语义检查 .-> K
    B -. 内容校验 .-> K
    classDef future fill:#fff2d7,stroke:#b78027,color:#3e3423;
    class U,P,A,C,D,F,K,S,R,B,O,V,T future;'''
BACK_MERMAID = '''flowchart LR
    accTitle: 后台专属职责及安全边界
    accDescr: 全部待实现。同步服务只持有密文，云识别需逐次授权并使用临时明文，公开包分发独立于私有同步。B编号仅是本图职责标签。
    CLI[注册客户端: 门禁 / 授权 / E2EE / 恢复] --> ID[B01 身份 / OIDC / token与owner]
    CLI --> KEY[B02 加密包装 / 设备 / epoch / 删除]
    CLI <-->|密文 Push/Pull| SY[B03 同步网关 / ACK / cursor]
    KEY --> DB[(PostgreSQL: 包装 / 密文 / 事件 / 墓碑)]
    SY --> DB
    CLI -->|逐次确认图像hash| API[B04 云识别job API]
    API --> COST[B06 幂等 / 配额 / 费用审计]
    API --> WK[B05 受限worker / 供应商适配]
    WK --> UP[外部视觉供应商: 临时图明文]
    API --> TEMP[(受控临时图 / 结果)]
    WK --> TEMP
    TEMP --> GC[B07 TTL / 清理 / 最小费用墓碑]
    OPS[B08 运维 / 备份 / 恢复演练] -. 保障 .-> DB
    CONTENT[tools/content/ 审校与签名] --> PUB[B09 公开包 / TUF元数据分发]
    PUB --> ASSET[客户端 fml-assets]
    classDef future fill:#fff2d7,stroke:#b78027,color:#3e3423;
    class CLI,ID,KEY,SY,DB,API,COST,WK,UP,TEMP,GC,OPS,CONTENT,PUB,ASSET future;'''


def md_link(path, label=None, start=None, end=None):
    target = Path(path)
    relative = Path(__import__('os').path.relpath(ROOT/target, SADD)).as_posix()
    anchor = f'#L{start}' + (f'-L{end}' if end and end != start else '') if start else ''
    return f'[{label or target.name}](<{relative}{anchor}>)'

def source_md(s):
    return md_link(s['path'], f"{Path(s['path']).stem.split('-')[0]}:{s['start']}–{s['end']}", s['start'],s['end'])

def sources_md(obj):
    vals=[obj['source']]+obj.get('additional_sources',[])
    if obj.get('historical'):
        vals.append(obj['historical'])
    return ' / '.join(source_md(s) for s in vals)

def cell(value):
    return str(value).replace('|','／').replace('\n','<br>')

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(cell(v) for v in r)+' |' for r in rows])

def report():
    p = []
    add=p.append
    add('# 预计功能与代码模块映射（v3）')
    add(f"\n_审计日期：{DATA['date']} · main 基线：{DATA['audit_commit']} · 文档映射，不是实现交付_\n")
    add('## 1. 结论与阅读方式\n')
    add('**当前仓库没有 Flutter 应用、Rust 核心或服务端源码。下列所有产品模块都是规划，不能描述成“已有后端、只缺前端”。** 现有应用外代码是文档一致性检查；公式 JSON 是三条研究输入，而非可运行的生产课程库。')
    add('效力依据：'+md_link('SADD/README.md','文档状态说明',9,11)+'、'+md_link('SADD/00-需求基线与文档效力-v3.md','v3 文档效力',9,13)+'、'+md_link('SADD/10-软件架构设计-v3.md','未来目录说明',66,83)+'。')
    add('覆盖现行矩阵 **R01–R31、H01–H02、A01–A04，共 37 项**；另拆出 **14 项平台/客户端细化职责**和 **9 组后台及后台配套职责**。D/B 编号仅为本报告导航，不新增需求，不等于物理目录。这里的 A 编号不是 09 复审缺陷编号。')
    add('完整离线可筛选图表：'+md_link('SADD/功能代码映射图.html','打开 HTML 图表')+'；结构化源：'+md_link('SADD/resources/feature-code-map.json','JSON 映射数据')+'；可复现生成器：'+md_link('tools/generate-feature-map.py','图表生成器')+'。')
    add('## 2. 功能—模块总览图\n')
    add('!'+md_link('SADD/diagrams/feature-module-map.png','预计功能与规划模块总览图'))
    add(md_link('SADD/diagrams/feature-module-map.svg','矢量总览图')+'。每行是职责对应关系，不表示每个功能必须联网。')
    add('### 2.1 分层调用关系（全部待实现）\n')
    add('页面不得绕过应用层直接访问数据库/HTTP；**仅 fml-core 绝对无 I/O**，其他基础设施按职责执行 I/O。成熟 FormulaView 渲染库接在适配器一侧，不由 Rust 自研排版。')
    add('\nmermaid\n'+ARCH_MERMAID+'\n')
    add('## 3. 预计代码模块目录与职责\n')
    add('前 11 个目录由 v3 主设计明确提出；**这些目录当前均不存在**。平台、工程和实验 3 项只列逻辑职责，不编造 *.dart / *.rs / server 子目录。纯核心内部子模块名称不表示已拆成独立 crate。')
    add(table(['标记','模块','预计目录（非现存）','对应职责','当前状态'],[[m['id'],m['name'],''+m['path']+'' if m['path'] else '未冻结物理目录／逻辑职责',m['responsibility'],m['status']] for m in DATA['modules']]))
    add('端口 / ABI 契约来源：'+md_link('SADD/10-软件架构设计-v3.md','10:85–105',85,105)+'。submit/poll/cancel、句柄 generation、缓冲所有权、线程模型需先过 M0 原型；鸿蒙只预留 C ABI，不等于已适配完整客户端。')
    add('## 4. 全量需求—模块—验收追踪\n')
    add('状态里的“规范已有 / 样例已有 / 预案分支已有”只表示文档或研究工件存在，**没有任何一项可据此记为产品实现通过**。模块标记见上一节。里程碑是建议主要落点，不是已排工期或已完成阶段。')
    add(table(['编号 / 预计功能','模块映射','接口面 / 里程碑','状态','实现边界 / 待做内容','验收引用 / 来源'],[[r['id']+' '+r['title'],' / '.join(r['modules']),r['surface']+' / '+r['milestone'],r['status'],r['note'],' / '.join(r['tests'])+' · '+sources_md(r)] for r in DATA['requirements']]))
    add('验收 ID 的详细场景与指标统一见 '+md_link('SADD/13-需求追踪与验收-v3.md','现行需求追踪与验收')+'；T-* 为未来验收项，不是当前自动测试结果。')
    add('## 5. 平台与客户端细化映射（补齐不显眼的功能）\n')
    add('以下仍全部待实现。v3 来源为当前约束；列出的 v2 平台章节仅补充未冲突细节，不能将旧候选方案、可选功能或目标参数升级为冻结必需能力。')
    add(table(['编号 / 子功能','关联需求 / 预计模块','待实现职责','当前边界 / 来源'],[[d['id']+' '+d['title'],d['reqs']+'<br>'+' / '.join(d['modules']),d['contract'],d['scope']+'<br>'+sources_md(d)] for d in DATA['client_details']]))
    add('## 6. 后台专属与后台配套映射（全部未实现）\n')
    add('这部分即使没有独立页面，也不能从功能映射中漏掉。B01–B08 位于预计 server/ 的逻辑模块及其运维支撑；B09 是离线发布工具链和公开分发配套，并不表示要再建一个私有微服务。')
    add('!'+md_link('SADD/diagrams/backend-module-map.png','后台专属能力与安全边界图'))
    add(md_link('SADD/diagrams/backend-module-map.svg','后台矢量图'))
    add('\nmermaid\n'+BACK_MERMAID+'\n')
    add(table(['职责编号 / 能力','关联需求 / 模块','数据流','必须实现的契约','验收 / 来源'],[[b['id']+' '+b['title'],b['reqs']+'<br>'+' / '.join(b['modules']),b['flow'],b['contract'],b['tests']+' · '+sources_md(b)] for b in DATA['backend']]))
    add('### 6.1 已设计但尚未实现的云识别路由\n')
    add(table(['方法','路由','职责'],[['POST','/v1/recognition/jobs','创建作业；校验账户/按次授权/image hash/幂等与配额'],['GET','/v1/recognition/jobs/{job_id}','查询既有作业；重启先查询，不自动重复提交'],['POST','/v1/recognition/jobs/{job_id}/cancel','取消请求；不保证供应商未执行/未计费']]))
    add('同步仅冻结 Push/Pull 语义，未冻结 HTTP URI；本报告不发明同步、登录、包发布或账户删除的路由。云识别图像会发给供应商：**同步 E2EE 不覆盖云推理明文**。')
    add('### 6.2 不能混淆的三个数据生命周期\n')
    add(table(['边界','设计保留策略','不代表什么'],[['本机识别历史','keep_last 整数 0–100，默认5；按开始序号留全部终态；N=0 终态只在内存展示','不等于服务端或供应商立即删除'],['自有云识别网关','终态清图目标≤60s、崩溃TTL≤1h、结果≤24h；最小费用墓碑初始30天','均为待验收目标；不是绝对擦除'],['外部供应商','政策与保留期限待核实、在按次授权中披露','不能由本机N或自有网关TTL代替上游保证']]))
    add('## 7. 现有工件与实现缺口\n')
    add(table(['现存文件','已经有什么','还不是什么'],[[md_link(a['path'],a['title']), '现存文档工具' if a['path'].startswith('tools/') else '现存研究／来源工件',a['note']] for a in DATA['artifacts']]))
    add('新增本报告、HTML、SVG/PNG、JSON 和生成器只完成**文档可视化与追踪交付**，不改变应用/服务端“未实现”的状态。没有新增 Flutter/Rust/服务 API、模型权重、数据库或生产资源包。')
    add('## 8. 历史设计冲突与范围边界\n')
    add(table(['主题','历史 v2 输入','本图采用的 v3 方案','来源'],[[x['topic'],x['old'],x['current'],sources_md(x)] for x in DATA['legacy']]))
    add('\n'+'\n'.join('- '+x for x in DATA['boundaries']))
    add('## 9. 预计落地顺序（非完成状态）\n')
    add(table(['阶段','主要目标','实现内容','重点需求'],DATA['milestones']))
    add('本地识别引擎、权重/训练数据许可、渲染依赖、Argon2id/SQLCipher 集成、课程教材版本/考试年份和云供应商政策仍需按设计冻结；没有实测不填性能/质量“通过”。里程碑依据 '+md_link('SADD/10-软件架构设计-v3.md','10:295–310',295,310)+'。')
    add('## 10. 检查范围与复现\n')
    add('生成器检查：37 项需求 ID 与现行矩阵一一对应、模块引用合法、12 组总览覆盖全部需求、文档来源存在及行范围有效、未来模块目录未落地；同时检查 SVG XML、PNG 结构与显式文本单元格溢出。')
    add('运行 python tools/generate-feature-map.py 重建文档图表，运行 node tools/verify-sadd.mjs 做既有文档一致性检查。需 Python＋Pillow＋Microsoft YaHei 字体；不下载库或联网。')
    add('这些检查不验证应用行为、数学推导、安全保证、性能、模型效果或所有浏览器渲染。本次另对生成的 PNG 进行视觉查看；不声称已渲染 Mermaid 或已验证在线 GUI 浏览器。')
    add('内容来源以工作区 v3 文档为主，历史平台文件作补充。仅确认 YOLO 预案分支存在；未切换、未审计该分支详细内容。')
    return ('\n\n'.join(p)+'\n').replace('',''*3).replace('',chr(96))

def html_source(s):
    relative=Path(__import__('os').path.relpath(ROOT/s['path'],SADD)).as_posix()
    label=Path(s['path']).stem.split('-')[0]+f":{s['start']}–{s['end']}"
    return f'<a href="{escape(relative)}#L{s["start"]}-L{s["end"]}" title="{escape(s["path"])}">{escape(label)}</a>'

def html_sources(obj):
    vals=[obj['source']]+obj.get('additional_sources',[])
    if obj.get('historical'): vals.append(obj['historical'])
    return ' / '.join(html_source(s) for s in vals)

def htable(headers,rows,ident):
    return '<div class="table-scroll"><table id="'+ident+'"><thead><tr>'+''.join('<th scope="col">'+escape(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def html_report(figures):
    e=escape
    badges=lambda ids: ' '.join('<span class="tag">'+e(x)+'</span>' for x in ids)
    reqrows=[[f'<strong>{e(r["id"])}</strong><br>{e(r["title"])}',badges(r['modules']),e(r['surface'])+'<br>'+e(r['milestone']),'<span class="pending">'+e(r['status'])+'</span>',e(r['note']),e(' / '.join(r['tests']))+'<br>'+html_sources(r)] for r in DATA['requirements']]
    modrows=[[badges([m['id']])+e(m['name']),'<code>'+e(m['path'])+'</code>' if m['path'] else '逻辑职责；目录未冻结',e(m['responsibility']),'<span class="pending">'+e(m['status'])+'</span>'] for m in DATA['modules']]
    brows=[[f'<strong>{e(b["id"])}</strong> '+e(b['title']),e(b['reqs'])+'<br>'+badges(b['modules']),e(b['flow']),e(b['contract']),e(b['tests'])+'<br>'+html_sources(b)] for b in DATA['backend']]
    drows=[[f'<strong>{e(d["id"])}</strong> '+e(d['title']),e(d['reqs'])+'<br>'+badges(d['modules']),e(d['contract']),e(d['scope'])+'<br>'+html_sources(d)] for d in DATA['client_details']]
    lrows=[[e(x['topic']),e(x['old']),e(x['current']),html_sources(x)] for x in DATA['legacy']]
    arows=[['<a href="'+e(Path(__import__('os').path.relpath(ROOT/a['path'],SADD)).as_posix())+'">'+e(a['title'])+'</a>',e(a['note'])] for a in DATA['artifacts']]
    stats=[('37','现行需求逐项覆盖'),('14','预计模块 / 职责'),('9','后台及配套职责'),('0','已实现产品模块')]
    sections=[]
    for f,title,caption in [(figures[0],'功能 → 模块总览','每行是一组对应关系；同一功能并非都需要联网。'),(figures[1],'后台职责与数据边界','所有后台能力均未实现。E2EE 同步、临时明文推理和公开包分发分开理解。')]:
        svg=(ROOT/f['svg']).read_text(encoding='utf-8')
        prefix=Path(f['svg']).stem
        svg=svg.replace('id="title"',f'id="{prefix}-title"').replace('id="desc"',f'id="{prefix}-desc"').replace('aria-labelledby="title desc"',f'aria-labelledby="{prefix}-title {prefix}-desc"')
        name=Path(f['svg']).name
        sections.append('<section id="'+('overview' if f is figures[0] else 'backend-figure')+'"><h2>'+title+'</h2><p>'+caption+'</p><figure class="diagram">'+svg+'</figure><p><a download href="diagrams/'+name+'">下载 SVG</a> · <a download href="diagrams/'+name.replace('.svg','.png')+'">下载 PNG</a></p></section>')
    css='''*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#20334e;font-family:"Microsoft YaHei",system-ui,sans-serif;line-height:1.65}main{max-width:1600px;margin:auto;padding:42px 30px 70px}header{border-bottom:1px solid #dbe3ef;padding-bottom:24px}h1{font-size:clamp(28px,3vw,44px);margin:0 0 8px;letter-spacing:.02em}h2{font-size:27px;margin:0 0 12px}p{margin:10px 0}.meta,small{color:#62728a}.warning{background:#fff2d7;color:#795014;border-left:5px solid #bd8a2e;padding:16px 20px;margin:24px 0;border-radius:8px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}.stat{background:white;border:1px solid #dbe3ef;border-radius:12px;padding:18px 22px}.stat b{font-size:36px;display:block;color:#205ea3}.stat span{color:#62728a}nav{display:flex;gap:8px 16px;flex-wrap:wrap;margin:20px 0}a{color:#205ea3;text-underline-offset:3px}section{margin:44px 0}.diagram{margin:18px 0 8px;border:1px solid #dbe3ef;border-radius:12px;background:white;overflow:auto}.diagram svg{display:block;width:100%;height:auto;min-width:960px}.table-scroll{overflow:auto;border:1px solid #dbe3ef;border-radius:10px;background:white;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px;min-width:1040px}th,td{text-align:left;vertical-align:top;padding:15px 14px;border-bottom:1px solid #e5ebf3}th{background:#20334e;color:white;white-space:nowrap}tbody tr:nth-child(even){background:#f6f8fc}td:first-child{min-width:165px}td:nth-last-child(2){min-width:230px}td:last-child{min-width:160px}code{font-family:Consolas,monospace;overflow-wrap:anywhere;color:#16726b}.tag{display:inline-block;padding:2px 7px;background:#e9f0fa;color:#205ea3;border-radius:5px;font-size:12px;margin:1px}.pending{display:inline-block;color:#795014;background:#fff2d7;border-radius:5px;padding:2px 6px}label{font-weight:700}input{font:inherit;width:min(100%,720px);display:block;margin-top:10px;padding:12px 16px;border:1px solid #aabbd3;border-radius:8px;background:white}.filterinfo{color:#62728a;font-size:14px}footer{margin-top:40px;border-top:1px solid #dbe3ef;padding-top:20px;color:#62728a}ul{padding-left:24px}li{margin:8px 0}@media(max-width:760px){main{padding:24px 16px}.stats{grid-template-columns:repeat(2,1fr)}.stat{padding:12px 16px}h2{font-size:23px}}@media print{body{background:white}main{max-width:none;padding:0}nav,.filterbar{display:none}.diagram svg{min-width:0}.table-scroll{overflow:visible}table{min-width:0;font-size:9px}th,td{padding:5px}section{break-inside:auto}.stats{grid-template-columns:repeat(4,1fr)}a{color:inherit}}'''
    js='''const search=document.getElementById('query');const groups=['requirements','modules','backend','client','legacy'];function apply(){const q=search.value.trim().toLocaleLowerCase();let count=0;for(const id of groups){for(const row of document.querySelectorAll('#'+id+' tbody tr')){const show=!q||row.textContent.toLocaleLowerCase().includes(q);row.hidden=!show;if(id==='requirements'&&show)count++;}}document.getElementById('match-count').textContent='需求匹配：'+count+' / 37。筛选同时作用于模块、后台、平台细项和历史差异表；总览图保持完整。';}search.addEventListener('input',apply);document.getElementById('clear-query').addEventListener('click',()=>{search.value='';apply();search.focus();});apply();'''
    return '<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>'+e(DATA['title'])+'</title><style>'+css+'</style></head><body><main><header><h1>预计功能—代码模块映射</h1><p class="meta">BubeiGongshi · '+e(DATA['date'])+' · main@'+e(DATA['audit_commit'])+' · 离线、无外部资源</p><p>覆盖原始需求、历史扩展、架构约束，以及没有独立页面的后台职责。v3 优先于历史 v2；目录和接口均区分“设计”与“实现”。</p></header><aside class="warning"><strong>当前没有应用或服务端实现。</strong> 预计 apps/flutter/、crates/、server/、tools/content/ 均未落地。文档校验脚本和三条研究样例不是业务后端，也不构成已发布公式库。</aside><div class="stats">'+''.join('<div class="stat"><b>'+v+'</b><span>'+t+'</span></div>' for v,t in stats)+'</div><nav aria-label="图表导航"><a href="#overview">功能总览图</a><a href="#module-section">模块目录</a><a href="#requirement-section">完整需求</a><a href="#client-section">平台细化</a><a href="#backend-figure">后台图</a><a href="#backend-section">后台清单</a><a href="#legacy-section">历史差异</a><a href="14-功能与代码模块映射-v3.md">Markdown 完整报告</a><a href="resources/feature-code-map.json">JSON 源数据</a></nav><div class="filterbar"><label for="query">筛选全部映射表（编号 / 功能 / 模块 / 关键字）</label><input id="query" type="search" placeholder="例如：R22、云识别、STORE、恢复、B07" autocomplete="off"><button type="button" id="clear-query">清除筛选</button><p id="match-count" class="filterinfo" aria-live="polite"></p></div>'+sections[0]+'<section id="module-section"><h2>规划模块与预计目录</h2><p>11 个未来物理目录来自现行主设计；平台、工程、实验仅列逻辑职责。所有产品模块待实现，避免虚构源码文件。</p>'+htable(['模块','预计目录（非现存）','职责','状态'],modrows,'modules')+'</section><section id="requirement-section"><h2>37 项全量需求追踪</h2><p>R01–R31 为原始需求，H01–H02 为历史扩展，A01–A04 为现行架构约束（不是复审缺陷编号）。T-* 是验收引用，不表示测试已通过；里程碑是建议主要落点。</p>'+htable(['需求','预计模块','接口面 / 阶段','当前状态','实现边界 / 待做','验收 / 来源'],reqrows,'requirements')+'</section><section id="client-section"><h2>平台和客户端细化职责</h2><p>全部待实现。v2 章节只补充未冲突细节；可选增强不升级为当前必须能力。</p>'+htable(['子功能','需求 / 模块','待实现职责','边界 / 来源'],drows,'client')+'</section>'+sections[1]+'<section id="backend-section"><h2>后台专属与配套职责（全部未实现）</h2><p>B01–B09 仅是本图的职责编号，不是新需求或物理模块；B09 包含离线发布与公开分发配套。同步 HTTP 路由未冻结，不额外发明 API。</p>'+htable(['后台职责','需求 / 模块','数据流','契约与待实现内容','验收 / 来源'],brows,'backend')+'<aside class="warning"><strong>三个保留边界互不替代：</strong>本机 N 次历史（0–100，默认5）、自有网关临时图/结果 TTL、供应商留存政策。所有时限是待验收目标，不承诺闪存/备份/上游绝对擦除。</aside></section><section><h2>现有工件不等于产品实现</h2>'+htable(['现有工件','用途与边界'],arows,'artifacts')+'</section><section id="legacy-section"><h2>历史设计冲突与当前边界</h2>'+htable(['主题','历史输入','现行 v3 方案','来源'],lrows,'legacy')+'<ul>'+''.join('<li>'+e(x)+'</li>' for x in DATA['boundaries'])+'</ul></section><section><h2>预计实现顺序（未完成）</h2>'+htable(['阶段','主要目标','实现内容','重点需求'],[[e(x) for x in row] for row in DATA['milestones']],'milestones')+'</section><footer><p>来源：工作区 SADD 现行 v3 文档与未冲突历史平台参考；源链接在 GitHub 可定位行号，本地 Markdown 阅读器未必支持 #L 锚点。</p><p>文档生成器只检查需求覆盖、引用、数据一致性及图形结构/布局；不验证应用行为、安全、数学正确性、性能或模型质量。新增这些图表不改变实现状态。YOLO 仅确认预案分支存在，未审计分支详细内容。</p></footer></main><script>'+js+'</script></body></html>\n'

def expand_ids(value):
    # Normalize a display range such as R10–R12 and retain separate H/A namespaces.
    result=set()
    for prefix,a,prefix2,b in re.findall(r'([RHA])(\d{2})[–-]([RHA])?(\d{2})', value):
        assert not prefix2 or prefix==prefix2
        result.update(prefix+f'{n:02}' for n in range(int(a),int(b)+1))
    result.update(re.findall(r'[RHA]\d{2}',value))
    return result

def validate_data():
    reqs=DATA['requirements']
    ids=[x['id'] for x in reqs]
    expected={f'R{i:02}' for i in range(1,32)}|{'H01','H02','A01','A02','A03','A04'}
    assert len(ids)==len(set(ids))==37 and set(ids)==expected
    source=(SADD/'13-需求追踪与验收-v3.md').read_text(encoding='utf-8')
    actual=set(re.findall(r'^\| ([RHA]\d{2}) \|',source,re.M))
    assert set(ids)==actual
    assert len(DATA['modules'])==14 and len(MODULES)==14
    defined_tests=set(re.findall(r'^\| (T-[A-Z]+) \|',source,re.M))
    count=0
    for obj in reqs+DATA['backend']+DATA['client_details']+DATA['legacy']:
        assert set(obj.get('modules',[]))<=set(MODULES),obj
        tests=obj.get('tests',[])
        if isinstance(tests,str): tests=re.findall(r'T-[A-Z]+',tests)
        assert set(tests)<=defined_tests,(obj.get('id'),tests)
        srcs=[obj['source']]+obj.get('additional_sources',[])
        if obj.get('historical'): srcs.append(obj['historical'])
        for s in srcs:
            file=ROOT/s['path']
            assert file.is_file(),s
            lines=file.read_text(encoding='utf-8').splitlines()
            assert 1<=s['start']<=s['end']<=len(lines),s
            count+=1
    group_ids=set().union(*(expand_ids(g['ids']) for g in DATA['groups']))
    assert group_ids==expected,('Overview coverage mismatch',expected-group_ids,group_ids-expected)
    paths=[m['path'] for m in DATA['modules'] if m['path']]
    assert len(paths)==11
    assert not any((ROOT/p).exists() for p in paths),'Update implementation-status audit before rebuilding.'
    for a in DATA['artifacts']: assert (ROOT/a['path']).is_file()
    return {'requirements':len(reqs),'module_responsibilities':len(MODULES),'planned_absent_directories':len(paths),'overview_groups':len(DATA['groups']),'backend_responsibilities':len(DATA['backend']),'platform_details':len(DATA['client_details']),'source_ranges_checked':count,'acceptance_ids_defined':len(defined_tests),'product_implementation_status':'not implemented'}

def main():
    evidence=validate_data()
    figures=[overview(),backend()]
    (SADD/'14-功能与代码模块映射-v3.md').write_text(report(),encoding='utf-8')
    # Separate tags so generated tables stay readable by line-oriented tools.
    page=html_report(figures).replace('><', '>\n<')
    assert '<script src=' not in page and 'http' not in page.split('<style>')[1].split('</style>')[0]
    (SADD/'功能代码映射图.html').write_text(page,encoding='utf-8')
    evidence['figures']=figures
    evidence['scope']='Documentation mapping and graphics checks only; no product test or security/performance claim.'
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
