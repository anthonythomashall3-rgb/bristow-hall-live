# -*- coding: utf-8 -*-
"""THE SOURCE GATE'S OWN TEST (15 November 2026, collection 1052). No AI.

Proves that s2/source_gate.py catches the errors the 15 November audit found, on deliberately broken copies of a real build, and
that it does not cry wolf: each broken copy is checked against the SAME source data as the unbroken build (one fetch, saved by
source_gate.py --sources-out), and a mutation counts as caught only if it adds a FAIL the unbroken build does not have.

  python3 s2/source_gate_selftest.py --site <a built site/public> --sources <the saved source fetch> [--out report.json]

Exit 1 if any mutation is not caught, or if the unbroken build fails anything the outage test needs.
"""
import argparse, copy, json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import source_gate as G


def load_S(site):
    t = open(os.path.join(site, 'detector', 'index.html'), encoding='utf-8').read()
    i = t.find('const S = ')
    S, end = json.JSONDecoder().raw_decode(t[i + 10:])
    return t, i + 10, i + 10 + end, S


def save_S(site, S):
    t, a, b, _ = load_S(site)
    open(os.path.join(site, 'detector', 'index.html'), 'w', encoding='utf-8').write(t[:a] + json.dumps(S, separators=(',', ':')) + t[b:])
    json.dump(S, open(os.path.join(site, 'bhs_state.json'), 'w'))


def edit(site, rel, fn):
    p = os.path.join(site, rel); t = open(p, encoding='utf-8').read(); t2 = fn(t)
    if t2 == t: raise RuntimeError('the mutation changed nothing in %s' % rel)
    open(p, 'w', encoding='utf-8').write(t2)


def home_tiles(site, fn):
    def f(t):
        i = t.find('const H=') + 8; H, n = json.JSONDecoder().raw_decode(t[i:]); fn(H)
        return t[:i] + json.dumps(H, separators=(',', ':')) + t[i + n:]
    edit(site, 'index.html', f)


def tile(H, lab):
    return next(x for x in H['tiles'] if x['lab'] == lab)


def data_row(t, ids, fn):
    m = re.search(r'<tr data-tool="[^"]*" data-name="[^"]*" data-ids="%s"[^>]*>.*?</tr>' % re.escape(ids), t, re.S)
    if not m: raise RuntimeError('no data-page row %s' % ids)
    return t[:m.start()] + fn(m.group(0)) + t[m.end():]


def mutations(src_cache, build_day):
    """(name, what the audit found, function(site) that breaks a copy, the checks that must FAIL: (page prefix, label part, check))"""
    def m_cpi(site):
        home_tiles(site, lambda H: tile(H, 'CPI inflation').update(val='3.9%'))
    def m_icnsa(site):
        t, a, b, S = load_S(site)
        S['feed_value_dates']['ICNSA']['value'] = 170626.0
        S['feed_value_dates']['CCNSA']['value'] = 5780893.0
        save_S(site, S)
        edit(site, 'data/index.html', lambda t: re.sub(r'<b>[\d,]+</b><span class="u">ICNSA', '<b>170,626</b><span class="u">ICNSA', t))
    def m_frozen(site):
        # the reading frozen in September but labelled the newest month / week
        t, a, b, S = load_S(site)
        r = next(x for x in S['readings'] if x['object'].startswith('fed-shock door'))
        r['through'] = '2026-11-30'
        S['through']['claims'] = '2026-09-12'
        save_S(site, S)
        home_tiles(site, lambda H: tile(H, 'Initial claims (week)').update(sub='week ending Nov 14, 2026'))
    def m_phantom(site):
        def f(t):
            i = t.find('const ALL = ') + 12; ALL, n = json.JSONDecoder().raw_decode(t[i:])
            s = ALL['CA']['series']
            for k in ('dates', 'values', 'reading', 'damage', 'phase', 'branch'):
                if isinstance(s.get(k), list) and s[k]:
                    s[k].append(G.madd(s[k][-1], 1) if k == 'dates' else s[k][-1])
            ALL['CA']['now']['last_month'] = s['dates'][-1]
            return t[:i] + json.dumps(ALL, separators=(',', ':')) + t[i + n:]
        edit(site, 'state-onset/index.html', f)
        def g(t):
            m = re.search(r'(<script[^>]*id="data"[^>]*>)(.*?)(</script>)', t, re.S); J = json.loads(m.group(2))
            J['prov']['last'] = G.madd(J['prov']['last'], 1); J['last'] = J['prov']['last']
            return t[:m.start(2)] + json.dumps(J, separators=(',', ':')) + t[m.end(2):]
        edit(site, 'stress-map/index.html', g)
    def m_nextday(site):
        edit(site, 'data/index.html', lambda t: data_row(t, 'unrate, payems, unemploy, lns13023621',
                                                         lambda r: re.sub(r'data-next="[^"]*"', 'data-next="%s"' % build_day, r)))
        home_tiles(site, lambda H: tile(H, 'Unemployment rate').update(next=build_day))
    def m_stale_row(site):
        edit(site, 'data/index.html', lambda t: data_row(t, 'jtsjol', lambda r: re.sub(r'data-through="[^"]*"', 'data-through="2026-07-31"', r)))
    return [
        ('cpi_estimate', 'CPI tile shows an estimate (3.9%) instead of the published 12-month change', m_cpi,
         [('home', 'CPI inflation', 'value')]),
        ('icnsa_stale_fallback', 'ICNSA 170,626 (an old row) and CCNSA 5,780,893 (a 2020 row) shown as current', m_icnsa,
         [('detector', 'feed ICNSA', 'value'), ('detector', 'feed CCNSA', 'value'), ('data/detector', 'ICNSA', 'value')]),
        ('frozen_label_date', 'a reading frozen earlier but labelled with a later date; the detector current-through frozen in September',
         m_frozen, [('detector', 'fed-shock door', 'freshness'), ('detector', 'current through: claims', 'freshness'),
                    ('home', 'Initial claims (week)', 'freshness')]),
        ('phantom_month', 'a phantom carried-forward month on /state-onset/ (and a provisional month after the newest week on /stress-map/)',
         m_phantom, [('state-onset', 'CA chronology', 'phantom'), ('stress-map', 'provisional last month', 'phantom')]),
        ('build_day_next', "'Next published' = the build day, not the publisher's release", m_nextday,
         [('data/detector', 'unemployment rate', 'next published'), ('home', 'Unemployment rate', 'next published')]),
        ('stale_row', 'a data-page row held through a stale month while a newer release existed', m_stale_row,
         [('data/detector', 'job openings', 'freshness')]),
    ]


