import os, subprocess, re
OUT='/home/claude/lab/nber/data'; os.makedirs(OUT,exist_ok=True)
BASE='https://data.nber.org/databases/macrohistory/rectdata'
SER={  # id -> (chapter, our channel name)
 'm01001':('01','business activity index (Babson)'),
 'm01128':('01','electric power production'),
 'm01130a':('01','pig iron production'),
 'm01135a':('01','steel ingot production'),
 'm03031':('03','freight carloadings'),
 'm06002b':('06','department store sales'),
 'm08010b':('08','manufacturing employment'),
 'm08069b':('08','manufacturing payrolls'),
 'm08146':('08','durable goods employment'),
 'm12007':('12','business activity index (AT&T)'),
 'm16111':('16','NBER employment diffusion index'),
 'm16113':('16','NBER income diffusion index'),
}
for sid,(ch,nm) in SER.items():
    url=f'{BASE}/{ch}/{sid}.dat'
    p=subprocess.run(['curl','-sS','-A','Mozilla/5.0','--max-time','60',url],capture_output=True,text=True)
    rows=[]
    for line in p.stdout.splitlines():
        m=re.match(r'\s*(\d{4})\s+(\d{1,2})\s+(-?[0-9]+(?:\.[0-9]*)?|-?\.[0-9]+)\s*$', line)
        if not m: continue
        y,mo,v=int(m.group(1)),int(m.group(2)),float(m.group(3))
        if not (1<=mo<=12): continue
        rows.append((f'{y:04d}-{mo:02d}-01',v))
    if len(rows)<60: print(f'{sid}: only {len(rows)} rows'); continue
    with open(f'{OUT}/{sid}.csv','w') as g:
        g.write('date,value\n')
        for d,v in rows: g.write(f'{d},{v}\n')
    print(f'{sid:9s} {nm:34s} n={len(rows):4d}  {rows[0][0][:7]}..{rows[-1][0][:7]}')
