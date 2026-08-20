# -*- coding: utf-8 -*-
"""生成 golden 基准集：九运全部 24 坐向（下卦），另附八运对照"""
import json, csv, sys
sys.path.insert(0, ".")
from reference.feixing_engine import MOUNTAINS, pan, PALACE_NAME, liunian_center

def build(yun):
    rows = []
    for m in MOUNTAINS:
        p = pan(yun, m[4])          # 以山中心度数取正向（下卦）
        rows.append(p)
    return rows

def to_csv(rows, path):
    order = [8,1,6,3,5,7,4,9,2]     # 艮坎乾 震中兑 巽离坤
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        head = ["元运","坐向","坐山","向首","向度数","三元龙","卦法",
                "山星入中","山星飞法","向星入中","向星飞法","格局"]
        head += [f"{PALACE_NAME[g][0]}_山" for g in order]
        head += [f"{PALACE_NAME[g][0]}_向" for g in order]
        head += [f"{PALACE_NAME[g][0]}_运" for g in order]
        w.writerow(head)
        for p in rows:
            r = [p["元运"],p["坐向"],p["坐山"],p["向首"],p["向度数"],p["三元龙"],p["卦法"],
                 p["山星入中"],p["山星飞法"],p["向星入中"],p["向星飞法"],p["格局"]]
            r += [p["山星盘"][g] for g in order]
            r += [p["向星盘"][g] for g in order]
            r += [p["运盘"][g]   for g in order]
            w.writerow(r)

golden = {}
for yun in range(1, 10):
    golden[f"{yun}运"] = build(yun)

json.dump(golden, open("reference/golden_24山向.json","w"), ensure_ascii=False, indent=1)
to_csv(golden["9运"], "reference/golden_九运_24山向.csv")
to_csv(golden["8运"], "reference/golden_八运_24山向.csv")

# 流年中宫表
with open("reference/golden_流年中宫.csv","w",newline="",encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["年份","中宫星"])
    for y in range(2020, 2036): w.writerow([y, liunian_center(y)])

print("九运格局分布：")
from collections import Counter
c = Counter(p["格局"] for p in golden["9运"])
for k,v in c.most_common(): print(f"  {k}: {v}")
print("\n九运旺山旺向坐向：", [p["坐向"] for p in golden["9运"] if p["格局"]=="旺山旺向"])
print("九运上山下水坐向：", [p["坐向"] for p in golden["9运"] if p["格局"]=="上山下水"])
print("\n八运旺山旺向坐向：", [p["坐向"] for p in golden["8运"] if p["格局"]=="旺山旺向"])
print("\n流年中宫 2024-2028：", [(y, liunian_center(y)) for y in range(2024,2029)])
