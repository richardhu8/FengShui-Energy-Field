#!/usr/bin/env python3
"""六爻引擎一致性测试 —— 推导结果 vs 传世表。

传世表只在这里出现，引擎里一概不用；引擎全靠规则推。
两边对不上就是推导错了（或表抄错了，两种都要查）。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from liuyao_engine import *

TOTAL = 0; FAILS = []
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: 得 {got!r} 期 {want!r}")

# ══ 一、京房八宫六十四卦序（传世表）══════════════════════════
BAGONG = {
"乾":"乾为天 天风姤 天山遁 天地否 风地观 山地剥 火地晋 火天大有",
"兑":"兑为泽 泽水困 泽地萃 泽山咸 水山蹇 地山谦 雷山小过 雷泽归妹",
"离":"离为火 火山旅 火风鼎 火水未济 山水蒙 风水涣 天水讼 天火同人",
"震":"震为雷 雷地豫 雷水解 雷风恒 地风升 水风井 泽风大过 泽雷随",
"巽":"巽为风 风天小畜 风火家人 风雷益 天雷无妄 火雷噬嗑 山雷颐 山风蛊",
"坎":"坎为水 水泽节 水雷屯 水火既济 泽火革 雷火丰 地火明夷 地水师",
"艮":"艮为山 山火贲 山天大畜 山泽损 火泽睽 天泽履 风泽中孚 风山渐",
"坤":"坤为地 地雷复 地泽临 地天泰 雷天大壮 泽天夬 水天需 水地比",
}
for palace, row in BAGONG.items():
    want = row.split()
    got  = [lines_to_name(l) for _, l in palace_series(palace)]
    for i in range(8):
        check(f"八宫.{palace}.{PALACE_STEPS[i]}", got[i], want[i])
# 覆盖性：八宫推导须恰好覆盖 64 卦，不重不漏
allg = [lines_to_name(l) for p in BAGONG for _, l in palace_series(p)]
check("八宫.总数", len(allg), 64)
check("八宫.无重复", len(set(allg)), 64)
check("八宫.等于全部卦名", set(allg), set(GUA_NAME.values()))

# ══ 二、纳甲（传世表：各卦内外六爻干支，自下而上）══════════════
NAJIA_TABLE = {
"乾":"甲子 甲寅 甲辰 壬午 壬申 壬戌", "坤":"乙未 乙巳 乙卯 癸丑 癸亥 癸酉",
"震":"庚子 庚寅 庚辰 庚午 庚申 庚戌", "巽":"辛丑 辛亥 辛酉 辛未 辛巳 辛卯",
"坎":"戊寅 戊辰 戊午 戊申 戊戌 戊子", "离":"己卯 己丑 己亥 己酉 己未 己巳",
"艮":"丙辰 丙午 丙申 丙戌 丙子 丙寅", "兑":"丁巳 丁卯 丁丑 丁亥 丁酉 丁未",
}
for gua, row in NAJIA_TABLE.items():
    got = ["".join(x) for x in najia(list(BITS[gua])*2)]
    for i, w in enumerate(row.split()):
        check(f"纳甲.{gua}为卦.{i+1}爻", got[i], w)
# 纳甲须覆盖全部 64 卦且每卦六爻干支合法
for nm in GUA_NAME.values():
    gz = najia(name_to_lines(nm))
    check(f"纳甲.{nm}.爻数", len(gz), 6)
    check(f"纳甲.{nm}.干支合法", all(g in "甲乙丙丁戊己庚辛壬癸" and z in ZHI for g,z in gz), True)

# ══ 三、世应（传世表：世爻位置由世次定，应恒隔三）══════════════
for step, want in [("本宫",6),("一世",1),("二世",2),("三世",3),
                   ("四世",4),("五世",5),("游魂",4),("归魂",3)]:
    check(f"世爻.{step}", SHI_POS[step], want)
for s in range(1,7):
    check(f"应爻.世{s}", ying_pos(s), s+3 if s<=3 else s-3)
    check(f"应爻.相隔三位.世{s}", abs(ying_pos(s)-s), 3)
# 世应不得重合，且都在 1~6
for nm in GUA_NAME.values():
    d = dress(name_to_lines(nm))
    check(f"世应.{nm}.不重合", d["世"] != d["应"], True)
    check(f"世应.{nm}.在卦内", 1 <= d["世"] <= 6 and 1 <= d["应"] <= 6, True)

# ══ 四、六亲（生克推导 vs 逐条定义）══════════════════════════
for me in "金木水火土":
    check(f"六亲.{me}.兄弟", liuqin(me, me), "兄弟")
    check(f"六亲.{me}.父母", liuqin(me, [k for k,v in SHENG.items() if v==me][0]), "父母")
    check(f"六亲.{me}.子孙", liuqin(me, SHENG[me]), "子孙")
    check(f"六亲.{me}.官鬼", liuqin(me, [k for k,v in KE.items() if v==me][0]), "官鬼")
    check(f"六亲.{me}.妻财", liuqin(me, KE[me]), "妻财")
# 五行两两组合共 25 种，须全部落到五种六亲之一，且各占 5 种
from collections import Counter
cnt = Counter(liuqin(a,b) for a in "金木水火土" for b in "金木水火土")
check("六亲.覆盖25组合", sum(cnt.values()), 25)
check("六亲.五类各5", set(cnt.values()), {5})

# ══ 五、六神（日干起首）══════════════════════════════════════
for gan, first in [("甲","青龙"),("乙","青龙"),("丙","朱雀"),("丁","朱雀"),("戊","勾陈"),
                   ("己","螣蛇"),("庚","白虎"),("辛","白虎"),("壬","玄武"),("癸","玄武")]:
    ls = liushen(gan)
    check(f"六神.{gan}日.初爻", ls[0], first)
    check(f"六神.{gan}日.六神齐", set(ls), set(LIUSHEN))
    check(f"六神.{gan}日.循环序", ls, [LIUSHEN[(LIUSHEN.index(first)+i)%6] for i in range(6)])

# ══ 六、装卦实例（对照通行排盘：泽水困 · 甲子日）══════════════
d = dress(name_to_lines("泽水困"), "甲")
check("装卦.泽水困.宫", d["宫"], "兑")
check("装卦.泽水困.世次", d["世次"], "一世")
check("装卦.泽水困.世爻", d["世"], 1)
check("装卦.泽水困.应爻", d["应"], 4)
check("装卦.泽水困.干支",
      [y["干支"] for y in d["爻"]], ["戊寅","戊辰","戊午","丁亥","丁酉","丁未"])
check("装卦.泽水困.六亲",
      [y["六亲"] for y in d["爻"]], ["妻财","父母","官鬼","子孙","兄弟","父母"])
#   兑宫属金：寅木被克=妻财、辰土生金=父母、午火克金=官鬼、
#   亥水金所生=子孙、酉金同类=兄弟、未土=父母。与通行排盘逐爻一致。
check("装卦.泽水困.六神",
      [y["六神"] for y in d["爻"]], ["青龙","朱雀","勾陈","螣蛇","白虎","玄武"])

# ══ 六之二、伏神（本卦缺的六亲，取本宫首卦同爻位）════════════
# 天风姤：乾宫一世，六爻为 父母丑/子孙亥/兄弟酉/官鬼午/兄弟申/父母戌，缺妻财。
# 乾为天二爻甲寅木为妻财 → 妻财甲寅伏于二爻。通行排盘同。
d = dress(name_to_lines("天风姤"))
fu = {y["位"]: y.get("伏神") for y in d["爻"] if y.get("伏神")}
check("伏神.天风姤.只缺妻财", list(fu.values()), ["妻财甲寅"])
check("伏神.天风姤.伏于二爻", list(fu.keys()), [2])

# 山地剥：乾宫五世，缺兄弟；乾为天五爻壬申金为兄弟 → 伏于五爻。
d = dress(name_to_lines("山地剥"))
fu = {y["位"]: y.get("伏神") for y in d["爻"] if y.get("伏神")}
check("伏神.山地剥.只缺兄弟", list(fu.values()), ["兄弟壬申"])
check("伏神.山地剥.伏于五爻", list(fu.keys()), [5])
check("伏神.山地剥.世爻", d["世"], 5)
check("伏神.山地剥.应爻", d["应"], 2)

# 本宫首卦六亲必然俱全 —— 八宫首卦都不该有伏神
for p in BAGONG:
    d = dress(list(BITS[p])*2)
    check(f"伏神.{p}为卦.无伏神", any(y.get("伏神") for y in d["爻"]), False)
    check(f"伏神.{p}为卦.六亲俱全", len({y["六亲"] for y in d["爻"]}), 5)
# 全 64 卦：伏神所补的六亲恰为本卦所缺，且不重复
for nm in GUA_NAME.values():
    d = dress(name_to_lines(nm))
    have = {y["六亲"] for y in d["爻"]}
    fus  = [y["伏神"][:2] for y in d["爻"] if y.get("伏神")]
    check(f"伏神.{nm}.补齐五亲", have | set(fus), {"父母","子孙","官鬼","妻财","兄弟"})
    check(f"伏神.{nm}.不补已有", [f for f in fus if f in have], [])
    check(f"伏神.{nm}.不重复", len(fus), len(set(fus)))

# ══ 七、变卦 ════════════════════════════════════════════════
check("变卦.乾变初爻", lines_to_name(bian(name_to_lines("乾为天"), {1})), "天风姤")
check("变卦.乾全变",   lines_to_name(bian(name_to_lines("乾为天"), {1,2,3,4,5,6})), "坤为地")
check("变卦.幂等", bian(bian(name_to_lines("水火既济"), {2,5}), {2,5}), name_to_lines("水火既济"))
# 任一卦全变皆得其错卦（六爻俱反），两次全变复原
for nm in GUA_NAME.values():
    ls = name_to_lines(nm)
    check(f"变卦.{nm}.全变复原", bian(bian(ls, set(range(1,7))), set(range(1,7))), ls)

# ══ 八、全 64 卦装卦不得抛异常，六亲六神齐备 ══════════════════
for nm in GUA_NAME.values():
    d = dress(name_to_lines(nm), "甲")
    check(f"装卦.{nm}.六爻", len(d["爻"]), 6)
    check(f"装卦.{nm}.六亲合法",
          all(y["六亲"] in {"父母","子孙","官鬼","妻财","兄弟"} for y in d["爻"]), True)
    check(f"装卦.{nm}.世应各一",
          sum(y["世应"]=="世" for y in d["爻"]) == 1 and
          sum(y["世应"]=="应" for y in d["爻"]) == 1, True)

# ══ 九、日辰：日柱与旬空 ════════════════════════════════════
# 日柱对通行万年历取证；旬空由旬首推出，再与传世「六甲空亡」表反向核对。
for y,m,d,want in [(1949,10,1,"甲子"),(2000,1,1,"戊午"),(2024,2,4,"戊戌"),(2026,8,20,"丙寅")]:
    check(f"日柱.{y}-{m:02d}-{d:02d}", day_ganzhi(y,m,d), want)
# 相邻两日干支必相继
for y,m,d in [(2026,8,20),(1999,12,31),(2024,2,28)]:
    c0=day_cycle(y,m,d)
    c1=day_cycle(y,m,d+1) if d<28 else (c0+1)%60
    check(f"日柱.相继.{y}-{m:02d}-{d:02d}", c1, (c0+1)%60)
# 六甲空亡传世表：甲子旬→戌亥、甲戌旬→申酉、甲申旬→午未、
#                甲午旬→辰巳、甲辰旬→寅卯、甲寅旬→子丑
KONG = {"甲子":("戌","亥"),"甲戌":("申","酉"),"甲申":("午","未"),
        "甲午":("辰","巳"),"甲辰":("寅","卯"),"甲寅":("子","丑")}
for i in range(60):
    head = GAN10[(i-i%10)%10] + ZHI12[(i-i%10)%12]
    check(f"旬空.{GAN10[i%10]}{ZHI12[i%12]}", xunkong(i), KONG[head])
# 每旬十日空亡相同，且空亡之支必不在本旬出现
for h in range(0,60,10):
    inxun = {ZHI12[(h+k)%12] for k in range(10)}
    k1,k2 = xunkong(h)
    check(f"旬空.{GAN10[h%10]}{ZHI12[h%12]}旬.十日同空",
          {xunkong(h+k) for k in range(10)}, {(k1,k2)})
    check(f"旬空.{GAN10[h%10]}{ZHI12[h%12]}旬.空支不在旬内",
          k1 not in inxun and k2 not in inxun, True)

print(f"[六爻] {TOTAL-len(FAILS)}/{TOTAL} passed")
for f in FAILS[:25]: print("  FAIL", f)
if len(FAILS) > 25: print(f"  …… 另有 {len(FAILS)-25} 条")
sys.exit(1 if FAILS else 0)
