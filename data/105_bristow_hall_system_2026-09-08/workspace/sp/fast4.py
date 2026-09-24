for sl in (0.3333,0.30,0.2667):
    q=dict(p0); q['sahm']=sl; r,t=build_v(q); report(f"hub line {sl}",r,t)
print('Sahm gap first prints, 2023-10 .. 2024-08 (month: gap, release day):',[(m.strftime('%Y-%m'),round(float(v),3),rel[m].date().isoformat() if m in rel else None) for m,v in g['2023-10':'2024-08'].items()])
