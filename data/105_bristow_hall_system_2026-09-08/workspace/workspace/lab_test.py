import sys, time, io, contextlib
t0=time.time()
_MARK = "# ---- the walk " + "itself"
src=open('walk94.py').read().split(_MARK)[0]
sys.argv=['walk94.py','2027','2026','wlabtest']
buf=io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src,'walk94_head','exec'))
print('preamble ok %.1f s'%(time.time()-t0)); print(buf.getvalue()[-1500:])
import pickle
chosen=pickle.load(open('cache/w94_chosen_1962.pkl','rb')) if __import__('os').path.exists('cache/w94_chosen_1962.pkl') else None
print('w94 chosen cache present:', chosen is not None)
