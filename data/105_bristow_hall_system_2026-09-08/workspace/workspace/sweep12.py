"""The winning vacancy form (four-month mean against the maximum of that mean over the previous four months) checked for its plateau and
its margins: the quiet Sahm crossings the hub must not confirm, and the pre-1971 quiet claims proposals the 0.45 branch must not confirm."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep11.py').read().split('P("\\nbaseline v2.8")')[0].replace("out=open('sweep11.out','w')","out=open('sweep12.out','w')"))
def inrec(m): return any(p_-pd.DateOffset(months=9)<=m<=t+pd.DateOffset(months=18) for p_,t in zip(PK,TR))
def qcross(sl=0.50):
    outq=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sl:
            armed=False
            if not inrec(m): outq.append(m)
        elif not armed and v<sl: armed=True
    return outq
QC=qcross(); FQ=[dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not any(p2-pd.DateOffset(months=6)<=dd<=t2 for p2,t2 in zip(PK,TR))]
P("quiet Sahm-0.50 crossings:",[m.strftime('%Y-%m') for m in QC],"| pre-1971 quiet 0.45 proposals:",[d.strftime('%Y-%m') for d in FQ])
for vk,vb,lab_ in [(2,6,'shipped (2,6)'),(4,4,'candidate (4,4)'),(3,4,'(3,4)'),(4,3,'(4,3)'),(4,5,'(4,5)'),(5,4,'(5,4)')]:
    G=vgap(vk,vb)
    hub_m=[round(float(G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)].max()),3) for m in QC]
    fh_m=[round(float(G[(G.index>=d-pd.DateOffset(months=6))&(G.index<=d+pd.DateOffset(months=4))].max()),3) for d in FQ]
    rec=[round(float(G[(G.index>=p_-pd.DateOffset(months=6))&(G.index<=t2)].max()),3) for p_,t2 in zip(PK,TR)]
    P(f"\n{lab_}: quiet Sahm-window maxima {hub_m}; pre-1971 quiet-proposal maxima {fh_m}; the thirteen recessions' maxima {rec}  -> highest quiet {max(hub_m+fh_m):.3f}, lowest recession {min(rec):.3f}")
P("\n--- the plateau of the candidate: line swept at (4,4) ---")
for ln in [0.30,0.25,0.22,0.20,0.18,0.15,0.12,0.10]: go6(f'vac (4,4) line {ln}',vk=4,vb=4,vl=ln)
P("--- neighbouring shapes at their own best lines ---")
for vk,vb in [(3,4),(4,3),(4,5),(5,4),(5,5),(4,6)]:
    for ln in [0.25,0.20,0.15]: go6(f'vac ({vk},{vb}) line {ln}',vk=vk,vb=vb,vl=ln)
out.close()
