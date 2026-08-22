#!/usr/bin/env python3
"""变异自检 —— 验证测试套件本身是否有效。

测试全过不等于测试有效。做法：往参考实现里注入一个已知缺陷，再跑对应
测试；若测试仍全过，说明那类缺陷有盲区。

本项目靠它补出 6 处盲区，最要紧的一处是：节气时刻的 ±2 分容差
放得下整个 ΔT（≈69 秒＝1.15 分）—— 把 UT→TT 转换整个删掉仍能全过，
而加 ΔT 的全部理由就是它有影响。判据改为「分秒不差的个数」后
（含 ΔT 19/20，漏掉 0/20），一测即穿。

用法：python3 mutation_check.py
"""
import subprocess, sys, re, shutil, pathlib, tempfile

ROOT = pathlib.Path(__file__).parent
REF = ROOT / "reference"

# (参考实现, 测试, [(变异名, 原文, 改成), ...])
PLAN = [
 ("plan_cv_engine.py", "plan_cv_test.py", [
   ("Otsu 少扫一档", "for t in range(256):\n        w_b += h[t]", "for t in range(255):\n        w_b += h[t]"),
   ("Otsu 平局取后者", "if v > best:", "if v >= best:"),
   ("膨胀半径少 1", "lo, hi = max(0, x - r), min(W - 1, x + r)", "lo, hi = max(0, x - r), min(W - 1, x + r - 1)"),
   ("膨胀漏掉纵向那遍",
    "    for x in range(W):\n        for y in range(H):\n            lo, hi = max(0, y - r), min(H - 1, y + r)",
    "    for x in range(W):\n        for y in range(H):\n            lo, hi = max(0, y - 0), min(H - 1, y + 0)"),
   ("腐蚀忘了取反回来", "return bytearray(0 if v else 1 for v in d)", "return bytearray(1 if v else 0 for v in d)"),
   ("泛洪只从上边进", "    for x in range(W):\n        push(x, 0); push(x, H - 1)", "    for x in range(W):\n        push(x, 0)"),
   ("泛洪改八邻域", "        if y < H - 1: push(x, y + 1)",
    "        if y < H - 1: push(x, y + 1)\n        if x>0 and y>0: push(x-1,y-1)\n        if x<W-1 and y<H-1: push(x+1,y+1)"),
   ("最大连通域取最小", "if len(cells) > len(best):", "if best and len(cells) < len(best):"),
   ("追踪起始回溯方向写错", "cur = (sx, sy); b = 4", "cur = (sx, sy); b = 0"),
   ("追踪邻域顺序反了", "d = (b + 1 + k) % 8", "d = (b - 1 - k) % 8"),
   ("DP 丢掉端点", "return [pts[0], pts[-1]]", "return [pts[0]]"),
   ("DP 阈值比较反向", "if mx > eps * eps:", "if mx < eps * eps:"),
   ("DP 点线距离忘了夹紧", "t = max(0.0, min(1.0, t))", "pass"),
 ]),
 ("liuyao_engine.py", "liuyao_test.py", [
   ("八宫归魂只变两爻", "for i in range(3): gui[i] ^= 1", "for i in range(2): gui[i] ^= 1"),
   ("纳甲阴卦也顺行", "step = 2 if fwd else -2", "step = 2"),
   ("世应改隔两位", "return shi + 3 if shi <= 3 else shi - 3", "return shi + 2 if shi <= 4 else shi - 4"),
   ("六亲生我我生互换", 'if SHENG[other] == me:     return "父母"', 'if SHENG[other] == me:     return "子孙"'),
   ("六神起首表错一位", '"庚":4,"辛":4', '"庚":3,"辛":3'),
   ("旬空取 +9/+10", "return ZHI12[(z0 + 10) % 12], ZHI12[(z0 + 11) % 12]",
                     "return ZHI12[(z0 + 9) % 12], ZHI12[(z0 + 10) % 12]"),
 ]),
 ("ziba_engine.py", "ziba_test.py", [
   ("流年改顺行", "return _wrap(7 - 1 - (solar_year - 1984))", "return _wrap(7 - 1 + (solar_year - 1984))"),
   ("流年起宫改八白", "return _wrap(7 - 1 - (solar_year - 1984))", "return _wrap(8 - 1 - (solar_year - 1984))"),
   ("流月起宫表互换", "if year_zhi_idx in ZI_WU_MAO_YOU:   base = 8", "if year_zhi_idx in ZI_WU_MAO_YOU:   base = 5"),
   ("流时阴阳遁起宫互换", "return 9 if yin else 1", "return 1 if yin else 9"),
   ("符头改恒取在前", "return before if (j - before) <= (after - j) else after", "return before"),
   ("遁局判据漏 not", "yin = after_xz and not after_dz", "yin = after_xz"),
 ]),
 ("qiflow_engine.py", "qiflow_test.py", [
   ("对角权改 1", "w = diag if (di and dj) else 1.0", "w = 1.0"),
   ("松弛条件反向", "if d + w < dist[nk] - 1e-12:", "if d + w > dist[nk] - 1e-12:"),
   ("洛书上下翻转", "PALACE_CELL = [[6, 1, 8], [7, 5, 3], [2, 9, 4]]", "PALACE_CELL = [[2, 9, 4], [7, 5, 3], [6, 1, 8]]"),
   ("λ 比值改 1", "LAMBDA_RATIO = 2.2", "LAMBDA_RATIO = 1.0"),
   ("宫格丢末行末列", 'assert G % 3 == 0, "G 必须能被 3 整除，否则末行末列会被静默丢弃"', "pass"),
 ]),
 ("solar_hp.py", "solar_term_test.py", [
   ("漏掉 ΔT 转换", "jd = jd + delta_t(jd)/86400.0", "pass"),
   ("章动符号反了", "dpsi = (-17.20*math.sin(math.radians(omega))", "dpsi = (+17.20*math.sin(math.radians(omega))"),
   ("光行差符号反了", "aberr = -20.4898/R/3600.0", "aberr = +20.4898/R/3600.0"),
   ("日心转地心漏 180", "theta = math.degrees(L) + 180.0", "theta = math.degrees(L)"),
 ]),
]

