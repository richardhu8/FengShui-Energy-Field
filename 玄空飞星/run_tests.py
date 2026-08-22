#!/usr/bin/env python3
"""跑全部基准测试。加 --mutate 顺带做变异自检。

变异自检的用处：测试全过不等于测试有效。往参考实现里注入已知缺陷，
若测试仍全过，说明那类缺陷有盲区。本项目靠它补出过 6 处盲区 ——
其中最要紧的一处是节气容差 ±2 分放得下整个 ΔT（≈69 秒）。
"""
import subprocess, sys, re, shutil, pathlib

ROOT = pathlib.Path(__file__).parent
SUITES = [
    ("玄空 / 命理 / 天时", "conformance_test.py"),
    ("节气 / 四柱",        "solar_term_test.py"),
    ("六爻纳甲",           "liuyao_test.py"),
    ("紫白飞星",           "ziba_test.py"),
    ("炁流场",             "qiflow_test.py"),
    ("户型识别",           "plan_cv_test.py"),
]

def run(path):
    r = subprocess.run([sys.executable, str(ROOT / "reference" / path)],
                       capture_output=True, text=True)
    m = re.findall(r"(\d+)/(\d+) passed", r.stdout)
    return (int(m[-1][0]), int(m[-1][1]), r.returncode, r.stdout.strip()) if m else (0, 0, 1, r.stdout + r.stderr)

def main():
    total = passed = 0; bad = []
    print(f"{'套件':<22}{'结果':<16}{'状态'}")
    print("-" * 46)
    for label, f in SUITES:
        p, t, rc, out = run(f)
        total += t; passed += p
        if rc: bad.append((label, out))
        print(f"{label:<22}{f'{p}/{t}':<16}{'✅' if rc == 0 else '❌'}")
    print("-" * 46)
    print(f"{'合计':<22}{f'{passed}/{total}':<16}{'✅' if not bad else '❌'}")
    for label, out in bad:
        print(f"\n--- {label} ---\n{out}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
