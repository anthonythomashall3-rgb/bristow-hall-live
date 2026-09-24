import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, bristow_rule_v3 as B, warnings, json; warnings.filterwarnings('ignore')
from rule17_sweep import score
rows=[]
grid=[((1,0),None,1,1,'T(1,0) rs1 only'),((1,1),None,1,1,'T(1,1) rs1 only'),(None,(1,0),2,2,'P(1,0) rs2 only'),
      ((1,0),(1,0),1,2,'T(1,0)rs1 + P(1,0)rs2'),((1,1),(1,0),1,2,'T(1,1)rs1 + P(1,0)rs2'),((1,0),(1,0),2,2,'T(1,0)rs2 + P(1,0)rs2')]
for rt,rp,rst,rsp,tag in grid:
    # separate refinement smoothing per end is not a switch yet: emulate by running with the trough setting
    B.REFINE_TROUGH=rt; B.REFINE_PEAK=rp; B.REFINE_SMOOTH=rst if rp is None else (rsp if rt is None else None)
    if rt is not None and rp is not None and rst!=rsp:
        # need both: run with REFINE_SMOOTH=rst for troughs and rsp for peaks -> implement via two-pass hack below
        B.REFINE_SMOOTH_T=rst; B.REFINE_SMOOTH_P=rsp; B.REFINE_SMOOTH=None
    s=score(3,'later','all',True)
    print(f'{tag:24s} || peaks {s["p_exact"]:>2d}/{s["p_w1"]:>2d}/{s["p_w3"]:>2d} bias {s["p_bias"]:+.2f} | troughs {s["t_exact"]:>2d}/{s["t_w1"]:>2d}/{s["t_w3"]:>2d} bias {s["t_bias"]:+.2f}', flush=True)
    for c,(cp,ct) in s['per'].items():
        f=lambda v:[('-' if x is None else x) for x in v]
        print(f'    {c:24s} peaks {str(f(cp)):58s} troughs {str(f(ct))}', flush=True)
    rows.append((tag,{k:v for k,v in s.items() if k!='per'},s['per']))
B.REFINE_TROUGH=None; B.REFINE_PEAK=None; B.REFINE_SMOOTH=1
json.dump(rows,open('/home/claude/lab/refine_sweep3.json','w'),default=str)
