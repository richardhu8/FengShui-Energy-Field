# -*- coding: utf-8 -*-
"""
玄空飞星下卦排盘 —— 参考实现（基准测试用）
输入：元运(1-9) + 向首方位角(0-360, 正北=0, 顺时针)
输出：运盘 / 山星盘 / 向星盘 / 格局判定

用途：给自研排盘引擎当 golden reference，不是生产代码。
"""
from __future__ import annotations
import json, csv, sys

# ---------- 常量 ----------
# 洛书飞泊路径：中 → 乾(西北) → 兑(西) → 艮(东北) → 离(南) → 坎(北) → 坤(西南) → 震(东) → 巽(东南)
PALACE_PATH = [5, 6, 7, 8, 9, 1, 2, 3, 4]

PALACE_NAME = {1: ("坎", "北"), 2: ("坤", "西南"), 3: ("震", "东"), 4: ("巽", "东南"),
               5: ("中", "中"), 6: ("乾", "西北"), 7: ("兑", "西"), 8: ("艮", "东北"),
               9: ("离", "南")}

# 二十四山：(名, 所属宫, 三元龙, 阴阳, 中心度数)
# 顺序自壬(345°)起，每山 15°
MOUNTAINS = [
    ("壬", 1, "地", "阳", 345.0), ("子", 1, "天", "阴",   0.0), ("癸", 1, "人", "阴",  15.0),
    ("丑", 8, "地", "阴",  30.0), ("艮", 8, "天", "阳",  45.0), ("寅", 8, "人", "阳",  60.0),
    ("甲", 3, "地", "阳",  75.0), ("卯", 3, "天", "阴",  90.0), ("乙", 3, "人", "阴", 105.0),
    ("辰", 4, "地", "阴", 120.0), ("巽", 4, "天", "阳", 135.0), ("巳", 4, "人", "阳", 150.0),
    ("丙", 9, "地", "阳", 165.0), ("午", 9, "天", "阴", 180.0), ("丁", 9, "人", "阴", 195.0),
    ("未", 2, "地", "阴", 210.0), ("坤", 2, "天", "阳", 225.0), ("申", 2, "人", "阳", 240.0),
    ("庚", 7, "地", "阳", 255.0), ("酉", 7, "天", "阴", 270.0), ("辛", 7, "人", "阴", 285.0),
    ("戌", 6, "地", "阴", 300.0), ("乾", 6, "天", "阳", 315.0), ("亥", 6, "人", "阳", 330.0),
]
BY_NAME = {m[0]: m for m in MOUNTAINS}

# 下卦/替卦门槛（度）：偏离山中心超过此值即入兼向替卦区。各派不一，此处可配置。
XIAGUA_HALF_WIDTH = 4.5


def norm(deg: float) -> float:
    return deg % 360.0


def mountain_of(deg: float):
    """方位角 → 所在山"""
    d = norm(deg)
    for m in MOUNTAINS:
        lo = norm(m[4] - 7.5)
        hi = norm(m[4] + 7.5)
        if lo < hi:
            if lo <= d < hi:
                return m
        else:  # 跨 0°
            if d >= lo or d < hi:
                return m
    raise ValueError(deg)


def offset_from_center(deg: float, m) -> float:
    o = norm(deg) - m[4]
    if o > 180:
        o -= 360
    if o < -180:
        o += 360
    return round(o, 3)


def fly(center_star: int, forward: bool) -> dict:
    """某星入中，顺飞/逆飞，返回 {宫位: 星}"""
    out = {}
    for i, p in enumerate(PALACE_PATH):
        step = i if forward else -i
        out[p] = (center_star - 1 + step) % 9 + 1
    return out


