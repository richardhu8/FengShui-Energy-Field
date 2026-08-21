#!/usr/bin/env python3
"""紫白飞星参考实现 —— 流年 / 流月 / 流日 / 流时 中宫。

与网页（玄空飞星排盘.html 的 ziba）同式。此前这一块零测试覆盖，
而「超神接气」取最近甲子符头是典型的差一错高发处。

三元起例（皆为传世口诀，此处只作断言对象，推导在测试里）：
  流年 —— 下元甲子（1984）起七赤，逐年逆行
  流月 —— 子午卯酉年正月起八白、辰戌丑未起五黄、寅申巳亥起二黑，逐月逆行
  流日 —— 冬至后阳遁一白起顺行，夏至后阴遁九紫起逆行，皆自最近甲子日（符头）起
  流时 —— 阳遁：子午卯酉日一白、辰戌丑未日四绿、寅申巳亥日七赤，顺行
           阴遁：子午卯酉日九紫、辰戌丑未日六白、寅申巳亥日三碧，逆行
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solar_hp import sun_longitude_hp, term_jd, utc_from_jd
from calendar_proto import four_pillars

TZ = 8.0
ZI_WU_MAO_YOU = {0, 6, 3, 9}      # 子午卯酉（地支序号）
CHEN_XU_CHOU_WEI = {4, 10, 1, 7}  # 辰戌丑未
# 其余为寅申巳亥

def jdn(y, m, d):
    a = (14 - m) // 12; yy = y + 4800 - a; mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045

def cyc(j):
    return (j - 11) % 60

def nearest_jiazi(y, m, d):
    """离该日最近的甲子日（儒略日数）。等距时取在前者。"""
    j = jdn(y, m, d); c = cyc(j)
    before = j - c
    after = j + (60 - c) % 60
    return before if (j - before) <= (after - j) else after

def term_local(year, lon):
    """节气的北京时间 (y, m, d, h)。"""
    return utc_from_jd(term_jd(year, lon, sun_longitude_hp) + TZ / 24)

def _wrap(n):
    """归到 1~9。"""
    return (n % 9 + 9) % 9 + 1

def nian_center(solar_year):
    """流年中宫。1984 下元甲子起七赤，逐年逆行。"""
    return _wrap(7 - 1 - (solar_year - 1984))

def yue_center(year_zhi_idx, month_idx):
    """流月中宫。month_idx: 寅月=0。"""
    if year_zhi_idx in ZI_WU_MAO_YOU:   base = 8
    elif year_zhi_idx in CHEN_XU_CHOU_WEI: base = 5
    else:                                base = 2
    return _wrap(base - 1 - month_idx)

def shi_base(day_zhi_idx, yin):
    """流时起宫。"""
    if day_zhi_idx in ZI_WU_MAO_YOU:       return 9 if yin else 1
    if day_zhi_idx in CHEN_XU_CHOU_WEI:    return 6 if yin else 4
    return 3 if yin else 7

def ziba(y, m, d, h):
    """返回 {年,月,日,时} 中宫与遁局。"""
    Y, M, D, H, yi, mi, di, hz = four_pillars(y, m, d, h)
    # 立春分年后的干支年，用于流年
    lichun = term_local(y, 315)
    solar_year = y if (m, d, h) >= (lichun[1], lichun[2], lichun[3]) else y - 1

    xz = term_local(y, 90)     # 夏至
    dz = term_local(y, 270)    # 冬至
    after_xz = (m, d, h) >= (xz[1], xz[2], xz[3])
    after_dz = (m, d, h) >= (dz[1], dz[2], dz[3])
    yin = after_xz and not after_dz                    # 夏至后至冬至前为阴遁
    ref = xz if yin else (dz if after_dz else term_local(y - 1, 270))

    n = jdn(y, m, d) - nearest_jiazi(ref[0], ref[1], ref[2])
    ri = _wrap(9 - 1 - n) if yin else _wrap(1 - 1 + n)
    b2 = shi_base(di % 12, yin)
    shi = _wrap(b2 - 1 - hz) if yin else _wrap(b2 - 1 + hz)
    return {"四柱": (Y, M, D, H), "solarYear": solar_year,
            "年": nian_center(solar_year), "月": yue_center(yi % 12, mi),
            "日": ri, "时": shi,
            "遁": "阴遁·夏至后" if yin else "阳遁·冬至后",
            "符头": nearest_jiazi(ref[0], ref[1], ref[2]), "距符头": n}
