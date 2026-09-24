import os, sys, time, cProfile, pstats, io, warnings
sys.path.insert(0,'/home/claude/w'); warnings.filterwarnings('ignore')
os.environ.setdefault('US_DATA','/mnt/user-data/outputs/us')
import us_screen_local as L
L._apply(0); L.S.init()
sids=[s for s in ['TOTBORR','INDPRO','PAYEMS','HOUST','M1SL'] if os.path.exists('/mnt/user-data/outputs/us/%s.csv'%s)][:3]
t0=time.time(); [L.one_any(s) for s in sids]; print('%d channels %.2fs (%.2fs each)'%(len(sids),time.time()-t0,(time.time()-t0)/len(sids)))
pr=cProfile.Profile(); pr.enable(); [L.one_any(s) for s in sids]; pr.disable()
b=io.StringIO(); pstats.Stats(pr,stream=b).sort_stats('tottime').print_stats(14)
print('\n'.join(b.getvalue().splitlines()[4:22]))
