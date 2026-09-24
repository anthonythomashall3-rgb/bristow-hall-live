import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, pandas as pd, numpy as np, warnings, json, itertools; warnings.filterwarnings('ignore')
from rule17_sweep import score
rows=[]
grid=[(None,None,'shipped'),((2,1),None,'T refine (2,1)'),((1,1),None,'T refine (1,1)'),((2,2),None,'T refine (2,2)'),((3,1),None,'T refine (3,1)'),
      (None,(2,1),'P refine (2,1)'),(None,(1,1),'P refine (1,1)'),(None,(2,2),'P refine (2,2)'),((2,1),(2,1),'both (2,1)'),((1,1),(1,1),'both (1,1)')]
for rt,rp,tag in grid:
    B.REFINE_TROUGH=rt; B.REFINE_PEAK=rp
    s=score(3,'later','all',True)
    print(f'{tag:18s} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f} | Q {s["qp_exact"]}/{s["qt_exact"]} of {s["qn"]}', flush=True)
    rows.append((tag,{k:v for k,v in s.items() if k!='per'},s['per']))
B.REFINE_TROUGH=None; B.REFINE_PEAK=None
json.dump(rows,open('/home/claude/lab/refine_sweep.json','w'),default=str)
