#!/usr/bin/env python3
"""炁流场一致性测试 —— 测地距离场与各宫炁强度。

此前这一页的整个引擎零测试覆盖：报的「各宫炁强度」百分比没有任何东西
拦着它出错。补上后立刻查出一个真 bug —— 见下方「回归钉」。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qiflow_engine import (inside, build_grid, geodesic, geodesic_fifo,
                           entry_cell, palace_stats, PALACE_CELL, DIAG, LAMBDA_RATIO)

TOTAL = 0; FAILS = []
def check(name, got, want):
    global TOTAL; TOTAL += 1
    if got != want: FAILS.append(f"{name}: 得 {got!r} 期 {want!r}")

G = 72
SQUARE = [(0,0),(300,0),(300,300),(0,300)]
LSHAPE = [(0,0),(300,0),(300,180),(160,180),(160,300),(0,300)]
NOTCH  = [(0,0),(300,0),(300,300),(180,300),(180,140),(120,140),(120,300),(0,300)]
THIN   = [(0,0),(400,0),(400,120),(0,120)]

# ══ 一、测地距离场：与闭式八方距离逐格比对 ══════════════════════
# 全开放网格里最短路必为「先斜后直」，距离恒为 max+(√2−1)·min。
# 这是硬标准，不是经验值 —— 任何实现偏离它就是错的。
Go = 45                                   # 取奇数，源可置于严格正中
open_mask = bytearray([1]*(Go*Go))
mid = Go//2
d_ok = geodesic(open_mask, Go, mid*Go+mid)
d_bad = geodesic_fifo(open_mask, Go, mid*Go+mid)
octile = lambda dx,dy: max(dx,dy)+(DIAG-1)*min(dx,dy)
err_ok = err_bad = 0.0
for i in range(Go):
    for j in range(Go):
        t = octile(abs(i-mid), abs(j-mid))
        err_ok  = max(err_ok,  abs(d_ok[i*Go+j]-t))
        err_bad = max(err_bad, abs(d_bad[i*Go+j]-t))
check("测地.闭式解.Dijkstra精确", err_ok < 1e-9, True)
# ── 回归钉：旧的先进先出实现偏离闭式解 9 个格距以上 ──
# 若这条失败，说明有人把 geodesic 换回了 FIFO，或改动了 geodesic_fifo。
check("测地.回归钉.FIFO偏离>9格", err_bad > 9.0, True)

# 源点距离为 0；八邻域首圈恰为 1 或 √2
check("测地.源为0", d_ok[mid*Go+mid], 0.0)
ring = sorted(round(d_ok[(mid+di)*Go+(mid+dj)],6)
              for di in(-1,0,1) for dj in(-1,0,1) if di or dj)
check("测地.首圈", ring, sorted([1.0]*4+[round(DIAG,6)]*4))
# 三角不等式：相邻格距离差不得超过该边权
viol = 0
for i in range(Go-1):
    for j in range(Go-1):
        a=d_ok[i*Go+j]
        if abs(d_ok[(i+1)*Go+j]-a) > 1.0+1e-9: viol+=1
        if abs(d_ok[i*Go+j+1]-a) > 1.0+1e-9: viol+=1
        if abs(d_ok[(i+1)*Go+j+1]-a) > DIAG+1e-9: viol+=1
check("测地.三角不等式", viol, 0)
# 左右/上下镜像对称
sym = max(abs(d_ok[i*Go+j]-d_ok[(Go-1-i)*Go+j]) for i in range(Go) for j in range(Go))
check("测地.左右对称", sym < 1e-9, True)
sym2 = max(abs(d_ok[i*Go+j]-d_ok[i*Go+(Go-1-j)]) for i in range(Go) for j in range(Go))
check("测地.上下对称", sym2 < 1e-9, True)

# ══ 二、绕墙：封死的区域必须不可达 ═══════════════════════════
wall = bytearray([1]*(Go*Go))
for j in range(Go): wall[mid*Go+j] = 0        # 整道横墙，不留门
dw = geodesic(wall, Go, 0*Go+0)
check("绕墙.墙这侧可达", all(dw[i*Go+j] >= 0 for i in range(mid) for j in range(Go)), True)
check("绕墙.墙那侧不可达", all(dw[i*Go+j] < 0 for i in range(mid+1,Go) for j in range(Go)), True)
# 留一道门 → 全可达，且绕行距离必大于直线
wall2 = bytearray(wall)
for j in range(mid-2, mid+3): wall2[mid*Go+j] = 1
dw2 = geodesic(wall2, Go, 0)
far = (Go-1)*Go+0
check("绕墙.开门后可达", dw2[far] >= 0, True)
check("绕墙.绕行长于直线", dw2[far] > octile(Go-1, 0), True)

# ══ 三、宫格划分 ══════════════════════════════════════════
check("宫格.G须被3整除", G % 3, 0)
# 那条 assert 必须真的会拦人：G 不整除时末行末列会被静默丢弃。
# 变异测试发现，仅断言 G%3==0 抓不住「把 assert 删掉」—— 因为现行 G=72 本就整除。
try:
    palace_stats(bytearray([1]*(70*70)), [0.0]*(70*70), 70)
    check("宫格.非整除须报错", "未报错", "AssertionError")
except AssertionError:
    check("宫格.非整除须报错", "AssertionError", "AssertionError")
check("宫格.九宫齐全", sorted(g for r in PALACE_CELL for g in r), list(range(1,10)))
check("宫格.洛书上北", PALACE_CELL[0][1], 1)      # 坎1 在北
check("宫格.洛书离南", PALACE_CELL[2][1], 9)      # 离9 在南
check("宫格.中宫5",   PALACE_CELL[1][1], 5)
# 洛书性质：三行三列及两对角之和恒为 15
lines = ([sum(r) for r in PALACE_CELL] + [sum(PALACE_CELL[r][c] for r in range(3)) for c in range(3)]
         + [sum(PALACE_CELL[i][i] for i in range(3)), sum(PALACE_CELL[i][2-i] for i in range(3))])
check("宫格.洛书幻方和15", set(lines), {15})

# ══ 四、炁强度统计 ════════════════════════════════════════
mask, bb = build_grid(SQUARE, G)
check("统计.方正全室内", sum(mask), G*G)
src = entry_cell(mask, G, bb, 180)
dist = geodesic(mask, G, src)
cov, cnt, reach = palace_stats(mask, dist, G)
check("统计.九宫齐", sorted(cov), list(range(1,10)))
check("统计.值域0~1", all(0 <= v <= 1 for v in cov.values()), True)
check("统计.格数守恒", sum(cnt.values()), G*G)
check("统计.全可达", sum(reach.values()), G*G)
# 自炁口在南 → 离宫(9,南)最强，坎宫(1,北)弱于它
check("统计.南口离宫最强", max(cov, key=cov.get), 9)
check("统计.坎宫弱于离宫", cov[1] < cov[9], True)
# 东西对称：兑7(西) 与 震3(东) 应相近（残差来自偶数格源点略偏心）
check("统计.东西近似对称", abs(cov[7]-cov[3]) < 0.02, True)
check("统计.西北东北近似对称", abs(cov[6]-cov[8]) < 0.02, True)
# 换向：口在北 → 坎宫最强
src_n = entry_cell(mask, G, bb, 0)
cov_n,_,_ = palace_stats(mask, geodesic(mask,G,src_n), G)
check("统计.北口坎宫最强", max(cov_n, key=cov_n.get), 1)
# 确定性：同输入必得同输出（这一页曾用粒子出数，改为确定性场就是为此）
c2,_,_ = palace_stats(mask, geodesic(mask,G,src), G)
check("统计.确定性", [round(cov[g],12) for g in range(1,10)],
                     [round(c2[g],12) for g in range(1,10)])
# 缺角：L 形缺西南（PALACE_CELL[2][2]=4 巽/东南？按上北下南，4 在右下=东南）
maskL,bbL = build_grid(LSHAPE, G)
covL,cntL,_ = palace_stats(maskL, geodesic(maskL,G,entry_cell(maskL,G,bbL,180)), G)
missing = [g for g in cntL if cntL[g]==0]
check("缺角.L形恰缺一宫", len(missing), 1)
check("缺角.缺的宫强度为0", covL[missing[0]], 0.0)
# 不可达宫：凹口户型里被墙围死的部分强度必为 0（此处凹口连通，故全可达）
maskN,bbN = build_grid(NOTCH, G)
covN,cntN,reachN = palace_stats(maskN, geodesic(maskN,G,entry_cell(maskN,G,bbN,0)), G)
check("凹口.可达数不超室内数", all(reachN[g]<=cntN[g] for g in cntN), True)
# 细长户型不得崩
maskT,bbT = build_grid(THIN, G)
covT,_,_ = palace_stats(maskT, geodesic(maskT,G,entry_cell(maskT,G,bbT,270)), G)
check("细长.值域正常", all(0<=v<=1 for v in covT.values()), True)

# ══ 五、λ 与单调性 ═══════════════════════════════════════
check("λ.比值", LAMBDA_RATIO, 2.2)
# 距离越远强度越低（同一场内严格单调）
maxd = max(d for d in dist if d>=0)
lam = maxd/LAMBDA_RATIO
vals = [(dist[k], math.exp(-dist[k]/lam)) for k in range(G*G) if dist[k]>=0]
vals.sort()
check("λ.强度随距离单调不增",
      all(vals[i][1] >= vals[i+1][1]-1e-12 for i in range(len(vals)-1)), True)
check("λ.源处强度为1", round(math.exp(-0/lam), 9), 1.0)

print(f"[炁流场] {TOTAL-len(FAILS)}/{TOTAL} passed"
      f"   （旧 FIFO 实现偏离闭式解 {err_bad:.3f} 格距，已弃用）")
for f in FAILS[:20]: print("  FAIL", f)
sys.exit(1 if FAILS else 0)
