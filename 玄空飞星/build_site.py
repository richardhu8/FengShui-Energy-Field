#!/usr/bin/env python3
"""从源文件确定性地生成 site/ 发布副本。

源文件用中文名（便于本机阅读），GitHub Pages 用 ASCII 名（避免 URL 编码）。
此前 site/ 是手工改的，规则逐文件不一致 —— 外环境立极尺.html 的导航停在 5 项、
炁流场3D.html 缺 nav.site 样式，都是漏改。改为脚本生成后不再有这类漂移。

用法：python3 build_site.py        （加 --check 只报差异、不写盘，供 CI 用）
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).parent
SITE = ROOT / "site"

# 源文件 → 发布名 · 导航标题；顺序即导航顺序
PAGES = [
    ("玄空飞星排盘.html",  "paipan.html",   "排盘",   "玄空飞星 · 八宅 · 户型缺角 · 天时"),
    ("炁流场3D.html",      "qiflow.html",   "炁流场", "三维测地可达性 · 各宫炁强度"),
    ("外环境立极尺.html",  "waihuan.html",  "立极尺", "地图量朝向轴 · 直读二十四山"),
    ("八字命书.html",      "bazi.html",     "命书",   "四柱 · 十神 · 大运流年 · 真太阳时"),
    ("合盘.html",          "hepan.html",    "合盘",   "两造刑冲合害 · 只列关系"),
    ("六爻纳甲.html",      "liuyao.html",   "六爻",   "铜钱起卦 · 八宫世应 · 六亲六神"),
    ("寻炁-技术拆解.html", "research.html", "竞品拆解", "技术栈与术数引擎的对照分析"),
]
RENAME = {src: dst for src, dst, *_ in PAGES}

NAV_CSS = """
/* 顶栏：← 门户 | 模块名 | 副标题 …… 导航（右对齐），与竞品同构。
   页面原有的 .name（「飞星盘」等）与 modname 重复，故一并隐去。 */
header .name{display:none}
.topbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;flex:1;min-width:0}
.topbar .back{font-size:11.5px;letter-spacing:.08em;color:#9A8F78;text-decoration:none;
  padding:3px 9px;border:1px solid rgba(154,143,120,.35);border-radius:2px;white-space:nowrap}
.topbar .back:hover{color:var(--brass);border-color:var(--brass)}
.topbar .modname{font-family:"Songti SC","STSong",SimSun,serif;font-size:16px;letter-spacing:.16em;
  color:var(--lacquer);background:var(--brass);padding:3px 11px;border-radius:2px;white-space:nowrap}