# 等价变异：语义未变，测试抓不到是正确的，不计入失败
EQUIVALENT = {
  "Otsu 少扫一档": "t=255 时 w_b==n、w_f==0，循环在算方差前就 break，该档恒不可选",
}

def main():
    total = caught = equiv = 0
    for src, test, muts in PLAN:
        sp = REF / src; tp = REF / test
        with tempfile.NamedTemporaryFile(suffix=".bak", delete=False) as f:
            bak = f.name
        shutil.copy(sp, bak)
        print(f"\n=== {src} → {test} ===")
        try:
            for name, old, new in muts:
                s = pathlib.Path(bak).read_text(encoding="utf-8")
                if s.count(old) != 1:
                    print(f"  {name:<22}⚠ 锚点 {s.count(old)} 处，跳过"); continue
                sp.write_text(s.replace(old, new), encoding="utf-8")
                r = subprocess.run([sys.executable, str(tp)], capture_output=True, text=True)
                hit = r.returncode != 0
                total += 1
                if name in EQUIVALENT:
                    equiv += 1
                    mark = "⊘ 等价变异" if not hit else "✅ 抓到"
                    print(f"  {name:<22}{mark}  （{EQUIVALENT[name]}）")
                    continue
                caught += 1 if hit else 0
                m = re.search(r"(\d+)/(\d+) passed", r.stdout)
                d = f"{int(m.group(2))-int(m.group(1))} 项失败" if m and hit else ("全过 —— 有盲区" if not hit else "崩溃")
                print(f"  {name:<22}{'✅ 抓到' if hit else '❌ 漏掉'}  {d}")
        finally:
            shutil.copy(bak, sp)
    real = total - equiv
    print(f"\n{'─'*46}")
    print(f"注入 {total} 个缺陷：{caught}/{real} 被抓到，另 {equiv} 个为等价变异（不可抓）")
    return 0 if caught == real else 1

if __name__ == "__main__":
    sys.exit(main())
