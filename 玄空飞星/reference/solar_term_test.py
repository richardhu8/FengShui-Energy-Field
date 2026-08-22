#!/usr/bin/env python3
"""节气时刻一致性测试 —— 对公开历书取证。

补一个真实存在过的缺口：此前基准套件里一条节气检查都没有。
README 曾写「四柱 8 项全同」，那是手工比对的结果，没进测试 ——
于是节气解算换实现时无人拦得住。现在锁上。

节气时刻决定三件事，错一分钟都可能连锁：
  · 立春分年 → 年柱
  · 节气定月 → 月柱
  · 冬至/夏至 → 紫白阴阳遁
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solar_hp import (sun_longitude_hp, sun_longitude_lp, term_jd,
                      utc_from_jd, jd_from_utc, delta_t, TERMS)

TOTAL = 0; FAILS = []
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: 得 {got!r} 期 {want!r}")

def bj_minutes(year, name):
    """该年该节气的北京时间，返回 (月, 日, 距零点分钟数)。"""
    t = utc_from_jd(term_jd(year, TERMS[name], sun_longitude_hp) + 8/24)
    return t[1], t[2], t[3] * 60

# ── 公开历书节气时刻（北京时间）───────────────────────────────
# 容差 2 分钟：历书本身给到分，取整与 ΔT 模型各有零点几分的余量。
ALMANAC = [
    (2020, "立春", 2, 4, 17, 3), (2020, "冬至", 12, 21, 18, 2),
    (2021, "立春", 2, 3, 22, 59),
    # 2021 小雪原本也在此表，但我写下的参照值经核对是错的（差整 6 小时），
    # 而非引擎有误。不拿引擎输出反填参照 —— 那是自证，直接撤下这条。
    (2022, "立春", 2, 4, 4, 51), (2022, "夏至", 6, 21, 17, 14),
    (2023, "立春", 2, 4, 10, 43), (2023, "秋分", 9, 23, 14, 50),
    (2024, "小寒", 1, 6, 4, 49), (2024, "大寒", 1, 20, 22, 7),
    (2024, "立春", 2, 4, 16, 27), (2024, "春分", 3, 20, 11, 6),
    (2024, "夏至", 6, 21, 4, 51), (2024, "冬至", 12, 21, 17, 21),
    (2025, "立春", 2, 3, 22, 10), (2025, "清明", 4, 4, 20, 49),
    (2025, "夏至", 6, 21, 10, 42), (2025, "秋分", 9, 23, 2, 19),
    (2025, "冬至", 12, 21, 23, 3), (2026, "立春", 2, 4, 4, 2),
    (2000, "春分", 3, 20, 15, 35),
]
exact = 0
for y, nm, m, d, hh, mm in ALMANAC:
    gm, gd, gmin = bj_minutes(y, nm)
    check(f"节气.{y}.{nm}.日期", (gm, gd), (m, d))
    check(f"节气.{y}.{nm}.时刻±1分", abs(gmin - (hh*60+mm)) <= 1, True)
    if abs(gmin - (hh*60+mm)) < 0.5: exact += 1
# 「分秒不差的个数」才是 ΔT 是否生效的判据。
# 变异测试发现：±2 分的容差放得下整个 ΔT（≈69 秒＝1.15 分），
# 把 UT→TT 转换整个删掉仍能全过 —— 而加 ΔT 的全部理由就是它有影响。
# 含 ΔT 时 19/20 分秒不差；漏掉则 0/20。
check("节气.分秒不差数≥15（ΔT 生效的判据）", exact >= 15, True)

# ── 结构性质：不依赖历书，靠定义自洽 ──────────────────────────
for y in range(1950, 2051, 7):
    ts = sorted((term_jd(y, lon, sun_longitude_hp), nm) for nm, lon in TERMS.items())
    # 24 节气在一年内严格递增，相邻间隔 14~16 天
    gaps = [ts[i+1][0] - ts[i][0] for i in range(23)]
    check(f"节气.{y}.严格递增", all(g > 0 for g in gaps), True)
    check(f"节气.{y}.间隔14~16天", all(14.0 < g < 16.0 for g in gaps), True)
    # 每个节气解出的黄经必回到目标值
    for nm, lon in TERMS.items():
        got = sun_longitude_hp(term_jd(y, lon, sun_longitude_hp))
        check(f"节气.{y}.{nm}.黄经归位", abs(((got - lon + 180) % 360) - 180) < 1e-6, True)

# ── ΔT 模型：分段多项式在接缝处不得跳变 ───────────────────────
for yr in [1941, 1961, 1986, 2005, 2050]:
    jd = jd_from_utc(yr, 1, 1)
    a, b = delta_t(jd - 1), delta_t(jd + 1)
    check(f"ΔT.{yr}接缝连续", abs(a - b) < 2.0, True)   # 秒
# Espenak–Meeus 的 2005–2050 段是 2006 年前后做的「预测」，而地球自转实际
# 没按预测减慢：模型给 2024 年 73.9 秒，实测约 69.2 秒，高估约 4.7 秒。
# 4.7 秒 = 0.08 分钟，对节气时刻无影响（上表 20 个节气仍逐分对上），
# 故不另建观测表；但把这个已知偏差写在测试里，免得日后被当成新 bug。
check("ΔT.2024模型值(高估约5秒)", 72 < delta_t(jd_from_utc(2024,1,1)) < 76, True)
check("ΔT.2024高估量<0.1分钟", (delta_t(jd_from_utc(2024,1,1)) - 69.2)/60 < 0.1, True)
check("ΔT.1950约29秒", 27 < delta_t(jd_from_utc(1950,1,1)) < 32, True)
check("ΔT.单调递增", delta_t(jd_from_utc(2040,1,1)) > delta_t(jd_from_utc(2000,1,1)), True)

# ── 记录旧低精度式的偏差，防止有人"顺手改回去" ────────────────
worst = max(abs(term_jd(y, lon, sun_longitude_lp) - term_jd(y, lon, sun_longitude_hp))*24*60
            for y in range(1950, 2051) for lon in TERMS.values())
check("旧低精度式.最大偏差>10分", worst > 10, True)   # 若这条失败，说明有人动了 lp 或 hp

# ══ 四柱：另一处此前完全没有覆盖的地方 ══════════════════════
# calendar_proto.four_pillars 的月柱曾长期是错的（小寒兜底导致月支恒为丑），
# 因为没有一条测试碰过它。现在把四柱本身钉住。
from calendar_proto import four_pillars

SIZHU = [
    # (年,月,日,时)          年柱   月柱   日柱   时柱      来源
    ((2026, 8, 17, 12.0),   "丙午","丙申","癸亥","戊午"),  # 与 xunq.chat 万年历比对过
    ((2000, 5, 20, 14.5),   "庚辰","辛巳","戊寅","己未"),  # 与 xunq.chat 命书比对过
    ((2026, 2, 4, 3+58/60), "乙巳","己丑","己酉","丙寅"),  # 立春(04:02)前一刻
    ((2026, 2, 4, 4+10/60), "丙午","庚寅","己酉","丙寅"),  # 立春后一刻 → 年月双换
]
for args, Y, M, D, H in SIZHU:
    got = four_pillars(*args)[:4]
    check(f"四柱.{args}.年", got[0], Y)
    check(f"四柱.{args}.月", got[1], M)
    check(f"四柱.{args}.日", got[2], D)
    check(f"四柱.{args}.时", got[3], H)

# 月支必随黄经推进：一年之内十二个月支各出现且仅出现一次
seen = []
for mo in range(1, 13):
    gz = four_pillars(2026, mo, 20, 12.0)[1]
    seen.append(gz[1])
check("四柱.2026十二月支互异", len(set(seen)), 12)
# 日柱逐日递增
prev = None
for d in range(1, 29):
    idx = four_pillars(2026, 3, d, 12.0)[6]
    if prev is not None:
        check(f"四柱.日柱递增.3-{d}", idx, (prev + 1) % 60)
    prev = idx

print(f"[节气+四柱] {TOTAL-len(FAILS)}/{TOTAL} passed"
      f"   （旧低精度式最大偏差 {worst:.1f} 分，已弃用）")
for f in FAILS[:20]: print("  FAIL", f)
sys.exit(1 if FAILS else 0)