def yinyang_for_entry(entry_star: int, anchor_mountain) -> tuple[str, str]:
    """
    山星/向星入中后的顺逆判定：
    取 entry_star 所属宫中，与 anchor(坐山或向首) 同三元龙的那一山，用其阴阳。
    entry_star == 5 时 5 无本宫，依约定取 anchor 本山之阴阳。
    返回 (阴阳, 依据说明)
    """
    if entry_star == 5:
        return anchor_mountain[3], f"5入中无本宫，取{anchor_mountain[0]}本山之阴阳（约定 A）"
    yl = anchor_mountain[2]
    for m in MOUNTAINS:
        if m[1] == entry_star and m[2] == yl:
            return m[3], f"{entry_star}属{PALACE_NAME[entry_star][0]}宫，{yl}元龙为「{m[0]}」，{m[3]}"
    raise ValueError(entry_star)


def pan(yun: int, facing_deg: float) -> dict:
    facing = mountain_of(facing_deg)
    sitting = mountain_of(facing_deg + 180)

    off = offset_from_center(facing_deg, facing)
    is_xiagua = abs(off) <= XIAGUA_HALF_WIDTH

    yun_pan = fly(yun, True)

    shan_entry = yun_pan[sitting[1]]
    shan_yy, shan_why = yinyang_for_entry(shan_entry, sitting)
    shan_pan = fly(shan_entry, shan_yy == "阳")

    xiang_entry = yun_pan[facing[1]]
    xiang_yy, xiang_why = yinyang_for_entry(xiang_entry, facing)
    xiang_pan = fly(xiang_entry, xiang_yy == "阳")

    sp, fp = sitting[1], facing[1]
    shan_at_sit, shan_at_face = shan_pan[sp], shan_pan[fp]
    xiang_at_sit, xiang_at_face = xiang_pan[sp], xiang_pan[fp]
    if shan_at_sit == yun and xiang_at_face == yun:
        ge = "旺山旺向"
    elif shan_at_face == yun and xiang_at_face == yun:
        ge = "双星到向"
    elif shan_at_sit == yun and xiang_at_sit == yun:
        ge = "双星到坐"
    elif shan_at_face == yun and xiang_at_sit == yun:
        ge = "上山下水"
    else:
        ge = "非四正格"

    return {
        "元运": yun,
        "向度数": round(norm(facing_deg), 3),
        "坐山": sitting[0], "向首": facing[0],
        "坐向": f"{sitting[0]}山{facing[0]}向",
        "三元龙": sitting[2],
        "偏离山中心": off,
        "卦法": "下卦" if is_xiagua else f"替卦(兼向 {off:+.1f}°)",
        "山星入中": shan_entry, "山星飞法": "顺飞" if shan_yy == "阳" else "逆飞", "山星依据": shan_why,
        "向星入中": xiang_entry, "向星飞法": "顺飞" if xiang_yy == "阳" else "逆飞", "向星依据": xiang_why,
        "运盘": yun_pan, "山星盘": shan_pan, "向星盘": xiang_pan,
        "格局": ge,
    }


def render(p: dict) -> str:
    """九宫格文本渲染，按地图方位摆放（上南下北左东右西为传统罗盘，此处用上北下南便于对照屏幕）"""
    grid = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]  # 上南
    grid = [[8, 1, 6], [3, 5, 7], [4, 9, 2]]  # 上北：艮坎乾 / 震中兑 / 巽离坤
    lines = []
    for row in grid:
        c1 = " │ ".join(f"{PALACE_NAME[g][0]}{PALACE_NAME[g][1]:<3}" for g in row)
        c2 = " │ ".join(f"山{p['山星盘'][g]} 向{p['向星盘'][g]} 运{p['运盘'][g]}" for g in row)
        lines.append("  " + c1)
        lines.append("  " + c2)
        lines.append("  " + "─" * 34)
    return "\n".join(lines)


def liunian_center(year: int) -> int:
    """流年紫白中宫星：下元甲子(1984)七赤入中，逐年逆行"""
    return (7 - 1 - (year - 1984)) % 9 + 1


