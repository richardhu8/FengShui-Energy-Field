# -*- coding: utf-8 -*-
"""
一致性测试 —— 把你自研引擎接到 ADAPTER 上即可跑基准。
用法:  python3 reference/conformance_test.py
"""
import json, sys
sys.path.insert(0, ".")
from reference.feixing_engine import pan, MOUNTAINS, BY_NAME, liunian_center

# ── 把这里换成你自己的引擎；签名: (yun:int, facing_deg:float) -> dict ──────────
# 需返回同构 dict: 坐向/山星入中/山星飞法/向星入中/向星飞法/运盘/山星盘/向星盘/格局
ADAPTER = pan
# ─────────────────────────────────────────────────────────────────────────────

FAILS, TOTAL = [], 0
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: got={got!r} want={want!r}")

# T1 外部实测锚点：抖音「灵台虚」App，九运 / 向 209.5°
p = ADAPTER(9, 209.5)
check("T1.坐向", p["坐向"], "丑山未向")
check("T1.山星", (p["山星入中"], p["山星飞法"]), (3, "顺飞"))
check("T1.向星", (p["向星入中"], p["向星飞法"]), (6, "逆飞"))
check("T1.运盘",   [p["运盘"][g]   for g in (4,9,2,3,5,7,8,1,6)], [8,4,6,7,9,2,3,5,1])
check("T1.山星盘", [p["山星盘"][g] for g in (4,9,2,3,5,7,8,1,6)], [2,7,9,1,3,5,6,8,4])
check("T1.向星盘", [p["向星盘"][g] for g in (4,9,2,3,5,7,8,1,6)], [7,2,9,8,6,4,3,1,5])

# T2 八运旺山旺向六局（公开流传名单）
got8 = sorted(ADAPTER(8, m[4])["坐向"] for m in MOUNTAINS
              if ADAPTER(8, m[4])["格局"] == "旺山旺向")
check("T2.八运旺山旺向", got8,
      sorted(["乾山巽向","巽山乾向","亥山巳向","巳山亥向","丑山未向","未山丑向"]))

# T3 九运格局分布：无旺山旺向 / 无上山下水
g9 = [ADAPTER(9, m[4])["格局"] for m in MOUNTAINS]
check("T3.九运旺山旺向数", g9.count("旺山旺向"), 0)
check("T3.九运上山下水数", g9.count("上山下水"), 0)
check("T3.九运双星到向数", g9.count("双星到向"), 12)
check("T3.九运双星到坐数", g9.count("双星到坐"), 12)

# T4 逆飞方向：常见 bug 是反转宫序而非取负步长
q = ADAPTER(9, 209.5)["向星盘"]          # 6 入中逆飞
check("T4.逆飞_乾", q[6], 5)             # 中6 → 乾5，不是 乾7
check("T4.逆飞_坤", q[2], 9)             # 逆行至坤应为 9

# T5 流年中宫（App 实测 2026 丙午 = 1 白）
for y, w in [(2024,3),(2025,2),(2026,1),(2027,9),(2028,8),(1984,7)]:
    check(f"T5.流年{y}", liunian_center(y), w)

# T6 度数边界：山界 ±7.5°，跨 0° 不能错位
check("T6.边界_202.6", ADAPTER(9, 202.6)["向首"], "未")
check("T6.边界_217.4", ADAPTER(9, 217.4)["向首"], "未")
check("T6.边界_217.6", ADAPTER(9, 217.6)["向首"], "坤")
check("T6.跨零_359",   ADAPTER(9, 359.0)["向首"], "子")
check("T6.跨零_001",   ADAPTER(9,   1.0)["向首"], "子")
check("T6.跨零_350",   ADAPTER(9, 350.0)["向首"], "壬")

# T7 全 216 组自洽性：每盘九宫数字必为 1-9 各一次
for yun in range(1,10):
    for m in MOUNTAINS:
        r = ADAPTER(yun, m[4])
        for key in ("运盘","山星盘","向星盘"):
            check(f"T7.{yun}运{r['坐向']}.{key}", sorted(r[key].values()), list(range(1,10)))

print(f"[下卦] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 替卦（起星）：与专业排盘程序【妙訣堂】逐格校验 ──
from feixing_engine import pan_ti
def gridS(p,key):  # 上南 layout
    return [p[key][g] for g in (4,9,2,3,5,7,8,1,6)]

# E1: 九运 辛山乙向兼戌辰 (向乙 105°)
e1=pan_ti(9, BY_NAME['乙'][4])
check("TI.E1.坐向",(e1['坐山'],e1['向首']),('辛','乙'))
check("TI.E1.入中",(e1['山星入中'],e1['山星飞法'],e1['向星入中'],e1['向星飞法']),(1,'顺飞',7,'逆飞'))
check("TI.E1.山盘",gridS(e1,'山星盘'),[9,5,7,8,1,3,4,6,2])
check("TI.E1.向盘",gridS(e1,'向星盘'),[8,3,1,9,7,5,4,2,6])

# E2: 九运 子山午向兼壬丙 (向午 180°) — 关键边界: 山R=5(廉贞无替→5), 向R=4(文曲→替6)
e2=pan_ti(9, BY_NAME['午'][4])
check("TI.E2.坐向",(e2['坐山'],e2['向首']),('子','午'))
check("TI.E2.入中",(e2['山星入中'],e2['山星飞法'],e2['向星入中'],e2['向星飞法']),(5,'逆飞',6,'顺飞'))
check("TI.E2.山盘",gridS(e2,'山星盘'),[6,1,8,7,5,3,2,9,4])
check("TI.E2.向盘",gridS(e2,'向星盘'),[5,1,3,4,6,8,9,2,7])

# 替卦全 216 组自洽性: 每盘九宫 1-9 各一次
for yun in range(1,10):
    for m in MOUNTAINS:
        r=pan_ti(yun,m[4])
        for k in ("山星盘","向星盘"):
            check(f"TI.{yun}运{r['坐向']}.{k}",sorted(r[k].values()),list(range(1,10)))

print(f"[含替卦] {TOTAL-len(FAILS)}/{TOTAL} passed")
for f in FAILS: print("  FAIL",f)
sys.exit(1 if FAILS else 0)
