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
    ("玄空飞星排盘.html",  "paipan.html",   "排盘"),
    ("炁流场3D.html",      "qiflow.html",   "炁流场"),
    ("外环境立极尺.html",  "waihuan.html",  "立极尺"),
    ("八字命书.html",      "bazi.html",     "命书"),
    ("合盘.html",          "hepan.html",    "合盘"),
    ("六爻纳甲.html",      "liuyao.html",   "六爻"),
    ("寻炁-技术拆解.html", "research.html", "竞品拆解"),
]
RENAME = {src: dst for src, dst, _ in PAGES}

NAV_CSS = """
nav.site{display:flex;gap:2px;margin-left:auto;align-items:center;flex-wrap:wrap}
nav.site a{font-size:11.5px;letter-spacing:.1em;color:#9A8F78;text-decoration:none;
  padding:4px 10px;border-radius:2px;white-space:nowrap}
nav.site a:hover{color:var(--brass)}
nav.site a[aria-current="page"]{color:var(--lacquer);background:var(--brass);font-weight:600}
header .sub{display:none}"""


def nav_html(current, ascii_href=True):
    """整站唯一的导航来源 —— 加一页只需改 PAGES。

    ascii_href=True  给 site/ 用（同目录 ASCII 名）
    ascii_href=False 给源文件用（同目录中文名，门户在 site/ 下）
    """
    home = "./" if ascii_href else "site/index.html"
    out = [f'<nav class="site"><a href="{home}">门户</a>']
    for src, dst, label in PAGES:
        href = dst if ascii_href else src
        cur = ' aria-current="page"' if current in (src, dst) else ''
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out) + "</nav>"


def put_nav(text, nav):
    """整块替换已有导航；没有就插到 </header> 前。幂等。"""
    if re.search(r'<nav class="site">', text):
        return re.sub(r'<nav class="site">.*?</nav>', lambda _: nav, text, flags=re.S)
    return text.replace("</header>", nav + "</header>", 1)


def ensure_nav_css(text):
    if "nav.site{" not in text:
        i = text.rindex("</style>")
        return text[:i] + NAV_CSS + "\n" + text[i:]
    return text


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
    for src, dst, _ in PAGES:
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