if __name__ == "__main__":
    # ---- 校验：视频中 App 的真实输出 ----
    p = pan(9, 209.5)
    print("== 校验用例：九运 / 向 209.5° ==")
    for k in ["坐向", "卦法", "山星入中", "山星飞法", "向星入中", "向星飞法", "格局"]:
        print(f"  {k}: {p[k]}")
    print(render(p))
    print(f"  2026 流年中宫: {liunian_center(2026)}")


# ══════════ 替卦（起星）══════════
# 替星口诀（山名 → 替星）；每山唯一，输出恒为 {1,2,6,7,9}
TIXING = {}
for _s, _ms in {1:"子癸甲申", 2:"壬卯乙未坤", 6:"乾亥辰巽巳戌", 7:"酉辛丑艮丙", 9:"寅午庚丁"}.items():
    for _m in _ms:
        TIXING[_m] = _s

def _tsub_entry(R, anchor):
    """替卦入中之数：R=运盘在anchor宫之星。R==5(廉贞)无替，仍用5；否则取R本宫中与anchor同元龙之山查替星。"""
    if R == 5:
        return 5, f"运星5(廉贞)入中，无替，仍用5"
    M = next(m for m in MOUNTAINS if m[1] == R and m[2] == anchor[2])
    return TIXING[M[0]], f"运星{R}→{PALACE_NAME[R][0]}宫{anchor[2]}元龙「{M[0]}」→替星{TIXING[M[0]]}"

def pan_ti(yun, facing_deg):
    """替卦排盘。顺逆同下卦（由 anchor 定），仅入中之数改用替星。"""
    F = mountainOf_py(facing_deg); S = mountainOf_py(facing_deg + 180)
    yun_pan = fly(yun, True)
    # 顺逆：与下卦同法，用运盘入中数 R 判
    Rs = yun_pan[S[1]]; sy, _ = yinyang_for_entry(Rs, S)
    Rx = yun_pan[F[1]]; xy, _ = yinyang_for_entry(Rx, F)
    # 入中之数：替星
    se, sw = _tsub_entry(Rs, S)
    xe, xw = _tsub_entry(Rx, F)
    shan_pan = fly(se, sy == "阳")
    xiang_pan = fly(xe, xy == "阳")
    return {"元运": yun, "坐向": f"{S[0]}山{F[0]}向", "坐山": S[0], "向首": F[0],
            "卦法": "替卦", "山星入中": se, "山星飞法": "顺飞" if sy=="阳" else "逆飞", "山星依据": sw,
            "向星入中": xe, "向星飞法": "顺飞" if xy=="阳" else "逆飞", "向星依据": xw,
            "运盘": yun_pan, "山星盘": shan_pan, "向星盘": xiang_pan}

# mountainOf 的模块内别名（供上面调用）
def mountainOf_py(d):
    return mountain_of(d)


# ══════════ 八宅明镜（游年变爻法）══════════
# 三爻 (初,二,三)=(下,中,上)，1=阳 0=阴
YAO = {1:(0,1,0), 2:(0,0,0), 3:(1,0,0), 4:(0,1,1),
       6:(1,1,1), 7:(1,1,0), 8:(0,0,1), 9:(1,0,1)}
BY_YAO = {v:k for k,v in YAO.items()}
YSEQ = [(2,"生气"),(1,"五鬼"),(0,"延年"),(1,"六煞"),
        (2,"祸害"),(1,"天医"),(0,"绝命"),(1,"伏位")]
JI4    = ["生气","延年","天医","伏位"]
XIONG4 = ["祸害","六煞","五鬼","绝命"]
EAST4  = {1,3,4,9}

def bazhai(zhai_palace):
    """宅卦洛书数 → {宫位: 游年名}。中宫(5)无宅卦，返回 None。"""
    if zhai_palace not in YAO:
        return None
    y = list(YAO[zhai_palace]); out = {}
    for i, name in YSEQ:
        y[i] ^= 1
        out[BY_YAO[tuple(y)]] = name
    return out

def is_east(palace):
    return palace in EAST4


# ══════════ 户型九宫覆盖（井字法）══════════
# 上北下南：row0=北 row2=南，col0=西 col2=东
PLAN_CELL = [[6,1,8],[7,5,3],[2,9,4]]

