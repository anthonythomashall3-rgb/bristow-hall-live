import builtins, sys, os
W="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/24_bristow_rule_lab/workspace"
_open=builtins.open
def fix(p):
    if isinstance(p,str) and p.startswith("/home/claude"): return W+p[len("/home/claude"):]
    return p
def myopen(file,*a,**k): return _open(fix(file),*a,**k)
builtins.open=myopen
for sub in ("","/lab","/lab/weekly","/lab/fh","/lab/rt","/lab/slack","/lab/dol","/lab/cps"):
    sys.path.insert(0,W+sub)
_exists=os.path.exists
os.path.exists=lambda p: _exists(fix(p))
