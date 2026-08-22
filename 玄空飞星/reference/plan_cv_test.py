#!/usr/bin/env python3
"""户型识别流水线一致性测试。

这条流水线此前零测试覆盖。图像那头难以造标准答案，但每一步都有
可验证的不变量 —— 全部对着数学定义验，不对着实现验。
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_cv_engine import (otsu, between_class_variance, dil_sep, ero_sep,
                            dil_brute, closing, opening, flood_ext, largest_cc,
                            trace_contour, dp_simplify, _seg_d2, footprint_at,
                            has_hole, outer_boundary)

TOTAL = 0; FAILS = []
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: 得 {got!r} 期 {want!r}")

def mk(rows):
    H = len(rows); W = len(rows[0])
    m = bytearray(W * H)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch == '#': m[y * W + x] = 1
    return m, W, H

RNG = random.Random(20260821)
def rand_mask(W, H, p=0.45):
    return bytearray(1 if RNG.random() < p else 0 for _ in range(W * H))

SHAPES = {
 "矩形":      ["............",".##########.",".##########.",".##########.",".##########.","............"],
 "L形":       ["..........","..#####...","..#####...","..#####...","..#######.","..#######.",".........."],
 "凸形":      ["..........","...####...","...####...",".########.",".########.",".........."],
 "细颈":      ["..........","..####....","..####....","...##.....","..####....","..####....",".........."],
 "锯齿":      ["..........",".#.#.#.#..",".########.",".########.","..........",".........."],
}

# ══ 一、Otsu：必为类间方差的 argmax ═══════════════════════════
for name, g in {
    "双峰": [10]*300 + [200]*300,
    "单值": [77]*500,
    "均匀": list(range(256)) * 3,
    "偏斜": [5]*900 + [250]*100,
    "三峰": [20]*200 + [128]*200 + [230]*200,
}.items():
    t = otsu(g)
    brute = max(range(256), key=lambda x: between_class_variance(g, x))
    check(f"Otsu.{name}.等于暴力argmax",
          abs(between_class_variance(g, t) - between_class_variance(g, brute)) < 1e-6, True)
    check(f"Otsu.{name}.值域", 0 <= t <= 255, True)
# 双峰阈值必落在两峰之间
check("Otsu.双峰.分开两类", 10 <= otsu([10]*300 + [200]*300) < 200, True)
# 单值图像：类间方差恒为 0，任何阈值都行，但不得抛异常
check("Otsu.单值不崩", 0 <= otsu([77]*500) <= 255, True)
# t=255 恒不可选：此时 w_b==n、w_f==0，循环在算方差前就 break。
# （变异测试里「少扫一档 range(255)」抓不到，正因为它是等价变异。）
check("Otsu.阈值恒小于255", all(otsu(g) < 255 for g in
      ([0]*10+[255]*10, list(range(256)), [255]*50, [254]*20+[255]*20)), True)

# ══ 二、形态学 ═══════════════════════════════════════════════
for name, rows in SHAPES.items():
    m, W, H = mk(rows)
    for r in (1, 2, 3):
        d = dil_sep(m, W, H, r)
        e = ero_sep(m, W, H, r)
        # 可分离实现必须等于暴力方形结构元
        check(f"形态.{name}.r{r}.可分离等于暴力", bytes(d), bytes(dil_brute(m, W, H, r)))
        # 膨胀外延、腐蚀内缩
        check(f"形态.{name}.r{r}.膨胀外延", all(d[i] or not m[i] for i in range(W*H)), True)
        check(f"形态.{name}.r{r}.腐蚀内缩", all(m[i] or not e[i] for i in range(W*H)), True)
        # 开 ⊆ 原 ⊆ 闭
        op, cl = opening(m, W, H, r), closing(m, W, H, r)
        check(f"形态.{name}.r{r}.开⊆原", all(m[i] or not op[i] for i in range(W*H)), True)
        check(f"形态.{name}.r{r}.原⊆闭", all(cl[i] or not m[i] for i in range(W*H)), True)
        # 平坦结构元的开闭必幂等
        check(f"形态.{name}.r{r}.闭运算幂等", bytes(closing(cl, W, H, r)), bytes(cl))
        check(f"形态.{name}.r{r}.开运算幂等", bytes(opening(op, W, H, r)), bytes(op))
# 随机掩码同样满足（幂等性最易在不规则形状上暴露问题）
for k in range(6):
    m = rand_mask(14, 14); W = H = 14
    cl = closing(m, W, H, 2); op = opening(m, W, H, 2)
    check(f"形态.随机{k}.闭幂等", bytes(closing(cl, W, H, 2)), bytes(cl))
    check(f"形态.随机{k}.开幂等", bytes(opening(op, W, H, 2)), bytes(op))
    check(f"形态.随机{k}.可分离", bytes(dil_sep(m,W,H,2)), bytes(dil_brute(m,W,H,2)))

# ══ 三、泛洪与连通域 ═════════════════════════════════════════
# 带孔洞的环：孔洞不得被标为外部
ring, W, H = mk(["........",".######.",".#....#.",".#....#.",".######.","........"])
ext = flood_ext(ring, W, H)
check("泛洪.外部含四角", all(ext[y*W+x] for x, y in [(0,0),(W-1,0),(0,H-1),(W-1,H-1)]), True)
check("泛洪.孔洞不算外部", any((not ring[i]) and (not ext[i]) for i in range(W*H)), True)
check("泛洪.前景不被标", all(not (ring[i] and ext[i]) for i in range(W*H)), True)
check("孔洞检测.环有洞", has_hole(ring, W, H), True)
solid, W2, H2 = mk(["......",".####.",".####.","......"])
check("孔洞检测.实心无洞", has_hole(solid, W2, H2), False)
# 最大连通域：两块分离，取大的
two, W3, H3 = mk(["..........",".###...#..",".###...#..",".###......","..........",])
cc = largest_cc(two, W3, H3)
check("连通域.取大块", sum(cc), 9)
check("连通域.是原图子集", all(two[i] or not cc[i] for i in range(W3*H3)), True)
# 结果必恰为一个四连通域
def n_components(m, W, H):
    seen = bytearray(W*H); n = 0
    for s in range(W*H):
        if not m[s] or seen[s]: continue
        n += 1; st=[s]; seen[s]=1
        while st:
            i = st.pop(); x, y = i % W, i // W
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=nx<W and 0<=ny<H:
                    j = ny*W+nx
                    if m[j] and not seen[j]: seen[j]=1; st.append(j)
    return n
check("连通域.恰一块", n_components(cc, W3, H3), 1)
check("连通域.空图不崩", sum(largest_cc(bytearray(36), 6, 6)), 0)

# ── 以下四组由变异测试补出：283 项全过时，这四类缺陷仍能溜过去 ──

# (a) 泛洪必须自四条边都进。四个形状各自「只有一条边能进」——
#     去掉任何一条边的种子，对应那个形状就一格都泛不到。
#     初版只用了一个形状，左右边仍能进，漏掉了「只从上边进」这个变异。
EDGE_CASES = {
 "只能从下进": ["########","#......#","#......#","##....##"],
 "只能从上进": ["##....##","#......#","#......#","########"],
 "只能从左进": ["####","#..#","...#","#..#","#..#","####"],
 "只能从右进": ["####","#..#","#...","#..#","#..#","####"],
}
for nm, rows in EDGE_CASES.items():
    me, We, He = mk(rows)
    ee = flood_ext(me, We, He)
    bg = sum(1 for i in range(We*He) if not me[i])
    check(f"泛洪.{nm}.全部背景可达", sum(ee), bg)
    check(f"泛洪.{nm}.前景不被标", all(not (me[i] and ee[i]) for i in range(We*He)), True)
    check(f"泛洪.{nm}.无孔洞残留", has_hole(me, We, He), False)

# (b) 泛洪必须是四邻域。此形内部空腔只经「对角」与外界相通：
#     四连通视其为孔洞，八连通会把它当外部 —— 两者结论相反。
diag, Wd, Hd = mk([".......",".#####.",".#...#.",".#...#.",".####..","......."])
check("泛洪.需四邻域.对角缺口仍算孔洞", has_hole(diag, Wd, Hd), True)
ed = flood_ext(diag, Wd, Hd)
check("泛洪.需四邻域.腔内未被标为外部",
      all(not ed[y*Wd+x] for y in (2,3) for x in (2,3,4)), True)

# (c) Otsu 平局取先者（与网页的 v>mx 同式）。改成 >= 会取后者，
#     类间方差相同但阈值不同 —— 网页与 Python 就会分叉。
tie = [0]*100 + [100]*100 + [200]*100     # 存在多个等优阈值
t_tie = otsu(tie)
best_v = max(between_class_variance(tie, x) for x in range(256))
ties = [x for x in range(256) if abs(between_class_variance(tie, x) - best_v) < 1e-9]
check("Otsu.平局.确有多个等优阈值", len(ties) > 1, True)
check("Otsu.平局.取最小者", t_tie, min(ties))
# 钉死几个具体阈值，保证网页与 Python 不分叉
check("Otsu.定值.双峰0_200", otsu([0]*300 + [200]*300), 0)
check("Otsu.定值.三峰", otsu([20]*200 + [128]*200 + [230]*200), 20)

# (d) 点到线段距离必须把投影参数夹到 [0,1]。不夹紧就变成到「无限长直线」
#     的垂距，端点外的点会被严重低估。
far = [(0,0), (10,0), (5,1)]              # (10,0) 的投影落在线段之外
d_clamped = _seg_d2((10,0), (0,0), (5,1))
check("DP.夹紧.端点外取端点距", abs(d_clamped - (25+1)) < 1e-9, True)
# 未夹紧的垂距会小得多；DP 的取舍因此不同
check("DP.夹紧.显著大于垂距", d_clamped > (10*1)**2/(25+1) * 1.5, True)
s_far = dp_simplify(far, 3.0)             # 3² =9 < 26，故必须保留中点
check("DP.夹紧.保留端点外的远点", len(s_far), 3)

# ══ 四、边界追踪 ═════════════════════════════════════════════
NEI = {(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)}
for name, rows in SHAPES.items():
    m, W, H = mk(rows)
    check(f"追踪.{name}.无洞前提", has_hole(m, W, H), False)
    c = trace_contour(m, W, H)
    check(f"追踪.{name}.闭合", c[0] == c[-1], True)
    check(f"追踪.{name}.皆为前景", all(m[y*W+x] for x, y in c), True)
    check(f"追踪.{name}.逐点八邻接",
          all((c[i+1][0]-c[i][0], c[i+1][1]-c[i][1]) in NEI for i in range(len(c)-1)), True)
    # 无洞掩码上，追踪须覆盖全部外轮廓像素
    check(f"追踪.{name}.覆盖全外轮廓",
          set(c) >= outer_boundary(m, W, H), True)
check("追踪.空图返回空", trace_contour(bytearray(36), 6, 6), [])
single, Ws, Hs = mk([".....",".....","..#..",".....","....."])
check("追踪.单点不崩", len(trace_contour(single, Ws, Hs)) >= 1, True)

# ══ 五、Douglas–Peucker ══════════════════════════════════════
for name, rows in SHAPES.items():
    m, W, H = mk(rows)
    c = trace_contour(m, W, H)
    prev = None
    for eps in (0.5, 1.0, 2.0, 4.0, 8.0):
        s = dp_simplify(c, eps)
        check(f"DP.{name}.eps{eps}.保端点", (s[0], s[-1]), (c[0], c[-1]))
        # 输出必为输入的有序子序列
        it = iter(c); check(f"DP.{name}.eps{eps}.有序子序列",
                            all(p in it for p in s), True)
        # 被丢弃的点到其所在简化段的距离不超过 eps
        worst = 0.0
        for k in range(len(s) - 1):
            a, b = s[k], s[k+1]
            i0, i1 = c.index(a), len(c) - 1 - c[::-1].index(b)
            if i1 <= i0: continue
            for p in c[i0:i1+1]:
                worst = max(worst, _seg_d2(p, a, b))
        check(f"DP.{name}.eps{eps}.偏差有界", worst <= eps*eps + 1e-9, True)
        # eps 越大，顶点数不增
        if prev is not None:
            check(f"DP.{name}.eps{eps}.随eps单调", len(s) <= prev, True)
        prev = len(s)
# 矩形应精确还原为四角（首尾重合故 5 点）
mr, Wr, Hr = mk(SHAPES["矩形"])
check("DP.矩形还原四角", len(dp_simplify(trace_contour(mr, Wr, Hr), 1.0)), 5)
check("DP.少于三点原样返回", dp_simplify([(0,0),(1,1)], 1.0), [(0,0),(1,1)])

# ══ 六、足迹提取端到端 ═══════════════════════════════════════
def gray_from(rows):
    """'#' 为墙(0)，'.' 为空(255)"""
    H = len(rows); W = len(rows[0])
    return [0 if rows[y][x] == '#' else 255 for y in range(H) for x in range(W)], W, H

# 闭合房间 + 一个 2 格宽门洞
ROOM = ["####################",
        "#..................#",
        "#..................#",
        "#..................#",
        "#..................#",
        "#..................#",
        "#..................#",
        "##########..########",
        "####################"]
g, W, H = gray_from(ROOM)
for R in (1, 2, 3, 4):
    r = footprint_at(g, W, H, 128, R)
    check(f"足迹.R{R}.值域", 0 <= r["solidity"] <= 1.0000001, True)
    check(f"足迹.R{R}.结果无洞", has_hole(r["foot"], W, H), False)
    check(f"足迹.R{R}.恰一连通块", n_components(r["foot"], W, H) <= 1, True)
# 门洞宽 2：R 足够大才封得住，实心度随之上升
s_small = footprint_at(g, W, H, 128, 1)["solidity"]
s_big   = footprint_at(g, W, H, 128, 3)["solidity"]
check("足迹.封门洞后实心度不降", s_big >= s_small - 1e-9, True)
# 空图与全黑图不得抛异常
check("足迹.全白不崩", footprint_at([255]*(W*H), W, H, 128, 2)["area"] >= 0, True)
check("足迹.全黑不崩", footprint_at([0]*(W*H), W, H, 128, 2)["area"] >= 0, True)

print(f"[户型识别] {TOTAL-len(FAILS)}/{TOTAL} passed")
for f in FAILS[:20]: print("  FAIL", f)
sys.exit(1 if FAILS else 0)