def poly_area(p):
    s = 0.0
    for i in range(len(p)):
        x1,y1 = p[i]; x2,y2 = p[(i+1) % len(p)]
        s += x1*y2 - x2*y1
    return abs(s)/2

def clip_rect(poly, x0, y0, x1, y1):
    """Sutherland–Hodgman：多边形对轴对齐矩形裁剪"""
    def stage(p, inside, inter):
        out = []
        for i in range(len(p)):
            a = p[i]; b = p[(i+1) % len(p)]
            ia, ib = inside(a), inside(b)
            if ia and ib: out.append(b)
            elif ia and not ib: out.append(inter(a,b))
            elif not ia and ib: out.append(inter(a,b)); out.append(b)
        return out
    ix = lambda a,b,X: (X, a[1] + (X-a[0])/(b[0]-a[0])*(b[1]-a[1]))
    iy = lambda a,b,Y: (a[0] + (Y-a[1])/(b[1]-a[1])*(b[0]-a[0]), Y)
    p = poly
    p = stage(p, lambda q: q[0] >= x0, lambda a,b: ix(a,b,x0));  
    if not p: return p
    p = stage(p, lambda q: q[0] <= x1, lambda a,b: ix(a,b,x1))
    if not p: return p
    p = stage(p, lambda q: q[1] >= y0, lambda a,b: iy(a,b,y0))
    if not p: return p
    p = stage(p, lambda q: q[1] <= y1, lambda a,b: iy(a,b,y1))
    return p

def plan_coverage(poly):
    """户型多边形 → {宫位: 覆盖率 0..1}。覆盖率 < 0.6 视为缺角（经验阈值）。"""
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    x0,x1,y0,y1 = min(xs), max(xs), min(ys), max(ys)
    w = (x1-x0)/3; h = (y1-y0)/3; cell_a = w*h
    cov = {}
    for r in range(3):
        for c in range(3):
            cx, cy = x0+c*w, y0+r*h
            clipped = clip_rect(poly, cx, cy, cx+w, cy+h)
            cov[PLAN_CELL[r][c]] = poly_area(clipped)/cell_a if cell_a else 0.0
    return cov


# ══════════ 立极点与中心放射法 ══════════
import math as _math

def signed_area(p):
    return sum(p[i][0]*p[(i+1)%len(p)][1] - p[(i+1)%len(p)][0]*p[i][1]
               for i in range(len(p))) / 2

def centroid(p):
    """多边形面积形心（非外接矩形中心）"""
    A = signed_area(p)
    if abs(A) < 1e-12: return None
    cx = cy = 0.0
    for i in range(len(p)):
        x1,y1 = p[i]; x2,y2 = p[(i+1)%len(p)]
        cr = x1*y2 - x2*y1
        cx += (x1+x2)*cr; cy += (y1+y2)*cr
    return (cx/(6*A), cy/(6*A))

def clip_half(poly, cx, cy, nx, ny):
    """半平面裁剪，保留 (p-c)·n >= 0"""
    f = lambda q: (q[0]-cx)*nx + (q[1]-cy)*ny
    out = []
    for i in range(len(poly)):
        a = poly[i]; b = poly[(i+1)%len(poly)]
        fa, fb = f(a), f(b)
        if fa >= 0 and fb >= 0: out.append(b)
        elif fa >= 0 > fb:
            t = fa/(fa-fb); out.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])))
        elif fa < 0 <= fb:
            t = fa/(fa-fb); out.append((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))); out.append(b)
    return out

def _dir(theta):
    """方位角 → 单位向量。屏幕坐标 y 向下：0°=北=(0,-1)，顺时针"""
    r = _math.radians(theta)
    return (_math.sin(r), -_math.cos(r))

def sector_clip(poly, c, theta, span=45.0):
    """裁出以 c 为心、theta 为中线、span 度的扇区部分"""
    d0 = _dir(theta - span/2); d1 = _dir(theta + span/2)
    p = clip_half(poly, c[0], c[1], -d0[1],  d0[0])
    if not p: return p
    return clip_half(p, c[0], c[1],  d1[1], -d1[0])

