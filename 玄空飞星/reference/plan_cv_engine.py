#!/usr/bin/env python3
"""户型识别流水线参考实现 —— 与网页（玄空飞星排盘.html）逐函数同式。

流程：灰度 → Otsu 阈值 → 形态学闭运算（封门洞）→ 外部泛洪 + 填洞
      → 最大连通域 → Moore 边界追踪 → Douglas–Peucker 简化 → 九宫叠加

此前整条流水线零测试覆盖。图像那头难以单测，但每一步都有可验证的不变量：
Otsu 必为类间方差的 argmax；膨胀必外延、腐蚀必内缩、闭运算幂等；
追踪出的轮廓必闭合且逐点八邻接；DP 简化必保端点、单调、偏差有界。
"""
from __future__ import annotations


# ── Otsu 阈值 ────────────────────────────────────────────────
def otsu(gray, n=None):
    """最大类间方差阈值。gray 为 0~255 的可迭代。"""
    g = list(gray)
    n = n if n is not None else len(g)
    h = [0] * 256
    for v in g[:n]:
        h[v] += 1
    total = sum(t * h[t] for t in range(256))
    sum_b = w_b = 0
    best = 0.0; th = 128
    for t in range(256):
        w_b += h[t]
        if not w_b:
            continue
        w_f = n - w_b
        if not w_f:
            break
        sum_b += t * h[t]
        m_b = sum_b / w_b
        m_f = (total - sum_b) / w_f
        v = w_b * w_f * (m_b - m_f) ** 2
        if v > best:
            best = v; th = t
    return th


def between_class_variance(gray, t):
    """给定阈值的类间方差 —— 用来独立验证 otsu 确实取到 argmax。"""
    g = list(gray); n = len(g)
    lo = [v for v in g if v <= t]
    hi = [v for v in g if v > t]
    if not lo or not hi:
        return 0.0
    wb, wf = len(lo), len(hi)
    return wb * wf * (sum(lo) / wb - sum(hi) / wf) ** 2


# ── 形态学：可分离的方形结构元 ─────────────────────────────────
def dil_sep(m, W, H, r):
    """膨胀（先横后纵，等价于 (2r+1)×(2r+1) 方形结构元）。"""
    t = bytearray(W * H); o = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            lo, hi = max(0, x - r), min(W - 1, x + r)
            t[y * W + x] = 1 if any(m[y * W + k] for k in range(lo, hi + 1)) else 0
    for x in range(W):
        for y in range(H):
            lo, hi = max(0, y - r), min(H - 1, y + r)
            o[y * W + x] = 1 if any(t[k * W + x] for k in range(lo, hi + 1)) else 0
    return o


def ero_sep(m, W, H, r):
    """腐蚀 —— 由膨胀的对偶实现（与网页同式）。"""
    inv = bytearray(1 if not v else 0 for v in m)
    d = dil_sep(inv, W, H, r)
    return bytearray(0 if v else 1 for v in d)


def dil_brute(m, W, H, r):
    """暴力方形膨胀，用于验证可分离实现。"""
    o = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            hit = 0
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and m[ny * W + nx]:
                        hit = 1; break
                if hit: break
            o[y * W + x] = hit
    return o


def closing(m, W, H, r):
    return ero_sep(dil_sep(m, W, H, r), W, H, r)


def opening(m, W, H, r):
    return dil_sep(ero_sep(m, W, H, r), W, H, r)


# ── 连通域与泛洪 ────────────────────────────────────────────
def flood_ext(m, W, H):
    """自四边泛洪标记外部背景（四邻域）。内部孔洞不会被标到。"""
    ext = bytearray(W * H); st = []
    def push(x, y):
        i = y * W + x
        if not m[i] and not ext[i]:
            ext[i] = 1; st.append(i)
    for x in range(W):
        push(x, 0); push(x, H - 1)
    for y in range(H):
        push(0, y); push(W - 1, y)
    while st:
        i = st.pop(); x, y = i % W, i // W
        if x > 0: push(x - 1, y)
        if x < W - 1: push(x + 1, y)
        if y > 0: push(x, y - 1)
        if y < H - 1: push(x, y + 1)
    return ext


