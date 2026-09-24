import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, warnings, json; warnings.filterwarnings('ignore')
from rule17_sweep import score
rows=[]
grid=[]
for rs in (1,2):
    for w in ((1,0),(2,0),(1,1),(1,2),(0,1)):
        grid.append((w,None,rs,f'T{w} rs{rs}'))
    for w in ((1,0),(2,0),(1,1),(1,2),(0,1)):
        grid.append((None,w,rs,f'P{w} rs{rs}'))
for rt,rp,rs,tag in grid:
    B.REFINE_TROUGH=rt; B.REFINE_PEAK=rp; B.REFINE_SMOOTH=rs
    s=score(3,'later','all',True)
    print(f'{tag:16s} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f}', flush=True)
    rows.append((tag,{k:v for k,v in s.items() if k!='per'},s['per']))
B.REFINE_TROUGH=None; B.REFINE_PEAK=None; B.REFINE_SMOOTH=1
json.dump(rows,open('/home/claude/lab/refine_sweep2.json','w'),default=str)
