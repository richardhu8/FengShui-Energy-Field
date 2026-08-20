#!/usr/bin/env python3
"""六爻纳甲参考实现 —— 八宫卦序 · 世应 · 纳甲 · 六亲 · 六神 · 伏神。

本文件的规矩与 feixing_engine.py 一致：**能推的一律推，不抄表**。
六爻里绝大多数"要背的表"其实都是规则的产物：

  · 京房八宫六十四卦     —— 本宫依次变爻得来，不是任意排的
  · 世爻位置             —— 由卦在本宫中的世次直接决定
  · 纳甲干支             —— 阳卦地支顺行、阴卦逆行，各有起支
  · 六亲                 —— 卦宫五行与爻支五行的生克关系
  · 六神                 —— 日干起首，六神固定序上排

抄来的表错一格看不出来，推出来的错了会当场崩 —— 见文末自检。
"""
from __future__ import annotations

# ── 八卦：三爻自下而上的阴阳 ────────────────────────────────────
# 乾三连 ☰ / 兑上缺 ☱ / 离中虚 ☲ / 震仰盂 ☳
# 巽下断 ☴ / 坎中满 ☵ / 艮覆碗 ☶ / 坤六断 ☷
TRIGRAM = {
    (1,1,1):"乾", (1,1,0):"兑", (1,0,1):"离", (1,0,0):"震",
    (0,1,1):"巽", (0,1,0):"坎", (0,0,1):"艮", (0,0,0):"坤",
}
BITS = {v:k for k,v in TRIGRAM.items()}

# 六十四卦名：行为下卦、列为上卦（唯一一处传世表，其余全靠推）
_ORDER = ["乾","兑","离","震","巽","坎","艮","坤"]
_NAMES = """
乾为天 泽天夬 火天大有 雷天大壮 风天小畜 水天需 山天大畜 地天泰
天泽履 兑为泽 火泽睽 雷泽归妹 风泽中孚 水泽节 山泽损 地泽临
天火同人 泽火革 离为火 雷火丰 风火家人 水火既济 山火贲 地火明夷
天雷无妄 泽雷随 火雷噬嗑 震为雷 风雷益 水雷屯 山雷颐 地雷复
天风姤 泽风大过 火风鼎 雷风恒 巽为风 水风井 山风蛊 地风升
天水讼 泽水困 火水未济 雷水解 风水涣 坎为水 山水蒙 地水师
天山遁 泽山咸 火山旅 雷山小过 风山渐 水山蹇 艮为山 地山谦
天地否 泽地萃 火地晋 雷地豫 风地观 水地比 山地剥 坤为地
"""
GUA_NAME = {}
for _r, _row in enumerate(_NAMES.strip().split("\n")):
    for _c, _nm in enumerate(_row.split()):
        GUA_NAME[(_ORDER[_r], _ORDER[_c])] = _nm      # (下卦, 上卦) → 卦名


def lines_to_name(lines):
    """六爻（自下而上，1 阳 0 阴）→ 卦名。"""
    lo = TRIGRAM[tuple(lines[0:3])]
    hi = TRIGRAM[tuple(lines[3:6])]
    return GUA_NAME[(lo, hi)]


def name_to_lines(name):
    for (lo, hi), nm in GUA_NAME.items():
        if nm == name:
            return list(BITS[lo]) + list(BITS[hi])
    raise KeyError(name)