def largest_cc(m, W, H):
    """最大四连通域。"""
    seen = bytearray(W * H); best = []
    for s0 in range(W * H):
        if not m[s0] or seen[s0]:
            continue
        st = [s0]; cells = []; seen[s0] = 1
        while st:
            i = st.pop(); cells.append(i)
            x, y = i % W, i // W
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < W and 0 <= ny < H:
                    j = ny * W + nx
                    if m[j] and not seen[j]:
                        seen[j] = 1; st.append(j)
        if len(cells) > len(best):
            best = cells
    o = bytearray(W * H)
    for i in best:
        o[i] = 1
    return o


# ── Moore 边界追踪 ─────────────────────────────────────────
NEI8 = [(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]

def trace_contour(m, W, H):
    """Moore 邻域追踪。与网页同式：回到起点即停。"""
    s0 = next((i for i in range(W * H) if m[i]), -1)
    if s0 < 0:
        return []
    sx, sy = s0 % W, s0 // W
    cur = (sx, sy); b = 4
    out = [(sx, sy)]
    for _ in range(W * H * 4):
        found = False
        for k in range(8):
            d = (b + 1 + k) % 8
            nx, ny = cur[0] + NEI8[d][0], cur[1] + NEI8[d][1]
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if m[ny * W + nx]:
                b = (d + 5) % 8
                cur = (nx, ny); out.append(cur); found = True; break
        if not found:
            break
        if cur == (sx, sy) and len(out) > 2:
            break
    return out


# ── Douglas–Peucker ────────────────────────────────────────
def _seg_d2(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if dx == 0 and dy == 0:
        return (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return (p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2


def dp_simplify(pts, eps):
    pts = list(pts)
    if len(pts) < 3:
        return pts
    mx = 0.0; idx = 0
    for i in range(1, len(pts) - 1):
        d = _seg_d2(pts[i], pts[0], pts[-1])
        if d > mx:
            mx = d; idx = i
    if mx > eps * eps:
        return dp_simplify(pts[:idx + 1], eps)[:-1] + dp_simplify(pts[idx:], eps)
    return [pts[0], pts[-1]]


# ── 足迹提取（流水线主体）─────────────────────────────────────
def footprint_at(gray, W, H, th, R):
    """墙体加粗封门洞 → 外部泛洪 → 取反得含墙足迹 → 腐蚀还原 → 最大连通域。

    第三步取反是关键：从外部不可达的一切都算室内，孔洞（天井、内院）
    因此被自动填掉 —— 所以后续边界追踪面对的必是无洞掩码。
    """
    n = W * H
    wall = bytearray(1 if gray[i] < th else 0 for i in range(n))
    ext = flood_ext(dil_sep(wall, W, H, R), W, H)
    foot = bytearray(0 if ext[i] else 1 for i in range(n))
    foot = largest_cc(ero_sep(foot, W, H, R), W, H)
    a = 0; x0 = y0 = 10**9; x1 = y1 = -1
    for i in range(n):
        if foot[i]:
            a += 1; x = i % W; y = i // W
            x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
    bb = 0 if x1 < x0 else (x1 - x0 + 1) * (y1 - y0 + 1)
    return {"foot": foot, "area": a,
            "solidity": (a / bb) if bb else 0.0, "frac": a / n}


def has_hole(m, W, H):
    """掩码内是否存在从边界不可达的背景（＝孔洞）。"""
    ext = flood_ext(m, W, H)
    return any((not m[i]) and (not ext[i]) for i in range(W * H))


def outer_boundary(m, W, H):
    """外轮廓像素集：前景中四邻有「外部背景」者。孔洞壁不算。"""
    ext = flood_ext(m, W, H)
    s = set()
    for y in range(H):
        for x in range(W):
            if not m[y * W + x]:
                continue
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if not (0 <= nx < W and 0 <= ny < H) or ext[ny * W + nx]:
                    s.add((x, y)); break
    return s
