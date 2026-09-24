import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, warnings, json; warnings.filterwarnings('ignore')
from rule17_sweep import score
rows=[]
for rt,rp,tag in (((1,1),(1,0),'T(1,1)rs1 + P(1,0)rs2, window from unrefined trough'),((1,0),(1,0),'T(1,0)rs1 + P(1,0)rs2, window from unrefined trough')):
    B.REFINE_TROUGH=rt; B.REFINE_PEAK=rp; B.REFINE_SMOOTH=None; B.REFINE_SMOOTH_T=1; B.REFINE_SMOOTH_P=2
    s=score(3,'later','all',True)
    print(f'{tag:52s} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f} | Q {s["qp_exact"]}/{s["qt_exact"]} of {s["qn"]}', flush=True)
    for c,(cp,ct) in s['per'].items():
        f=lambda v:[('-' if x is None else x) for x in v]
        print(f'    {c:24s} peaks {str(f(cp)):58s} troughs {str(f(ct))}', flush=True)
    rows.append((tag,{k:v for k,v in s.items() if k!='per'},s['per']))
B.REFINE_TROUGH=None; B.REFINE_PEAK=None; B.REFINE_SMOOTH=1
json.dump(rows,open('/home/claude/lab/refine_sweep4.json','w'),default=str)
