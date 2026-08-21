#!/usr/bin/env python3
"""炁流场参考实现 —— 测地距离场与各宫炁强度。

页面（炁流场3D.html）报的「各宫炁强度」必须是确定性、可复算的量：
炁强度 = exp(−自炁口的测地距离 / λ)，不可达为 0。粒子只是观感，不参与统计。

原实现用先进先出队列做 BFS，但边权有 1（正交）与 √2（对角）两种 ——
FIFO 只在等权图上给出最短路。实测它系统性高估测地距离：
开放矩形中心起点平均高估 17.4%、最大 41.4%；带隔墙时最大 16.8%。
只会高估不会低估（先到的路径未必最短）。此处改用 Dijkstra，精确。
"""
from __future__ import annotations
import heapq, math

DIAG = math.sqrt(2)          # 原实现写死 1.414，这里用真值
PALACE_CELL = [[6, 1, 8], [7, 5, 3], [2, 9, 4]]   # 上北下南：坎1 在上


def inside(poly, x, y):
    """射线法判点在多边形内。与页面同式。"""
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def build_grid(poly, G):
    """户型多边形 → G×G 室内掩码。返回 (mask, bbox)。"""
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    bb = {"x0": min(xs), "x1": max(xs), "y0": min(ys), "y1": max(ys)}
    bb["cw"] = (bb["x1"] - bb["x0"]) / G
    bb["ch"] = (bb["y1"] - bb["y0"]) / G
    mask = bytearray(G * G)
    for i in range(G):
        for j in range(G):
            x = bb["x0"] + (i + .5) * bb["cw"]
            y = bb["y0"] + (j + .5) * bb["ch"]
            mask[i * G + j] = 1 if inside(poly, x, y) else 0
    return mask, bb


def geodesic(mask, G, src, diag=DIAG):
    """自 src 的测地距离场（八邻域，绕墙）。不可达为 -1。

    Dijkstra —— 混合边权必须按距离出队，不能按入队先后。
    """
    INF = math.inf
    dist = [INF] * (G * G)
    dist[src] = 0.0
    pq = [(0.0, src)]
    while pq:
        d, k = heapq.heappop(pq)
        if d > dist[k]:
            continue
        i, j = divmod(k, G)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if not di and not dj:
                    continue
                ni, nj = i + di, j + dj
                if not (0 <= ni < G and 0 <= nj < G) or not mask[ni * G + nj]:
                    continue
                nk = ni * G + nj
                w = diag if (di and dj) else 1.0
                if d + w < dist[nk] - 1e-12:
                    dist[nk] = d + w
                    heapq.heappush(pq, (dist[nk], nk))
    return [(-1.0 if x == INF else x) for x in dist]


def geodesic_fifo(mask, G, src, diag=1.414):
    """旧实现：先进先出 + 首达即定值。仅供回归比对，勿用于出数。"""
    dist = [-1.0] * (G * G)
    q = [src]; dist[src] = 0.0; head = 0
    while head < len(q):
        k = q[head]; head += 1
        i, j = divmod(k, G); d = dist[k]
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if not di and not dj:
                    continue
                ni, nj = i + di, j + dj
                if not (0 <= ni < G and 0 <= nj < G) or not mask[ni * G + nj]:
                    continue
                nk = ni * G + nj
                if dist[nk] >= 0:
                    continue
                dist[nk] = d + (diag if (di and dj) else 1.0)
                q.append(nk)
    return dist


def entry_cell(mask, G, bb, ent_deg):
    """自炁口方位角 → 射入后第一个室内格。与页面同式。"""
    th = math.radians(ent_deg)
    cx = (bb["x0"] + bb["x1"]) / 2
    cy = (bb["y0"] + bb["y1"]) / 2
    R = max(bb["x1"] - bb["x0"], bb["y1"] - bb["y0"]) * .62
    px = cx + math.sin(th) * R
    py = cy - math.cos(th) * R
    vx, vy = -math.sin(th), math.cos(th)
    for _ in range(200):
        i = int((px - bb["x0"]) / bb["cw"])
        j = int((py - bb["y0"]) / bb["ch"])
        if 0 <= i < G and 0 <= j < G and mask[i * G + j]:
            return i * G + j
        px += vx * 3; py += vy * 3
    return None


LAMBDA_RATIO = 2.2           # λ = 最远测地距离 / 2.2

def palace_stats(mask, dist, G):
    """各宫炁强度 = 宫内室内格 exp(−d/λ) 的均值；不可达格计 0。

    返回 {宫: 强度 0~1}、{宫: 室内格数}、{宫: 可达格数}。
    """
    assert G % 3 == 0, "G 必须能被 3 整除，否则末行末列会被静默丢弃"
    maxd = max([d for d in dist if d >= 0] or [1.0])
    lam = maxd / LAMBDA_RATIO
    w = G // 3
    cov, cnt, reach = {}, {}, {}
    for r in range(3):
        for c in range(3):
            g = PALACE_CELL[r][c]
            s = n = rc = 0
            for i in range(c * w, (c + 1) * w):
                for j in range(r * w, (r + 1) * w):
                    if not mask[i * G + j]:
                        continue
                    n += 1
                    d = dist[i * G + j]
                    if d >= 0:
                        rc += 1
                        s += math.exp(-d / lam)
            cov[g] = s / n if n else 0.0
            cnt[g] = n; reach[g] = rc
    return cov, cnt, reach
