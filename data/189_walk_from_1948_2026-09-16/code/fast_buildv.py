# fast_buildv.py -- memoisation of build_v's sub-objects (16 September 2026).
#
# Profile of summary() (profile_summary.py, walk 90 preamble): about 4 s per configuration, of which
# vgap2_asof(vk,vb) 35%, mkpair_either_asof(hline) 22%, confirm_wx 18%, mkpair_sv_asof 10%, the vacancy
# publication table 6%, hubv 4%; the chronology itself is under 5%. vk and vb are not even on the grid,
# so the vacancy object was rebuilt identically for every configuration the walk ever scored.
#
# Every sub-object is a pure function of its own parameters and of module data; each is now computed once
# per distinct parameter tuple and reused. The chronology is memoised on the exact content of the legs it
# is given and on the closer parameters. Nothing about any value changes: verify_fast_buildv.py compares the
# patched summary() with the cached summaries of walk 81 and must find zero differences.
#
# Usage, in a walk script after `_hdr` is assembled and walk 81's `_old -> _new` replacement is applied:
#     exec(open('s2/fast_buildv.py').read()); _hdr = patch_hdr(_hdr)
import re as _re

_MEMO = {}
def _M(key, thunk):
    v = _MEMO.get(key)
    if v is None:
        v = thunk(); _MEMO[key] = v
    return v

def _legs_key(legs, tlkey):
    return ('chron', tuple((k, tuple(tuple(x) for x in v)) for k, v in sorted(legs.items())), tlkey)

def _copy_turns(t):
    return [dict(x) for x in t]

def patch_hdr(h):
    reps = [
        ("    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})",
         "    G,pubs=_M(('vg',p['vk'],p['vb']),lambda:(lambda G_:(G_,pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G_.index})))(vgap2_asof(p['vk'],p['vb'])))"),
        ("    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])",
         "    F45=_M(('f45',p['u45']),lambda:[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45']))"),
        ("    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])",
         "    F25=_M(('f25',p['low']),lambda:[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low']))"),
        ("    Hc=mkpair_either_asof(p['hline']); Hh=HOURS_ASOF",
         "    Hc=_M(('hc',p['hline']),lambda:mkpair_either_asof(p['hline'])); Hh=HOURS_ASOF"),
        ("    SV=mkpair_sv_asof(G,pubs,p['vl'])",
         "    SV=_M(('sv',p['vk'],p['vb'],p['vl']),lambda:mkpair_sv_asof(G,pubs,p['vl']))"),
        ("        legs={'U':[(a,b) for a,b,c in confirm_wx(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1,'month')],",
         "        _kb=(p['vk'],p['vb'],p['vl'],p['spr'],p['hline'])\n        legs={'U':_M(('U',p['u45'],p['look'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1,'month')]),"),
        ("              'L':[(a,b) for a,b,c in confirm_wx(leg_gapL_x(spl,p['low'],52,rearm='window')+F25,C2,'month')],",
         "              'L':_M(('L',p['low'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_gapL_x(spl,p['low'],52,rearm='window')+F25,C2,'month')]),"),
        ("              'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_wx(leg_ic_cx(ICfp,p['ic']),C1,'month')]}",
         "              'X':_M(('X',p['sahm'],p['hback'])+_kb,lambda:[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])]),'I':_M(('I',p['ic'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_ic_cx(ICfp,p['ic']),C1,'month')])}"),
        ("        if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline'],rearm='zero'),C2,'month')]",
         "        if p.get('wline'): legs['W']=_M(('W',p['wline'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline'],rearm='zero'),C2,'month')])"),
        ("        if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline2'],rearm='window'),C2,'month')]",
         "        if p.get('wline2'): legs['V']=_M(('V',p['wline2'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline2'],rearm='window'),C2,'month')])"),
        ("        if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_wx(leg_br_x(p['bshare']),C2,'month')]",
         "        if p.get('bshare'): legs['B']=_M(('B',p['bshare'])+_kb,lambda:[(a,b) for a,b,c in confirm_wx(leg_br_x(p['bshare']),C2,'month')])"),
        ("        if p.get('kc'): legs['K']=[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]",
         "        if p.get('kc'): legs['K']=_M(('K',p['kc']),lambda:[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])])"),
        ("    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)",
         "    _tlk=(p['rst'],p['tst'],p['qst'],p.get('cD'),p['cn'],p['cs'])\n    turns=_copy_turns(_M(_legs_key(legs,_tlk),lambda:_chron_quiet(legs,TL)))"),
        ("        with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)",
         "        turns=_copy_turns(_M(_legs_key(legs,_tlk),lambda:_chron_quiet(legs,TL)))"),
    ]
    for a, b in reps:
        n = h.count(a)
        assert n == 1, 'fast_buildv: expected exactly one occurrence, found %d of: %s' % (n, a[:70])
        h = h.replace(a, b)
    h = h.replace("def build_v(p):", "def _chron_quiet(legs,TL):\n    with contextlib.redirect_stdout(io.StringIO()): return B.american_chronology(legs,TL)\ndef build_v(p):", 1)
    return h