.topbar .modsub{font-size:11px;color:#7E7562;letter-spacing:.06em;white-space:nowrap}
nav.site{display:flex;gap:2px;margin-left:auto;align-items:center;flex-wrap:wrap}
nav.site a{font-size:11.5px;letter-spacing:.1em;color:#9A8F78;text-decoration:none;
  padding:4px 10px;border-radius:2px;white-space:nowrap}
nav.site a:hover{color:var(--brass)}
nav.site a[aria-current="page"]{color:var(--lacquer);background:var(--brass);font-weight:600}
header .sub{display:none}
/* 长文页：顶栏单独成行，与下方标题块拉开 */
header .in{clear:both}
.topbar:has(+ .in){margin-bottom:14px;padding-bottom:12px;
  border-bottom:1px solid rgba(154,143,120,.18)}

/* 媒体块必须排在基础规则之后 —— 同特异度下后者胜出。
   先前把它插在 nav.site 基础规则之前，flex-wrap:nowrap 从未生效，
   窄屏 8 项导航仍折行，反把顶栏撑到 178px。 */
@media(max-width:760px){
  .topbar .modsub{display:none}
  .topbar{flex-wrap:nowrap;overflow:hidden;gap:8px}
  nav.site{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;
    scrollbar-width:none;mask-image:linear-gradient(90deg,#000 86%,transparent)}
  nav.site::-webkit-scrollbar{display:none}
}"""


def topbar_html(current, ascii_href=True):
    """工具页顶栏：← 门户 + 模块名 + 副标题。竞品有，我们此前只有一条导航。"""
    home = "./" if ascii_href else "site/index.html"
    for src, dst, label, sub in PAGES:
        if current in (src, dst):
            return (f'<span class="topbar"><a class="back" href="{home}">← 门户</a>'
                    f'<span class="modname">{label}</span>'
                    f'<span class="modsub">{sub}</span>')
    return '<span class="topbar">'


def nav_html(current, ascii_href=True):
    """整站唯一的导航来源 —— 加一页只需改 PAGES。

    ascii_href=True  给 site/ 用（同目录 ASCII 名）
    ascii_href=False 给源文件用（同目录中文名，门户在 site/ 下）
    """
    home = "./" if ascii_href else "site/index.html"
    out = [topbar_html(current, ascii_href), f'<nav class="site"><a href="{home}">门户</a>']
    for src, dst, label, _sub in PAGES:
        href = dst if ascii_href else src
        cur = ' aria-current="page"' if current in (src, dst) else ''
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out) + "</nav></span>"


def put_nav(text, nav):
    """整块替换已有导航；没有就插到 </header> 前。幂等。"""
    if re.search(r'<span class="topbar">', text):
        return re.sub(r'<span class="topbar">.*?</nav></span>', lambda _: nav, text, flags=re.S)
    if re.search(r'<nav class="site">', text):
        return re.sub(r'<nav class="site">.*?</nav>', lambda _: nav, text, flags=re.S)
    # 长文页（header 里包着 .in 的大标题块）：顶栏要放在标题之前，否则被压到
    # 正文标题下面，头部叠成 214px。其余页面 header 本身就是那条 flex 栏，
    # 顶栏追加在末尾即可。
    m = re.search(r'(<header[^>]*>)\s*(<div class="in">)', text)
    if m:
        return text[:m.start(2)] + nav + text[m.start(2):]
    return text.replace("</header>", nav + "</header>", 1)


CSS_BEGIN = "/*==NAV-CSS-BEGIN==*/"
CSS_END = "/*==NAV-CSS-END==*/"

def ensure_nav_css(text):
    """把导航样式装进带标记的块里，可反复替换。

    原实现是「没有 nav.site 就插入」—— 于是 NAV_CSS 一旦写进页面，
    以后再改就永远不会更新。加了 header .name{display:none} 却不生效，
    就是踩到这个。
    """
    block = CSS_BEGIN + NAV_CSS + "\n" + CSS_END
    if CSS_BEGIN in text:
        return re.sub(re.escape(CSS_BEGIN) + r".*?" + re.escape(CSS_END),
                      lambda _: block, text, flags=re.S)
    # 旧页面：先摘掉无标记的那份，再装新的
    if "nav.site{" in text:
        text = text.replace(NAV_CSS + "\n", "").replace(NAV_CSS, "")
        legacy = re.search(r"\nnav\.site\{.*?header \.sub\{display:none\}\n", text, re.S)
        if legacy:
            text = text[:legacy.start()] + "\n" + text[legacy.end():]
    i = text.rindex("</style>")
    return text[:i] + block + "\n" + text[i:]


def normalize_source(text, src):
    """源文件也要能本机直接打开 —— 导航同源、只是 href 用中文名。"""
    return put_nav(ensure_nav_css(text), nav_html(src, ascii_href=False))


def build(text, current):
    # 1. href 里的中文文件名 → ASCII（只改属性，注释与正文不动）
    def sub_href(m):
        q, url = m.group(1), m.group(2)
        return f'href={q}{RENAME.get(url, url)}{q}'
    text = re.sub(r'href=(["\'])([^"\']+)\1', sub_href, text)

    # 2~3. 补样式、统一导航
    return put_nav(ensure_nav_css(text), nav_html(current))


def sync_portal(check):
    """门户 index.html 是手写的，不由源文件生成 —— 但导航仍须同一来源。
    否则新增一页时门户会漏掉入口（六爻上线时就漏过）。"""
    f = SITE / "index.html"
    if not f.exists():
        return []
    raw = f.read_text(encoding="utf-8")
    fixed = put_nav(ensure_nav_css(raw), nav_html("index.html"))
    # 门户自身高亮「门户」
    fixed = fixed.replace('<nav class="site"><a href="./">门户</a>',
                          '<nav class="site"><a href="./" aria-current="page">门户</a>')
    if fixed == raw:
        print("  = index.html（门户导航）")
        return []
    print(f"  {'≠' if check else '↻'} index.html（门户导航）")
    if not check:
        f.write_text(fixed, encoding="utf-8")
    return ["index.html"]


def main():
    check = "--check" in sys.argv
    drift = []
    for src, dst, *_ in PAGES:
        s = ROOT / src
        if not s.exists():
            print(f"⚠ 源文件缺失，跳过：{src}"); continue
        raw = s.read_text(encoding="utf-8")
        fixed = normalize_source(raw, src)          # 源文件自身的导航也归一
        if fixed != raw:
            drift.append(src)
            print(f"  {'≠' if check else '↻'} {src}（源文件导航）")
            if not check:
                s.write_text(fixed, encoding="utf-8")
        built = build(fixed, dst)
        out = SITE / dst
        old = out.read_text(encoding="utf-8") if out.exists() else None
        if old == built:
            print(f"  = {dst}")
        else:
            drift.append(dst)
            print(f"  {'≠' if check else '↻'} {dst}" + ("（未同步）" if check else ""))
            if not check:
                out.write_text(built, encoding="utf-8")
    drift += sync_portal(check)
    if check and drift:
        print(f"\n❌ {len(drift)} 个发布副本与源文件不同步：{'、'.join(drift)}")
        print("   跑 python3 build_site.py 重新生成")
        return 1
    print(f"\n✅ site/ 已与源文件一致（{len(PAGES)} 页）" if not check else "\n✅ 全部同步")
    return 0


if __name__ == "__main__":
    sys.exit(main())
