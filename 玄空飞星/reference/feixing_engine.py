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
