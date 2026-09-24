"""Colombia against the Banco de la Republica's reference chronology (Ensayos sobre Politica
Economica 110, 2025, 'Caracteristicas cuantitativas de los ciclos economicos en Colombia',
Cuadro 6, columns (6)-(7), the 'cronologia IDA' - the cumulative diffusion index over the
Bank's coincident set; the Bank proposes a dating committee, the CROC, but none exists yet, so
this is an accepted ruling and not an official one).  Peaks June 1982, December 1997, February
2008, October 2019, August 2022; troughs March 1984, August 1999, March 2009, April 2020
(lab/acq/banrep/cuadro_i036.png).  Panel: the OECD channels on disk for Colombia (production
from 1990, employment from 2007, retail volume from 2013), level route, shipped configuration."""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/cmp')
import bench, pandas as pd
from ecri_countries import run, cnt, panel
bench.PANELS.setdefault('Colombia',{'ch':[],'chrono':[],'freq':'M'}); bench.CONCEPT['Colombia']='level'
chron=[('1982-06','1984-03'),('1997-12','1999-08'),('2008-02','2009-03'),('2019-10','2020-04')]
chs=panel('COL')
print(f"### Colombia — channels: {[(nm,str(s.index.min().date())[:7]) for nm,s in chs]}")
rows,ep,et=run('COL','Colombia',chron,chs)
print(f"Banco de la Republica IDA chronology, {len(chron)} contractions: peaks {cnt(ep)} | troughs {cnt(et)}")
for r in rows: print('   ',r)