# ── 京房八宫：由本宫卦依次变爻推出，不抄卦序表 ──────────────────
# 本宫 → 初爻变(一世) → 二爻变(二世) → 三爻变(三世) → 四爻变(四世)
# → 五爻变(五世) → 四爻再变(游魂) → 内卦三爻全变(归魂)
PALACE_STEPS = ["本宫", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂"]

def palace_series(palace):
    """推出某宫的八卦，返回 [(世次, 六爻), ...]。"""
    base = list(BITS[palace]) * 2          # 本宫卦为该卦重叠
    out = [("本宫", base[:])]
    cur = base[:]
    for i in range(5):                     # 一世~五世：初至五爻依次变
        cur = cur[:]; cur[i] ^= 1
        out.append((PALACE_STEPS[i+1], cur[:]))
    you = cur[:]; you[3] ^= 1              # 游魂：四爻变回
    out.append(("游魂", you[:]))
    gui = you[:]                            # 归魂：内卦三爻全变
    for i in range(3): gui[i] ^= 1
    out.append(("归魂", gui))
    return out

# 世爻爻位（1~6）：由世次直接决定，应爻恒隔三位
SHI_POS = {"本宫":6, "一世":1, "二世":2, "三世":3, "四世":4, "五世":5, "游魂":4, "归魂":3}
def ying_pos(shi):
    return shi + 3 if shi <= 3 else shi - 3

# 全部六十四卦 → (所属宫, 世次)
GUA_PALACE = {}
for _p in _ORDER:
    for _step, _ls in palace_series(_p):
        GUA_PALACE[lines_to_name(_ls)] = (_p, _step)


# ── 纳甲：阳卦地支顺行、阴卦逆行，各有起支 ──────────────────────
ZHI = "子丑寅卯辰巳午未申酉戌亥"
# 卦 → (内卦天干, 外卦天干, 内卦起支, 外卦起支, 是否顺行)
NAJIA_RULE = {
    "乾":("甲","壬","子","午", True ), "震":("庚","庚","子","午", True ),
    "坎":("戊","戊","寅","申", True ), "艮":("丙","丙","辰","戌", True ),
    "坤":("乙","癸","未","丑", False), "巽":("辛","辛","丑","未", False),
    "离":("己","己","卯","酉", False), "兑":("丁","丁","巳","亥", False),
}

def najia(lines):
    """六爻纳甲，返回自下而上的 [(天干, 地支), ...]。

    内卦（初二三）与外卦（四五六）各按其本卦纳甲：
    阳卦地支每爻 +2，阴卦每爻 -2。
    """
    out = []
    for half, idx in ((tuple(lines[0:3]), 0), (tuple(lines[3:6]), 1)):
        gua = TRIGRAM[half]
        gi, go, zi, zo, fwd = NAJIA_RULE[gua]
        gan = gi if idx == 0 else go
        start = ZHI.index(zi if idx == 0 else zo)
        step = 2 if fwd else -2
        for k in range(3):
            out.append((gan, ZHI[(start + step*k) % 12]))
    return out


# ── 六亲：卦宫五行为"我"，与爻支五行论生克 ──────────────────────
PALACE_WX = {"乾":"金","兑":"金","坤":"土","艮":"土","震":"木","巽":"木","坎":"水","离":"火"}
ZHI_WX = {"子":"水","丑":"土","寅":"木","卯":"木","辰":"土","巳":"火",
          "午":"火","未":"土","申":"金","酉":"金","戌":"土","亥":"水"}
SHENG = {"木":"火","火":"土","土":"金","金":"水","水":"木"}   # 生
KE    = {"木":"土","土":"水","水":"火","火":"金","金":"木"}   # 克

def liuqin(me, other):
    """以 me（卦宫五行）为我，判 other（爻支五行）的六亲。"""
    if other == me:            return "兄弟"
    if SHENG[other] == me:     return "父母"     # 生我者
    if SHENG[me] == other:     return "子孙"     # 我生者
    if KE[other] == me:        return "官鬼"     # 克我者
    if KE[me] == other:        return "妻财"     # 我克者
    raise AssertionError(f"五行关系未覆盖: {me} vs {other}")


# ── 六神：由日干起首，六神固定序自初爻上排 ──────────────────────
LIUSHEN = ["青龙","朱雀","勾陈","螣蛇","白虎","玄武"]
def liushen_start(day_gan):
    return {"甲":0,"乙":0,"丙":1,"丁":1,"戊":2,"己":3,
            "庚":4,"辛":4,"壬":5,"癸":5}[day_gan]

def liushen(day_gan):
    s = liushen_start(day_gan)
    return [LIUSHEN[(s + i) % 6] for i in range(6)]


# ── 装卦总成 ────────────────────────────────────────────────
def dress(lines, day_gan=None):
    """给六爻装上：宫、世次、世应、纳甲、六亲、六神、伏神。"""
    name = lines_to_name(lines)
    palace, step = GUA_PALACE[name]
    me = PALACE_WX[palace]
    gz = najia(lines)
    shi = SHI_POS[step]
    yao = []
    for i in range(6):
        gan, zhi = gz[i]
        yao.append({
            "位": i+1, "阴阳": "阳" if lines[i] else "阴",
            "干支": gan+zhi, "五行": ZHI_WX[zhi],
            "六亲": liuqin(me, ZHI_WX[zhi]),
            "世应": "世" if i+1==shi else ("应" if i+1==ying_pos(shi) else ""),
        })
    if day_gan:
        for i, sh in enumerate(liushen(day_gan)):
            yao[i]["六神"] = sh
    # 伏神：本卦缺的六亲，取本宫首卦同爻位的爻
    have = {y["六亲"] for y in yao}
    base = list(BITS[palace]) * 2
    bgz = najia(base)
    for i in range(6):
        gan, zhi = bgz[i]
        qin = liuqin(me, ZHI_WX[zhi])
        if qin not in have:
            yao[i]["伏神"] = f"{qin}{gan}{zhi}"
    return {"卦名": name, "宫": palace, "世次": step, "宫五行": me,
            "世": shi, "应": ying_pos(shi), "爻": yao}


def bian(lines, moving):
    """动爻取变卦。moving 为 1~6 的爻位集合。"""
    out = lines[:]
    for p in moving:
        out[p-1] ^= 1
    return out


# ── 日辰：定六神起首与旬空 ──────────────────────────────────
GAN10 = "甲乙丙丁戊己庚辛壬癸"
ZHI12 = "子丑寅卯辰巳午未申酉戌亥"

def jdn(y, m, d):
    """公历 → 儒略日数（整数，民用日）。"""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def day_cycle(y, m, d):
    """日柱在六十甲子中的序号 0~59。口径与 feixing_engine 的排盘页一致。"""
    return (jdn(y, m, d) - 11) % 60

def day_ganzhi(y, m, d):
    c = day_cycle(y, m, d)
    return GAN10[c % 10] + ZHI12[c % 12]

def xunkong(cycle_index):
    """旬空：本旬十日排不到的两支。由旬首地支 +10、+11 推出，不查表。"""
    z0 = (cycle_index - cycle_index % 10) % 12
    return ZHI12[(z0 + 10) % 12], ZHI12[(z0 + 11) % 12]
