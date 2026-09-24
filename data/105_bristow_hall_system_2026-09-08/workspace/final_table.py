from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur, spl
X=leg_X2(); Uc=leg_U(s_cur); Uf=leg_U(spl)
TL={k:TLG[k] for k in 'KHJS'}
def full(nm,U,confs):
    turns=chron({'U':U,'X':X},TL,confs); r=score13(turns)
    print(f"\n=== {nm} ===")
    print(f"{'peak':8}{'onset call':12}{'by':3}{'dated':8}{'err':>4}{'lag d':>6}  |  {'trough':8}{'end call':12}{'by':3}{'dated':8}{'err':>4}{'lag d':>6}")
    tr=[t for t in turns if t['kind']=='trough']
    for i,(p,t) in enumerate(zip(PK,TR)):
        if i in r['opens']:
            op=r['opens'][i]; nxt=[u for u in tr if u['published']>op['published']]; u=nxt[0] if nxt else None
            s=f"{p:%Y-%m}  {op['published']:%Y-%m-%d}  {op['leg']:2} {op['date']:%Y-%m}  {r['errs_p'][i]:+3d} {r['lags_p'][i]:5d}  |  {t:%Y-%m}  "
            s+=(f"{u['published']:%Y-%m-%d}  {u['leg']:2} {u['date']:%Y-%m}  {r['errs_t'].get(i,99):+3d} {r['lags_t'].get(i,999):5d}" if u else "open")
        else: s=f"{p:%Y-%m}  MISSED"
        print(s)
    print("other onset calls:",r['other'])
    lp=list(r['lags_p'].values()); ep=list(r['errs_p'].values()); lt=list(r['lags_t'].values()); et=list(r['errs_t'].values())
    lp71=[r['lags_p'][i] for i in range(5,13)]
    print(f"peaks {len(lp)}/13: lag median {np.median(lp):.0f} d (1973 on: {np.median(lp71):.1f}), mean {np.mean(lp):.1f}, worst {max(lp)}, before month-end {sum(1 for l in lp if l<=0)}, <=7 d {sum(1 for l in lp if l<=7)}, <=31 d {sum(1 for l in lp if l<=31)}; dates exact {sum(1 for e in ep if e==0)}, within one {sum(1 for e in ep if abs(e)<=1)}, within three {sum(1 for e in ep if abs(e)<=3)}, mae {np.mean(np.abs(ep)):.2f}")
    print(f"troughs {len(lt)}/13: lag median {np.median(lt):.0f} d, worst {max(lt)}, <=7 d {sum(1 for l in lt if l<=7)}, <=31 d {sum(1 for l in lt if l<=31)}; dates exact {sum(1 for e in et if e==0)}, within one {sum(1 for e in et if abs(e)<=1)}, mae {np.mean(np.abs(et)):.2f}")
    # live standing
    last=[t for t in turns if t['published']>=pd.Timestamp('2023-01-01')]
    print("turns since 2023:",[(t['kind'],t['published'].strftime('%Y-%m-%d'),t['leg'],t['date'].strftime('%Y-%m')) for t in last])
full("CORE (IUR 0.50 | Sahm 0.50 & vacancy 0.36), U confirmed by vacancy only; closers K,H,J,S", Uc, ['V'])
full("CORE + PAIRS (U confirmed by vacancy | housing x rate | hours x nondurable); closers K,H,J,S", Uc, ['V','H','P'])
full("CORE + PAIRS, U on the Department's advance first prints (2002 on)", Uf, ['V','H','P'])
