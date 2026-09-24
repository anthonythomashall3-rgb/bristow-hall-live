# patch_build2.py - turn bhs_build.py (v3.26) into the v3.27 builder: building permits in the housing x rate pair, the
# co-signed weak proposals confirmed by any demand object, the readings rows and notes. Run in the workspace:
#   python3 s2/patch_build2.py     (writes bhs_build.py in place; the v3.26 copy goes to _v326_backup_2026-09-10/)
import os,shutil,re
src=open('bhs_build.py').read(); os.makedirs('_v326_backup_2026-09-10',exist_ok=True); shutil.copy('bhs_build.py','_v326_backup_2026-09-10/bhs_build.py')
def rep(old,new,count=1):
    global src
    assert src.count(old)==count, f'anchor not found or not unique ({src.count(old)}): {old[:90]}'
    src=src.replace(old,new)
# 1. the housing x rate pair on permits when the walk provides them
rep("G=vgap2_asof(p['vk'],p['vb']); Hc=mkpair_asof(p['hline']); MX=Hc['mx']; Hh=HOURS_ASOF",
    "G=vgap2_asof(p['vk'],p['vb']); PERM=('mkpair_perm_asof' in globals()); Hc=(mkpair_perm_asof(p['hline']) if PERM else mkpair_asof(p['hline'])); MX=Hc['mx']; Hh=HOURS_ASOF   # v3.27: building permits in the housing x rate pair (s2/asof_permits.py)")
# 2. the pair's daily object on the same series
rep("    ev=[(pd.Timestamp(hh_pub[m]),'D',m) for m in hh_asof.index]+[(pd.Timestamp(rate_pub[m]),'U',m) for m in rate_asof.index if m>=pd.Timestamp('1960-01-01')]\n    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; rows=[]",
    "    _HH,_HP=((PERM_ASOF,PERM_PUB) if PERM else (hh_asof,hh_pub))\n    ev=[(pd.Timestamp(_HP[m]),'D',m) for m in _HH.index if m in _HP.index]+[(pd.Timestamp(rate_pub[m]),'U',m) for m in rate_asof.index if m>=pd.Timestamp('1960-01-01')]\n    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; rows=[]")
rep("        v=min(hh_asof.get(lastD,np.nan),rate_asof.get(lastU,np.nan))\n        if np.isnan(v): continue\n        rows.append((d,max(lastD,lastU),float(v)/p['hline']))",
    "        v=min(_HH.get(lastD,np.nan),rate_asof.get(lastU,np.nan))\n        if np.isnan(v): continue\n        rows.append((d,max(lastD,lastU),float(v)/p['hline']))")
# 3. the co-signed weak proposals take C1 as well as C2 - the monthly reading
rep("            sc=min(float(w.max()),best_conf(confs,t))\n            if np.isnan(sc): continue\n            if nm in STRONG:",
    "            confs_=confs+(C1 if (WEAKCO and nm in ('L','W','V','B') and not np.isnan(gCSm.get(t,np.nan)) and float(gCSm.get(t))>=1.0-1e-9) else [])   # v3.27: a co-signed weak proposal takes any confirmer\n            sc=min(float(w.max()),best_conf(confs_,t))\n            if np.isnan(sc): continue\n            if nm in STRONG:")
rep("C1=[Vc,Hpm,Spm]; C2=[Ppm,Spm,SVm]","C1=[Vc,Hpm,Spm]; C2=[Ppm,Spm,SVm]\nWEAKCO=(COS and bool(globals().get('WEAK_COSIGN',False)))   # v3.27 (walk48): the household co-signer admits a weak proposal to the strong proposers' confirmers")
# 4. the daily reading
rep("        cc=[cvals[c] for c in confs if not np.isnan(cvals[c])]\n        if not cc: continue",
    "        confs_=confs+(CONF1 if (WEAKCO and nm in ('L','W','V','B') and not np.isnan(_cs_asof(d)) and _cs_asof(d)>=1.0-1e-9) else [])   # v3.27\n        cc=[cvals[c] for c in confs_ if not np.isnan(cvals[c])]\n        if not cc: continue")
# 5. the readings rows
rep("housing x rate pair (starts and the unemployment rate, each as it stood on its release day; 1 = both halves at their lines)",
    "housing x rate pair (building permits and the unemployment rate, each as it stood on its release day; 1 = both halves at their lines)")
open('bhs_build.py','w').write(src); print('patched bhs_build.py (v3.27); backup in _v326_backup_2026-09-10/')
