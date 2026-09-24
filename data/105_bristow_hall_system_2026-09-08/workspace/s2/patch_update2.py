# patch_update2.py - bhs_update.py for v3.27: refresh the building-permits vintage table and current file beside the others.
# Run in the workspace: python3 s2/patch_update2.py
import shutil,os
src=open('bhs_update.py').read(); os.makedirs('_v326_backup_2026-09-10',exist_ok=True); shutil.copy('bhs_update.py','_v326_backup_2026-09-10/bhs_update.py')
old="for s in ['UNRATE','HOUST','AWHMAN','NDMANEMP','JTSJOL','CLF16OV']:"
assert src.count(old)==1
src=src.replace(old,"for s in ['UNRATE','HOUST','AWHMAN','NDMANEMP','JTSJOL','CLF16OV','PERMIT']:   # PERMIT: the housing x rate pair reads building permits from v3.27")
old2="refresh_series('DCPF1M',os.path.join(C25,'fred_daily','DCPF1M.csv'))"
assert src.count(old2)==1
src=src.replace(old2,old2+"\nrefresh_series('PERMIT','cache/surveys/PERMIT.csv')   # the current file of building permits (v3.27; the pair reads the vintage table where it exists, this file before August 1999)")
open('bhs_update.py','w').write(src); print('patched bhs_update.py (v3.27); backup in _v326_backup_2026-09-10/')