# 八方中线角（宫位洛书数 → 方位角）
RADIAL_DIR = {1:0, 8:45, 3:90, 4:135, 9:180, 2:225, 7:270, 6:315}

def radial_coverage(poly):
    """中心放射法：自面积形心作 8 个 45° 扇区。
    覆盖率 = 该扇区内户型面积 / 同扇区内外接矩形面积
    （以外接矩形为基准，方正户型恒 100%，细长户型也不会误判）"""
    c = centroid(poly)
    xs = [q[0] for q in poly]; ys = [q[1] for q in poly]
    bb = [(min(xs),min(ys)),(max(xs),min(ys)),(max(xs),max(ys)),(min(xs),max(ys))]
    cov = {}
    for g, th in RADIAL_DIR.items():
        a = abs(signed_area(sector_clip(poly, c, th)))
        b = abs(signed_area(sector_clip(bb,   c, th)))
        cov[g] = a/b if b else 0.0
    return cov


# ══════════ 八字：十神 / 藏干 / 五行 ══════════
GAN10 = "甲乙丙丁戊己庚辛壬癸"
ZHI12 = "子丑寅卯辰巳午未申酉戌亥"
GAN_WX = [0,0,1,1,2,2,3,3,4,4]      # 0木 1火 2土 3金 4水
GAN_YY = [1,0,1,0,1,0,1,0,1,0]      # 1阳 0阴
WUXING = "木火土金水"
CANGGAN = {"子":"癸","丑":"己癸辛","寅":"甲丙戊","卯":"乙","辰":"戊乙癸","巳":"丙庚戊",
           "午":"丁己","未":"己丁乙","申":"庚壬戊","酉":"辛","戌":"戊辛丁","亥":"壬甲"}
# 藏干权重：本气 / 中气 / 余气
CANG_W = [1.0, 0.5, 0.3]

def shishen(day_gan, other_gan):
    """十神：以日主为我，判断另一天干的关系"""
    d = GAN10.index(day_gan); o = GAN10.index(other_gan)
    dw, ow = GAN_WX[d], GAN_WX[o]
    same = GAN_YY[d] == GAN_YY[o]
    if dw == ow:               return "比肩" if same else "劫财"
    if (dw+1) % 5 == ow:       return "食神" if same else "伤官"   # 我生
    if (dw+2) % 5 == ow:       return "偏财" if same else "正财"   # 我克
    if (ow+2) % 5 == dw:       return "七杀" if same else "正官"   # 克我
    if (ow+1) % 5 == dw:       return "偏印" if same else "正印"   # 生我
    raise ValueError((day_gan, other_gan))

def wuxing_score(pillars):
    """pillars: [(gan,zhi)]*4 → 五行加权得分（含藏干）"""
    c = [0.0]*5
    for g, z in pillars:
        c[GAN_WX[GAN10.index(g)]] += 1.0
        for i, h in enumerate(CANGGAN[z]):
            c[GAN_WX[GAN10.index(h)]] += CANG_W[i]
    return c

def dayun_dir(year_gan, male):
    """大运顺逆：阳年男 / 阴年女 → 顺；阴年男 / 阳年女 → 逆"""
    return (GAN_YY[GAN10.index(year_gan)] == 1) == bool(male)


# ══════════ 真太阳时 ══════════
def eot_minutes(day_of_year):
    """均时差（分钟）：真太阳时 − 平太阳时。全年约 −14.6 ~ +16.5"""
    B = 2*_math.pi*(day_of_year-81)/364.0
    return 9.87*_math.sin(2*B) - 7.53*_math.cos(B) - 1.5*_math.sin(B)

def true_solar_offset(day_of_year, lon, std_meridian=120.0):
    """返回 (经度时差, 均时差) 分钟。东经为正。"""
    return (lon-std_meridian)*4.0, eot_minutes(day_of_year)


