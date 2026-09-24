# walk37 = walk34 with the paper spread corrected after August 1997 (Rule Zero, 8 September 2026)
s=open('walk34.py').read()
def rep(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a)); s=s.replace(a,b)
rep('"""WALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30','"""WALK 37 - WALK 34 WITH THE PAPER SPREAD CORRECTED AFTER AUGUST 1997 (Rule Zero, collection 105, 8 September\n2026). The spread object was built as the prime commercial paper rate (FRED H0RIFSPPFM01NWF, weekly) less the\nthree-month bill (WTB3MS). That paper series ends on 29 August 1997 and the code carried its last value, 5.49,\nforward, so from September 1997 the "spread" was 5.49 less the bill rate - the bill rate falling, not paper widening\n(it read 5.5 in December 2008 and March 2020). Found on 8 September while building the live series. From 5 September\n1997 the paper leg is the one-month AA nonfinancial commercial paper rate (FRED DCPN30, daily, averaged to the\nFriday week) and the object is otherwise unchanged: 13-week mean of the spread above its 39-week minimum. Which\ncalls the old object confirmed, and what changes, is in the version note.\n\nWALK 34 - ONE CLOCK FOR THE CHRONOLOGY, THE MACHINERY OF WALK30')
CB='''
# ---- THE PAPER SPREAD, CORRECTED (see the docstring) ----
_cp1=pd.read_csv(os.path.join(C25,'fred_daily','DCPN30.csv')).iloc[:,:2]; _cp1.columns=['d','v']; _cp1['d']=pd.to_datetime(_cp1['d'],errors='coerce')
_cp1=pd.to_numeric(_cp1.set_index('d')['v'],errors='coerce').dropna(); _cp1w=_cp1.resample('W-FRI').mean().dropna()
_aa_old=aa[aa.index<=pd.Timestamp('1997-08-29')]; _aa_new=_cp1w[_cp1w.index>pd.Timestamp('1997-08-29')]
aa=pd.concat([_aa_old,_aa_new]).sort_index(); idx=aa.index.union(bb.index)
CPB=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); CPB=CPB[CPB.index>=max(aa.index.min(),bb.index.min())]
Sm=CPB.rolling(13).mean().dropna(); GSP=(Sm-Sm.rolling(39).min()).dropna()
'''
rep("def build_v(p):\n","%sdef build_v(p):\n"%CB)
rep("out=open('walk34_%s.out'%sys.argv[1],'w')","out=open('walk37_%s.out'%sys.argv[1],'w')")
open('walk37.py','w').write(s); print('walk37 written')
