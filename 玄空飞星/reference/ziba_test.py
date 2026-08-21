#!/usr/bin/env python3
"""紫白飞星一致性测试 —— 流年 / 流月 / 流日 / 流时中宫。

此前这一块零测试覆盖。策略与别处相同：口诀只作断言对象，
能由结构推的（顺逆、周期、连续性、遁局切换点、符头性质）一律推。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ziba_engine import (ziba, nian_center, yue_center, shi_base, nearest_jiazi,
                         jdn, cyc, term_local, ZI_WU_MAO_YOU, CHEN_XU_CHOU_WEI)

TOTAL = 0; FAILS = []
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: 得 {got!r} 期 {want!r}")

ZHI = "子丑寅卯辰巳午未申酉戌亥"

# ══ 一、流年：下元甲子(1984)起七赤，逐年逆行 ══════════════════
check("流年.1984下元甲子", nian_center(1984), 7)
check("流年.2026", nian_center(2026), 1)          # App 实测 2026 丙午 = 一白
for y in range(1900, 2101):
    check(f"流年.值域.{y}", 1 <= nian_center(y) <= 9, True)
# 逐年逆行：next = prev - 1（1 之后回到 9）
for y in range(1900, 2100):
    a, b = nian_center(y), nian_center(y + 1)
    check(f"流年.逆行.{y}", b, 9 if a == 1 else a - 1)
# 周期恰为 9
check("流年.周期9", nian_center(1984 + 9), nian_center(1984))
check("流年.九宫齐全", sorted({nian_center(y) for y in range(1984, 1993)}), list(range(1, 10)))
# 三元起例：上元甲子(1864)一白、中元甲子(1924)四绿、下元甲子(1984)七赤
check("流年.上元甲子1864", nian_center(1864), 1)
check("流年.中元甲子1924", nian_center(1924), 4)

# ══ 二、流月：三元起例，逐月逆行 ══════════════════════════════
for zi in range(12):
    base = 8 if zi in ZI_WU_MAO_YOU else (5 if zi in CHEN_XU_CHOU_WEI else 2)
    check(f"流月.{ZHI[zi]}年.正月起", yue_center(zi, 0), base)
    # 十二月逐月逆行
    for mo in range(11):
        a, b = yue_center(zi, mo), yue_center(zi, mo + 1)
        check(f"流月.逆行.{ZHI[zi]}.{mo}", b, 9 if a == 1 else a - 1)
    check(f"流月.值域.{ZHI[zi]}", all(1 <= yue_center(zi, m) <= 9 for m in range(12)), True)
# 三组起宫互不相同，且恰为 8/5/2
check("流月.三元起宫", sorted({yue_center(z, 0) for z in range(12)}), [2, 5, 8])

# ══ 三、流时：阳遁顺行、阴遁逆行，起宫按日支三组 ══════════════
for zi in range(12):
    for yin in (False, True):
        b = shi_base(zi, yin)
        check(f"流时.起宫值域.{ZHI[zi]}.{'阴' if yin else '阳'}", 1 <= b <= 9, True)
check("流时.阳遁起宫", sorted({shi_base(z, False) for z in range(12)}), [1, 4, 7])
check("流时.阴遁起宫", sorted({shi_base(z, True) for z in range(12)}), [3, 6, 9])
# 阳遁 子午卯酉=1、辰戌丑未=4、寅申巳亥=7；阴遁 9/6/3
check("流时.阳遁.子", shi_base(0, False), 1)
check("流时.阳遁.辰", shi_base(4, False), 4)
check("流时.阳遁.寅", shi_base(2, False), 7)
check("流时.阴遁.子", shi_base(0, True), 9)
check("流时.阴遁.辰", shi_base(4, True), 6)
check("流时.阴遁.寅", shi_base(2, True), 3)

# ══ 四、符头：最近的甲子日 ═══════════════════════════════════
for y in range(2000, 2041):
    for lon, nm in ((90, "夏至"), (270, "冬至")):
        t = term_local(y, lon)
        ft = nearest_jiazi(t[0], t[1], t[2])
        check(f"符头.{y}{nm}.确为甲子日", cyc(ft), 0)
        gap = abs(jdn(t[0], t[1], t[2]) - ft)
        check(f"符头.{y}{nm}.不超30天", gap <= 30, True)

# ══ 五、遁局切换恰在冬至/夏至 ═════════════════════════════════
for y in range(2020, 2031):
    xz = term_local(y, 90); dz = term_local(y, 270)
    for t, nm, want in ((xz, "夏至", "阴遁·夏至后"), (dz, "冬至", "阳遁·冬至后")):
        after = ziba(t[0], t[1], t[2], t[3] + 0.02)["遁"]
        check(f"遁局.{y}{nm}后", after, want)
    # 夏至前一刻仍为阳遁
    before = ziba(xz[0], xz[1], xz[2], max(xz[3] - 0.02, 0.0))["遁"]
    if xz[3] > 0.05:
        check(f"遁局.{y}夏至前", before, "阳遁·冬至后")

# ══ 六、流日：阳遁顺行、阴遁逆行，同一遁内逐日连续 ═════════════
import datetime as _dt
def walk(y, m, d, days):
    out = []
    t = _dt.date(y, m, d)
    for _ in range(days):
        z = ziba(t.year, t.month, t.day, 12.0)
        out.append((t, z["日"], z["遁"]))
        t += _dt.timedelta(days=1)
    return out
for start, lab in (((2026, 1, 5), "阳遁段"), ((2026, 7, 5), "阴遁段")):
    seq = walk(*start, 40)
    same = [s for s in seq if s[2] == seq[0][2]]
    fwd = seq[0][2].startswith("阳")
    bad = 0
    for i in range(len(same) - 1):
        a, b = same[i][1], same[i + 1][1]
        exp = (9 if a == 9 else a) % 9 + 1 if fwd else (9 if a == 1 else a - 1)
        if b != exp: bad += 1
    check(f"流日.{lab}.逐日{'顺' if fwd else '逆'}行", bad, 0)
    check(f"流日.{lab}.值域", all(1 <= s[1] <= 9 for s in seq), True)

# ══ 七、流时：一日十二时辰连续 ═══════════════════════════════
for (y, m, d), lab in (((2026, 1, 15), "阳遁日"), ((2026, 7, 15), "阴遁日")):
    hs = [ziba(y, m, d, hh)["时"] for hh in (0.5, 2.5, 4.5, 6.5, 8.5, 10.5,
                                             12.5, 14.5, 16.5, 18.5, 20.5, 22.5)]
    fwd = ziba(y, m, d, 12.0)["遁"].startswith("阳")
    bad = 0
    for i in range(11):
        a, b = hs[i], hs[i + 1]
        exp = a % 9 + 1 if fwd else (9 if a == 1 else a - 1)
        if b != exp: bad += 1
    check(f"流时.{lab}.十二时辰{'顺' if fwd else '逆'}行", bad, 0)
    check(f"流时.{lab}.值域", all(1 <= v <= 9 for v in hs), True)

# ══ 七之二、超神接气：符头可在至日之前或之后 ═════════════════
# 符头在节气之前叫「超神」，之后叫「接气」，取最近者 —— 这是流派选择。
# 另一派用「至日后第一个甲子」，两者可差到 54 天，流日会整体不同。
chao = jie = zheng = 0
for y in range(2000, 2041):
    for lon in (90, 270):
        t = term_local(y, lon)
        off = jdn(t[0], t[1], t[2]) - nearest_jiazi(t[0], t[1], t[2])
        TOTAL += 1
        if abs(off) > 30: FAILS.append(f"符头偏移过大 {y}/{lon}: {off}")
        if off > 0: chao += 1
        elif off < 0: jie += 1
        else: zheng += 1
check("超神接气.两种都出现", chao > 0 and jie > 0, True)
check("超神接气.总数", chao + jie + zheng, 82)

# 至日处流日必然跳变（换遁局即换锚点），不是缺陷 —— 钉住免得被「修」掉
import datetime as _d
for y in (2026, 2027):
    for lon in (90, 270):
        t = term_local(y, lon)
        day = _d.date(t[0], t[1], t[2])
        a = ziba(day.year, day.month, day.day, max(t[3] - 0.05, 0.0))
        b = ziba(day.year, day.month, day.day, min(t[3] + 0.05, 23.9))
        check(f"至日.{y}.{lon}.遁局确实切换", a["遁"] != b["遁"], True)
        check(f"至日.{y}.{lon}.锚点确实重置", a["符头"] != b["符头"], True)

# ══ 八、全域值域与确定性 ═════════════════════════════════════
n = 0
for y in range(2024, 2029):
    for mo in (1, 4, 7, 10):
        for d in (5, 20):
            z = ziba(y, mo, d, 12.0)
            n += 1
            if not all(1 <= z[k] <= 9 for k in ("年", "月", "日", "时")):
                FAILS.append(f"值域越界 {y}-{mo}-{d}")
            TOTAL += 1
z1 = ziba(2026, 8, 17, 12.0); z2 = ziba(2026, 8, 17, 12.0)
check("确定性", [z1[k] for k in ("年","月","日","时")], [z2[k] for k in ("年","月","日","时")])

print(f"[紫白] {TOTAL-len(FAILS)}/{TOTAL} passed")
for f in FAILS[:20]: print("  FAIL", f)
sys.exit(1 if FAILS else 0)
