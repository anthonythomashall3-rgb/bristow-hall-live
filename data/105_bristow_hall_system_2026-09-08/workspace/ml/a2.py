G=vgap2(p0['vk'],p0['vb']); hi=V0.rolling(4).mean().rolling(4).max().shift(1)
for y in (2001,2008,2019,2020,2022,2023,2025):
    s=V0[str(y)]; gg=G[str(y)]
    print(y,'vacancy rate level median %.2f'%s.median(),'| 4-month-mean gap max %.2f'%gg.max(),'| 0.20 line as percent of the prior 4-month high: %.1f%%'%(100*0.20/float(hi[str(y)].median())))
print('vacancy confirmer at its line (gap>=0.20), months per year:',{y:int((G[str(y)]>=0.20).sum()) for y in range(2001,2027)})