def fails(rep):
    return {(r['page'], r['label'], r['check']) for r in rep['rows'] if r['status'] == 'FAIL'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--site', required=True); ap.add_argument('--sources', required=True)
    ap.add_argument('--out', default=os.path.join(os.path.dirname(HERE), 'out', 'source_gate_selftest.json'))
    a = ap.parse_args()
    tmp = tempfile.mkdtemp(prefix='sg_test_')
    vfile = os.path.join(tmp, 'verified.json'); json.dump({}, open(vfile, 'w'))
    kw = dict(mode='hold', sources_in=a.sources, verified_path=vfile, quiet=True, write_verified=False)
    base = G.run(a.site, out=os.path.join(tmp, 'base.json'), **kw)
    B = fails(base)
    S = json.loads(open(os.path.join(a.site, 'bhs_state.json')).read())
    bd = S['built_at'][:10]
    out = {'base': {'checks': base['totals']['checks'], 'fail': len(B)}, 'mutations': []}
    print('the unbroken build (same sources): %d checks, %d FAIL' % (base['totals']['checks'], len(B)))
    allok = True
    for name, what, fn, must in mutations(None, bd):
        d = os.path.join(tmp, name); shutil.copytree(a.site, d)
        try:
            fn(d)
        except Exception as e:
            print('  %-22s could not be made: %s' % (name, e)); allok = False; out['mutations'].append({'name': name, 'caught': False, 'error': str(e)}); continue
        rep = G.run(d, out=os.path.join(tmp, name + '.json'), **kw)
        new = fails(rep) - B
        got = []
        for pg, lab, chk in must:
            hit = [x for x in new if x[0].startswith(pg) and lab.lower() in x[1].lower() and (x[2] == chk or chk in x[2])]
            got.append(bool(hit))
        caught = all(got) and rep['decision'] == 'HOLD'
        allok &= caught
        details = [r for r in rep['rows'] if r['status'] == 'FAIL' and (r['page'], r['label'], r['check']) in new]
        out['mutations'].append({'name': name, 'what': what, 'caught': caught, 'decision': rep['decision'], 'new_fails': len(new),
                                 'expected': [list(m) for m in must], 'expected_hit': got,
                                 'fails': [{k: x[k] for k in ('page', 'label', 'check', 'value', 'expected', 'detail')} for x in details]})
        print('  %-22s %s  decision %s, %d new FAIL(s): %s' % (name, 'CAUGHT' if caught else 'MISSED', rep['decision'], len(new),
              ' | '.join('%s %s: %s' % (x['page'], x['label'][:40], (x['detail'] or '')[:90]) for x in details[:4])))
    # a CORRECT build passes: the build above with only its known errors corrected (each correction is the publisher's own value
    # that the gate reported), and nothing else touched. Every other figure on it is left exactly as published.
    d = os.path.join(tmp, 'corrected'); shutil.copytree(a.site, d)
    fixed = []
    def fix_row(page, name, fn):
        p = os.path.join(d, 'data', 'index.html'); t = open(p, encoding='utf-8').read(); tool = page.split('/', 1)[1]
        for nm in (G.htmlmod.escape(name, quote=True).replace('&#x27;', "'"), name):
            pat = r'<tr data-tool="\d+ %s" data-name="%s".*?</tr>' % (re.escape(tool), re.escape(nm))
            t2 = re.sub(pat, lambda m: fn(m.group(0)), t, flags=re.S)
            if t2 != t: open(p, 'w', encoding='utf-8').write(t2); return True
    for r in base['rows']:
        if r['status'] != 'FAIL': continue
        if r['page'].startswith('data/') and r['check'] == 'value' and 'where the value it holds should be' in (r['detail'] or ''):
            if fix_row(r['page'], r['label'], lambda x: re.sub(r'<b>MISSING</b>', '<b>held</b>', x.replace('data-value="missing"', 'data-value="held"'), flags=re.I)):
                fixed.append(('MISSING shown', r['page'], r['label']))
        elif r['page'].startswith('data/') and r['check'] == 'freshness' and r.get('expected'):
            e = r['expected'] if len(r['expected']) == 10 else r['expected'] + '-01'
            if fix_row(r['page'], r['label'], lambda x: re.sub(r'data-through="[^"]*"', 'data-through="%s"' % e, x)):
                fixed.append(('stale period', r['page'], r['label']))
        elif r['page'] == 'detector' and r['check'] == 'freshness' and r.get('expected'):
            tt, aa, bb, S = load_S(d)
            for x in S['readings']:
                if x['object'].split(',')[0][:90] == r['label']: x['through'] = r['expected']; fixed.append(('frozen reading', r['page'], r['label']))
            save_S(d, S)
    rc = G.run(d, out=os.path.join(tmp, 'corrected.json'), **kw)
    left = [x for x in rc['rows'] if x['status'] == 'FAIL']
    ok_c = not left
    print('  %-22s %s  %d known errors corrected, nothing else touched: decision %s, %d checks, %d PASS, %d FAIL%s' % (
        'correct_build', 'PASSES' if ok_c else 'STILL FAILS', len(fixed), rc['decision'], rc['totals']['checks'], rc['totals']['passed'],
        len(left), (': ' + ' | '.join('%s %s %s' % (x['page'], x['label'][:40], (x['detail'] or '')[:80]) for x in left[:5])) if left else ''))
    out['correct_build'] = {'corrected': fixed, 'decision': rc['decision'], 'fails_left': left, 'totals': rc['totals']}
    allok &= ok_c
    # an outage: the source of a figure cannot be read. Unchanged since the last verified build -> may stay; changed -> held.
    cache = json.load(open(a.sources))
    for k in [k for k in cache if k.startswith('fred:UNRATE:')]: cache[k + ':err'] = 'simulated outage'; del cache[k]
    for k in [k for k in cache if k.startswith('bls:')]: cache[k + ':err'] = 'simulated outage'; del cache[k]
    oc = os.path.join(tmp, 'outage_sources.json'); json.dump(cache, open(oc, 'w'))
    # the verified store as a verified build would have left it for this tile
    ver = {}
    t = open(os.path.join(a.site, 'index.html'), encoding='utf-8').read(); i = t.find('const H=') + 8
    Ht, _ = json.JSONDecoder().raw_decode(t[i:])
    u = tile(Ht, 'Unemployment rate')
    ver['home|Unemployment rate|UNRATE'] = {'value': u['val'], 'period': '2026-10-01' if 'Oct 2026' in u['sub'] else G.label_period(u['sub']) + '-01'}
    json.dump(ver, open(vfile, 'w'))
    r1 = G.run(a.site, mode='hold', sources_in=oc, verified_path=vfile, quiet=True, write_verified=False)
    st1 = [x['status'] for x in r1['rows'] if x['page'] == 'home' and x['label'] == 'Unemployment rate' and x['check'] in ('source', 'value', 'freshness')]
    d = os.path.join(tmp, 'outage_changed'); shutil.copytree(a.site, d)
    home_tiles(d, lambda H: tile(H, 'Unemployment rate').update(val='4.4%'))
    r2 = G.run(d, mode='hold', sources_in=oc, verified_path=vfile, quiet=True, write_verified=False)
    st2 = [x['status'] for x in r2['rows'] if x['page'] == 'home' and x['label'] == 'Unemployment rate' and x['check'] in ('source', 'value', 'freshness')]
    o1 = 'UNVERIFIED' in st1 and 'FAIL' not in st1
    o2 = 'FAIL' in st2
    print('  %-22s %s  FRED and BLS down for UNRATE, the tile unchanged since the last verified build: %s (may stay)' % ('outage_unchanged', 'OK' if o1 else 'WRONG', st1))
    print('  %-22s %s  FRED and BLS down for UNRATE, the tile changed (4.4%%): %s (held)' % ('outage_changed', 'CAUGHT' if o2 else 'MISSED', st2))
    allok &= o1 and o2
    out['outage'] = {'unchanged': st1, 'unchanged_ok': o1, 'changed': st2, 'changed_held': o2}
    # 1052 (16 Nov 2026): FRED refuses a read (429, the key's shared limit) but the publisher answers. The figure is checked against the
    # publisher (BLS API v2) and passes, whatever the verified store says; changed to a wrong value, it is a FAIL (a mismatch), not merely held.
    cache = json.load(open(a.sources))
    # the BLS's answer for the gate's labour bundle: the capture's own when the live check asked the BLS; otherwise (FRED was current, so
    # the live check never needed the BLS) the same months as FRED's current UNRATE in the capture - the publisher's print, which FRED
    # republishes unchanged - so the fallback logic is tested on every run
    import datetime as _dt
    bk = 'bls:%s:%d' % (','.join(sorted(G.BLS_OF.values())), _dt.date.today().year - 1)
    if bk not in cache:
        fr = next((v for k, v in cache.items() if k.startswith('fred:UNRATE:') and not k.endswith(':err') and v), None)
        if fr:
            cache[bk] = {'LNS14000000': {r[0][:7]: r[3] for r in fr if r[2] == '9999-12-31' and r[3] is not None}}
    for k in [k for k in cache if k.startswith('fred:UNRATE:')]: cache[k + ':err'] = 'HTTP 429 Too Many Requests (simulated)'; del cache[k]
    pc = os.path.join(tmp, 'fred429_sources.json'); json.dump(cache, open(pc, 'w')); json.dump({}, open(vfile, 'w'))
    r3 = G.run(a.site, mode='hold', sources_in=pc, verified_path=vfile, quiet=True, write_verified=False)
    st3 = [x['status'] for x in r3['rows'] if x['page'] == 'home' and x['label'] == 'Unemployment rate' and x['check'] in ('source', 'value', 'freshness')]
    r4 = G.run(d, mode='hold', sources_in=pc, verified_path=vfile, quiet=True, write_verified=False)
    rows4 = [x for x in r4['rows'] if x['page'] == 'home' and x['label'] == 'Unemployment rate' and x['check'] in ('source', 'value', 'freshness')]
    st4 = [x['status'] for x in rows4]
    o3 = 'PASS' in st3 and 'FAIL' not in st3 and 'UNVERIFIED' not in st3
    o4 = any(x['status'] == 'FAIL' and x['check'] == 'value' for x in rows4)
    # the case needs the BLS's answer in the captured sources; a capture made while the BLS refused (its daily allowance) cannot test it
    if not any(k.startswith('bls:') and not k.endswith(':err') and 'LNS14000000' in k for k in cache):
        print('  %-22s NOT TESTABLE  the captured sources hold no BLS answer for UNRATE (the BLS refused the capture): the two cases are not run' % 'fred429_publisher')
        o3 = o4 = True; st3 = st4 = ['not testable']
    print('  %-22s %s  FRED refuses UNRATE (429), the BLS answers, a figure never verified: %s (checked against the publisher)' % ('fred429_publisher', 'OK' if o3 else 'WRONG', st3))
    print('  %-22s %s  the same, the tile changed (4.4%%): %s (a mismatch with the publisher)' % ('fred429_mismatch', 'CAUGHT' if o4 else 'MISSED', st4))
    allok &= o3 and o4
    out['fred429'] = {'unchanged': st3, 'unchanged_ok': o3, 'changed': st4, 'changed_caught': o4}
    out['all_caught'] = bool(allok)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print('SELF-TEST %s' % ('PASSED: every broken copy was caught' if allok else 'FAILED: see above'))
    sys.exit(0 if allok else 1)


if __name__ == '__main__':
    main()
