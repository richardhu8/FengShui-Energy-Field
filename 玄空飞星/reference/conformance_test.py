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

print(f"[含替卦] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 八宅明镜：游年变爻法，与经典游年歌比对 ──
from feixing_engine import bazhai, JI4, XIONG4, is_east
CLASSIC={
 8:{"生气":2,"五鬼":1,"延年":7,"六煞":3,"祸害":9,"天医":6,"绝命":4,"伏位":8},   # 艮宅
 1:{"生气":4,"五鬼":8,"延年":9,"六煞":6,"祸害":7,"天医":3,"绝命":2,"伏位":1},   # 坎宅
 6:{"生气":7,"五鬼":3,"延年":2,"六煞":1,"祸害":4,"天医":8,"绝命":9,"伏位":6},   # 乾宅
}
for z,exp in CLASSIC.items():
    got=bazhai(z)
    check(f"BZ.{z}宅", {v:k for k,v in got.items()}, exp)

# 八宅结构自洽：每宅游年必为八方的一个排列（无重无漏）
for z in (1,2,3,4,6,7,8,9):
    r=bazhai(z)
    check(f"BZ.{z}宅.排列", sorted(r.keys()), sorted([1,2,3,4,6,7,8,9]))
    check(f"BZ.{z}宅.八名",  sorted(r.values()), sorted(JI4+XIONG4))
    check(f"BZ.{z}宅.伏位",  [k for k,v in r.items() if v=="伏位"], [z])
    # 伏位必与宅卦同东西四命属性
    check(f"BZ.{z}宅.东西", is_east(z), is_east([k for k,v in r.items() if v=="伏位"][0]))
check("BZ.中宫无宅卦", bazhai(5), None)

print(f"[含八宅] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 户型九宫覆盖（井字法几何）──
from feixing_engine import plan_coverage, poly_area, clip_rect, PLAN_CELL
SQ=[(0,0),(300,0),(300,300),(0,300)]
LSHAPE=[(0,0),(300,0),(300,300),(100,300),(100,200),(0,200)]   # 缺左下(西南)
TRI=[(0,0),(300,0),(0,300)]

cov=plan_coverage(SQ)
for g,v in cov.items(): check(f"PL.方正.{g}", round(v,6), 1.0)

cov=plan_coverage(LSHAPE)
check("PL.L形.西南缺角", round(cov[2],6), 0.0)          # 坤=2 西南
for g in (6,1,8,7,3,9,4,5):                              # 其余满覆盖
    check(f"PL.L形.{g}满", round(cov[g],6), 1.0)

# 面积守恒：九宫裁剪面积之和 == 原多边形面积
for name,poly in (("方正",SQ),("L形",LSHAPE),("三角",TRI)):
    xs=[p[0] for p in poly]; ys=[p[1] for p in poly]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys); w=(x1-x0)/3; h=(y1-y0)/3
    tot=sum(poly_area(clip_rect(poly,x0+c*w,y0+r*h,x0+(c+1)*w,y0+(r+1)*h))
            for r in range(3) for c in range(3))
    check(f"PL.{name}.面积守恒", round(tot,6), round(poly_area(poly),6))

# 覆盖率恒在 [0,1]
for name,poly in (("方正",SQ),("L形",LSHAPE),("三角",TRI)):
    for g,v in plan_coverage(poly).items():
        check(f"PL.{name}.{g}.域", -1e-9 <= v <= 1+1e-9, True)

# 九宫格宫位映射：上北下南、左西右东
check("PL.宫位映射", PLAN_CELL, [[6,1,8],[7,5,3],[2,9,4]])

print(f"[含户型] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 立极点（面积形心）与中心放射法 ──
from feixing_engine import centroid, radial_coverage, sector_clip, signed_area, RADIAL_DIR
check("RD.形心.方正", tuple(round(v,6) for v in centroid(SQ)), (150.0,150.0))
# 形心 ≠ 外接矩形中心（L 形）
cl=centroid(LSHAPE)
check("RD.形心≠框心", (round(cl[0],2),round(cl[1],2)) != (150.0,150.0), True)
# 形心须落在多边形外接框内
check("RD.形心.在框内", 0<=cl[0]<=300 and 0<=cl[1]<=300, True)

# 扇区面积守恒：8 个 45° 扇区之和 == 多边形总面积
for name,poly in (("方正",SQ),("L形",LSHAPE),("三角",TRI)):
    c=centroid(poly)
    tot=sum(abs(signed_area(sector_clip(poly,c,th))) for th in RADIAL_DIR.values())
    check(f"RD.{name}.扇区守恒", round(tot,6), round(poly_area(poly),6))

# 归一化正确性：方正 / 细长 均不应误判缺角；L 形只有西南缺
for g,v in radial_coverage(SQ).items():  check(f"RD.方正.{g}", round(v,6), 1.0)
TALL=[(100,0),(200,0),(200,300),(100,300)]
for g,v in radial_coverage(TALL).items(): check(f"RD.细长.{g}", round(v,6), 1.0)
rc=radial_coverage(LSHAPE)
check("RD.L形.西南缺", rc[2] < 0.6, True)
for g in (6,1,8,7,3,9,4):
    check(f"RD.L形.{g}不缺", rc[g] >= 0.6, True)
# 两法结论一致：都指向西南
check("RD.两法同指西南",
      min(plan_coverage(LSHAPE), key=lambda k: plan_coverage(LSHAPE)[k]),
      min(rc, key=lambda k: rc[k]))

print(f"[含放射] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 八字：十神 / 藏干 / 五行 / 大运顺逆 ──
from feixing_engine import (shishen, wuxing_score, dayun_dir,
                            GAN10, ZHI12, CANGGAN, GAN_WX)
# 结构自洽：任一日主对十天干恰好给出十神各一
for d in GAN10:
    got=[shishen(d,o) for o in GAN10]
    check(f"BZ.{d}.十神齐全", sorted(set(got)), sorted(got))
    check(f"BZ.{d}.十神数", len(got), 10)
# 已知案例（日主癸 · 阴水）
for o,exp in [("丙","正财"),("戊","正官"),("壬","劫财"),("癸","比肩"),("乙","食神"),
              ("甲","伤官"),("辛","偏印"),("庚","正印"),("丁","偏财"),("己","七杀")]:
    check(f"BZ.癸对{o}", shishen("癸",o), exp)
# 藏干合法性与本气一致性
ZHI_WX={"子":4,"丑":2,"寅":0,"卯":0,"辰":2,"巳":1,"午":1,"未":2,"申":3,"酉":3,"戌":2,"亥":4}
for z in ZHI12:
    check(f"BZ.藏干合法.{z}", all(h in GAN10 for h in CANGGAN[z]), True)
    check(f"BZ.本气五行.{z}", GAN_WX[GAN10.index(CANGGAN[z][0])], ZHI_WX[z])
# 五行得分：总量守恒（4天干 + 各支藏干权重和）
bz=[("丙","午"),("丙","申"),("癸","亥"),("戊","午")]
tot=sum(wuxing_score(bz))
exp=4.0+sum(sum([1.0,0.5,0.3][:len(CANGGAN[z])]) for _,z in bz)
check("BZ.五行总量", round(tot,6), round(exp,6))
# 大运顺逆四组合
check("BZ.阳年男顺", dayun_dir("庚",True),  True)
check("BZ.阳年女逆", dayun_dir("庚",False), False)
check("BZ.阴年男逆", dayun_dir("辛",True),  False)
check("BZ.阴年女顺", dayun_dir("辛",False), True)

print(f"[含八字] {TOTAL-len(FAILS)}/{TOTAL} checks so far")

# ── 真太阳时 ──
from feixing_engine import eot_minutes, true_solar_offset
import datetime as _dt
# 均时差全年极值应接近 +16.4 / −14.2（天文参考值）
vals=[eot_minutes(n) for n in range(1,366)]
check("TS.均时差最大", 15.5 <= max(vals) <= 17.0, True)
check("TS.均时差最小", -15.5 <= min(vals) <= -13.5, True)
# 次极值符号：5 月中为正、7 月底为负
check("TS.5月中为正", eot_minutes(134) > 0, True)
check("TS.7月底为负", eot_minutes(207) < 0, True)
# 经度时差：每度 4 分钟，东经>120 为正
for lon,exp in [(120.0,0.0),(121.0,4.0),(119.0,-4.0),(87.62,(87.62-120)*4)]:
    d,_=true_solar_offset(140,lon)
    check(f"TS.经度差{lon}", round(d,6), round(exp,6))
# 外部锚点：xunq.chat 2000-05-20 乌鲁木齐 报 经度差 -130 分 / 均时差 3.5 分
n=_dt.date(2000,5,20).timetuple().tm_yday
dl,de=true_solar_offset(n,87.62)
check("TS.锚点.经度差", abs(dl-(-130)) < 1.0, True)
check("TS.锚点.均时差", abs(de-3.5) < 1.0, True)

print(f"[含真太阳时] {TOTAL-len(FAILS)}/{TOTAL} passed")
for f in FAILS: print("  FAIL",f)
sys.exit(1 if FAILS else 0)
