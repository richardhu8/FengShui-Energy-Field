# -*- coding: utf-8 -*-
"""节气/四柱/紫白 原型 —— 用视频实测值校验后再移植到 JS"""
import math

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
SX  = "鼠牛虎兔龙蛇马羊猴鸡狗猪"

def jd_from_utc(y, m, d, h=0.0):
    if m <= 2: y, m = y-1, m+12
    a = y//100; b = 2 - a + a//4
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + b - 1524.5 + h/24.0

def utc_from_jd(jd):
    z = math.floor(jd + 0.5); f = jd + 0.5 - z
    a = z
    if z >= 2299161:
        al = int((z - 1867216.25)/36524.25); a = z + 1 + al - al//4
    b = a + 1524; c = int((b - 122.1)/365.25); d = int(365.25*c); e = int((b-d)/30.6001)
    day = b - d - int(30.6001*e) + f
    mo = e - 1 if e < 14 else e - 13
    yr = c - 4716 if mo > 2 else c - 4715
    di = int(day); hh = (day - di)*24
    return yr, mo, di, hh

def sun_longitude(jd):
    """太阳视黄经(度)。

    原为 Meeus 低精度式；实测 1950–2050 的 2424 个节气平均差 3.65 分、
    最大 13.1 分，约 0.017%% 的出生时刻会判错月柱。现改用 solar_hp 的
    截断 VSOP87D + ΔT，与公开历书 14 个节气 13 个分秒不差。"""
    from solar_hp import sun_longitude_hp
    return sun_longitude_hp(jd)

def _sun_longitude_legacy(jd):
    """旧的 Meeus 低精度式，保留供回归比对"""
    T = (jd - 2451545.0)/36525.0
    L0 = 280.46646 + 36000.76983*T + 0.0003032*T*T
    M  = 357.52911 + 35999.05029*T - 0.0001537*T*T
    Mr = math.radians(M)
    C = ((1.914602 - 0.004817*T - 0.000014*T*T)*math.sin(Mr)
         + (0.019993 - 0.000101*T)*math.sin(2*Mr) + 0.000289*math.sin(3*Mr))
    true_long = L0 + C
    omega = 125.04 - 1934.136*T
    return (true_long - 0.00569 - 0.00478*math.sin(math.radians(omega))) % 360

def solar_term_jd(year, index):
    """index: 0=春分(0°) 起，每 15°。返回 UTC JD"""
    target = (index*15.0) % 360
    # 粗估：春分约 3/20
    jd = jd_from_utc(year, 3, 20) + index*15.2
    for _ in range(60):
        diff = (sun_longitude(jd) - target + 180) % 360 - 180
        jd -= diff*365.2422/360.0
    return jd

# 节气名与黄经：立春=315°
TERMS = {"立春":315,"雨水":330,"惊蛰":345,"春分":0,"清明":15,"谷雨":30,
         "立夏":45,"小满":60,"芒种":75,"夏至":90,"小暑":105,"大暑":120,
         "立秋":135,"处暑":150,"白露":165,"秋分":180,"寒露":195,"霜降":210,
         "立冬":225,"小雪":240,"大雪":255,"冬至":270,"小寒":285,"大寒":300}

def term_local(year, name, tz=8):
    """返回该年该节气的本地时间 (y,m,d,h)"""
    lon = TERMS[name]; idx = round(((lon - 0) % 360)/15)
    # 立春等黄经>270 的节气落在该公历年年初
    jd = solar_term_jd(year - (1 if lon >= 270 else 0), idx)
    return utc_from_jd(jd + tz/24.0)

# 十二节（定月建），黄经 315,345,15,45,75,105,135,165,195,225,255,285 → 寅..丑
JIE = ["立春","惊蛰","清明","立夏","芒种","小暑","立秋","白露","寒露","立冬","大雪","小寒"]

def four_pillars(y, m, d, h, tz=8):
    """四柱。月柱由太阳黄经直接定，与网页同式。

    原先按「遍历十二节、取最后一个已过的」定月，是错的：小寒发生在公历年的
    一月，排在节序末位却时间最早，于是一月之后的任何日期都被它兜底成丑月 ——
    四柱月支恒为丑。此函数当时无测试覆盖，故一直没被发现。
    改由黄经定月后与网页逐例一致，见 solar_term_test.py。
    """
    # --- 年柱：以立春为界 ---
    ly = term_local(y, "立春")
    after_lichun = (m, d, h) >= (ly[1], ly[2], ly[3])
    yy = y if after_lichun else y - 1
    yi = (yy - 4) % 60
    year_gz = GAN[yi % 10] + ZHI[yi % 12]
    # --- 月柱：黄经每 30° 一月，立春(315°)为寅月之始 ---
    lon = sun_longitude(jd_from_utc(y, m, d, h) - tz/24.0)
    zhi_idx = int(((lon - 315) % 360) // 30)          # 寅=0
    month_zhi = (zhi_idx + 2) % 12                    # 寅=2
    # 月干：年干 → 正月(寅)月干  甲己丙作首,乙庚戊为头,丙辛寻庚上,丁壬壬位流,戊癸甲寅求
    start = [2,4,6,8,0][yi % 10 % 5]
    month_gan = (start + zhi_idx) % 10
    month_gz = GAN[month_gan] + ZHI[month_zhi]
    # --- 日柱：JDN ---
    jdn = int(jd_from_utc(y, m, d, 12.0) + 0.5)
    di = (jdn - 11) % 60                  # 校准常数
    day_gz = GAN[di % 10] + ZHI[di % 12]
    # --- 时柱 ---
    hz = int(((h + 1) % 24)//2)
    hour_gan = ((di % 10) % 5 * 2 + hz) % 10
    hour_gz = GAN[hour_gan] + ZHI[hz]
    return year_gz, month_gz, day_gz, hour_gz, yi, zhi_idx, di, hz

if __name__ == "__main__":
    print("立春 2026 :", term_local(2026, "立春"), "  (App 显示 2/4 04:02)")
    print("夏至 2026 :", term_local(2026, "夏至"))
    print("立秋 2026 :", term_local(2026, "立秋"))
    print()
    r = four_pillars(2026, 8, 17, 12.0)
    print("2026-08-17 12:00 四柱:", r[0], r[1], r[2], r[3])
    print("App 实测           :", "丙午", "丙申", "癸亥", "戊午")
