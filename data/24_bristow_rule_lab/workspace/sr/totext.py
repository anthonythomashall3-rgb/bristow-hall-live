import sys, os, json, warnings
warnings.filterwarnings('ignore')
from vq import load
p=sys.argv[1]
out=p+'.txt'
if os.path.exists(out): sys.exit(0)
try:
    t=load(p)
except Exception as ex:
    t=''
open(out,'w').write(t)
