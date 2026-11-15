#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): build the BASE state asset on the Mac, once, from the files the live tools were
traced reading (ops/live_tools/state_files.txt: every file opened or imported by the State page chain, the stress map v3.1 build and
checks, s2/tool_inputs_mac.py, the shadow tool live_union_823.py and its feed refresher refresh_feeds_824.py; traced with a Python audit
hook on 15 Nov 2026) plus the folders their globs need (ops/live_tools/state_dirs.txt).
Paths are kept exactly as on the Mac (Users/anthonyhall/Projects/..., Volumes/Sandisk G/...), so the scripts run unchanged in the runner.
The three BLS flat files of the 191 collector are reduced to the series the tools read (same lines, same format; bls_api_1052.py keeps
them current in the runner). Writes <out>/base-<stamp>.tar.gz, its .sha256, and MANIFEST (sha256 of every file) inside the archive.
Usage: python3 make_base_on_mac.py <out dir>"""
import os, sys, io, gzip, time, tarfile, hashlib
H = os.path.dirname(os.path.abspath(__file__))
FIPS = ['01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
        '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56']
SUPER = ['00', '10', '20', '15', '30', '40', '50', '55', '60', '65', '70', '80', '90']
KEEP = {'ces_all.txt.gz': {f'CES{c}00000001' for c in SUPER if c != '15'},
        'state_metro_payrolls_all.txt.gz': {f'SMS{f}00000{c}00000001' for f in FIPS for c in SUPER},
        'laus_all_states_sa.txt.gz': {f'LASST{f}0000000000003' for f in FIPS}}
def reduced(path, keep):
    out = io.BytesIO(); n = 0
    with gzip.open(path, 'rt', encoding='latin-1') as f, gzip.GzipFile(fileobj=out, mode='wb', mtime=0) as g:
        g.write(next(f).encode('latin-1'))
        for line in f:
            if line[:line.find('\t')].strip() in keep: g.write(line.encode('latin-1')); n += 1
    return out.getvalue(), n
def main():
    od = sys.argv[1]; os.makedirs(od, exist_ok=True); stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    files = [l.rstrip('\n') for l in open(os.path.join(H, 'state_files.txt')) if l.strip()]
    dirs = [l.rstrip('\n') for l in open(os.path.join(H, 'state_dirs.txt')) if l.strip()]
    bls = '/191_standing_collector_2026-09-16/warehouse/bls_flat_files/'
    for nm in KEEP:   # the State fallback file is in the base even if no trace opened it
        p = 'Users/anthonyhall/Projects/Onset Detector Data' + bls + nm
        if p not in files: files.append(p)
    man = []; tp = os.path.join(od, f'base-{stamp}.tar.gz')
    with tarfile.open(tp, 'w:gz', compresslevel=6) as T:
        for d in sorted(set(dirs)):
            ti = tarfile.TarInfo(d); ti.type = tarfile.DIRTYPE; ti.mode = 0o755; ti.mtime = int(os.path.getmtime('/' + d)); T.addfile(ti)
        for rel in sorted(set(files)):
            src = '/' + rel; nm = os.path.basename(rel)
            if bls in src and nm in KEEP:
                b, n = reduced(src, KEEP[nm]); print('reduced', nm, n, 'lines', len(b), 'bytes')
            else: b = open(src, 'rb').read()
            ti = tarfile.TarInfo(rel); ti.size = len(b); ti.mode = 0o644; ti.mtime = int(os.path.getmtime(src)); T.addfile(ti, io.BytesIO(b))
            man.append(f'{hashlib.sha256(b).hexdigest()}  {rel}')
        mb = ('\n'.join(man) + '\n').encode(); ti = tarfile.TarInfo('Users/anthonyhall/.lts/MANIFEST-base-' + stamp + '.sha256'); ti.size = len(mb); ti.mtime = int(time.time()); T.addfile(ti, io.BytesIO(mb))
    h = hashlib.sha256(open(tp, 'rb').read()).hexdigest(); open(tp + '.sha256', 'w').write(f'{h}  {os.path.basename(tp)}\n')
    print(tp, os.path.getsize(tp), h, len(man), 'files')
if __name__ == '__main__': main()