# ══════════ 十二长生 ══════════
STAGES12 = ["长生","沐浴","冠带","临官","帝旺","衰","病","死","墓","绝","胎","养"]
CS_START = {"甲":"亥","丙":"寅","戊":"寅","庚":"巳","壬":"申",
            "乙":"午","丁":"酉","己":"酉","辛":"子","癸":"卯"}
YANG_GAN = set("甲丙戊庚壬")

def changsheng(gan, zhi):
    """十二长生：阳干顺行、阴干逆行"""
    st = ZHI12.index(CS_START[gan]); z = ZHI12.index(zhi)
    step = (z - st) if gan in YANG_GAN else (st - z)
    return STAGES12[step % 12]

def year_ganzhi(year):
    """流年干支（以立春为界的年）"""
    i = (year - 4) % 60
    return GAN10[i % 10], ZHI12[i % 12]


# ══════════ 纳音 · 神煞 ══════════
NAYIN60 = ["海中金","炉中火","大林木","路旁土","剑锋金","山头火","涧下水","城头土","白蜡金","杨柳木",
"泉中水","屋上土","霹雳火","松柏木","长流水","沙中金","山下火","平地木","壁上土","金箔金",
"覆灯火","天河水","大驿土","钗钏金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]

def gz_index(gan, zhi):
    gi, zi = GAN10.index(gan), ZHI12.index(zhi)
    for i in range(60):
        if i % 10 == gi and i % 12 == zi: return i
    raise ValueError((gan, zhi))

def nayin(gan, zhi):
    return NAYIN60[gz_index(gan, zhi) // 2]

SANHE = {("申","子","辰"):"壬", ("亥","卯","未"):"甲",
         ("寅","午","戌"):"丙", ("巳","酉","丑"):"庚"}
def _he_gan(zhi):
    for k, g in SANHE.items():
        if zhi in k: return g
    raise ValueError(zhi)
def _stage_zhi(gan, stage):
    return next(z for z in ZHI12 if changsheng(gan, z) == stage)
def _chong(z):
    return ZHI12[(ZHI12.index(z)+6) % 12]

def shensha(ref_zhi):
    """由三合局阳干的十二长生推出四神煞所在支（非查表）"""
    g = _he_gan(ref_zhi)
    return {"桃花": _stage_zhi(g,"沐浴"), "将星": _stage_zhi(g,"帝旺"),
            "华盖": _stage_zhi(g,"墓"),   "驿马": _chong(_stage_zhi(g,"长生"))}

def kongwang(day_cycle_index):
    """旬空：由日柱在六十甲子中的旬推出"""
    head = day_cycle_index - (day_cycle_index % 10)
    hz = head % 12
    return ZHI12[(hz+10) % 12], ZHI12[(hz+11) % 12]


# ══════════ 合盘：干支关系（全部由索引算术判定）══════════
_gi = lambda g: GAN10.index(g)
_zi = lambda z: ZHI12.index(z)
WUHE_WX = [2,3,4,0,1]                       # 甲己合土 乙庚合金 丙辛合水 丁壬合木 戊癸合火

def gan_he(a, b):     return (_gi(b)-_gi(a)) % 10 == 5
def gan_he_wx(a, b):  return WUXING[WUHE_WX[min(_gi(a), _gi(b)) % 5]]
def zhi_chong(a, b):  return (_zi(b)-_zi(a)) % 12 == 6
def zhi_he(a, b):     return (_zi(a)+_zi(b)) % 12 == 1
def zhi_hai(a, b):    return (_zi(a)+_zi(b)) % 12 == 7
def zhi_sanhe(a, b):  return a != b and _zi(a) % 4 == _zi(b) % 4

XING3 = [("寅","巳","申"), ("丑","戌","未"), ("子","卯")]
ZIXING = ["辰","午","酉","亥"]
def zhi_xing(a, b):
    if a == b: return a in ZIXING
    return any(a in t and b in t for t in XING3)
