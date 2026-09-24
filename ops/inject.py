#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Puts ops/site/next_published.js into the published site and links it from the data page and the front page
(ops/; 22 September 2026, collection 306). Idempotent; changes nothing else on the pages; never fails the run.
    python3 ops/inject.py        (from the repository root, after the tool has built its pages)"""
import json, os, shutil, sys
OPS = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(OPS)
TAG = '<script src="/ops/next_published.js" defer></script>'


def main():
    tool = json.load(open(os.path.join(OPS, 'tool.json')))
    pub = os.path.join(ROOT, tool['site_public'])
    os.makedirs(os.path.join(pub, 'ops'), exist_ok=True)
    shutil.copyfile(os.path.join(OPS, 'site', 'next_published.js'), os.path.join(pub, 'ops', 'next_published.js'))
    done = []
    for key in ('data_page', 'home_page'):
        p = os.path.join(ROOT, tool.get(key, ''))
        if not tool.get(key) or not os.path.isfile(p):
            continue
        t = open(p, encoding='utf-8').read()
        if TAG in t:
            done.append(key + ' (already)'); continue
        i = t.rfind('</body>')
        if i < 0:
            continue
        t = t[:i] + TAG + '\n' + t[i:]
        tmp = p + '.tmp'
        open(tmp, 'w', encoding='utf-8').write(t); os.replace(tmp, p)
        done.append(key)
    print('ops inject: next_published.js linked from %s' % (', '.join(done) or 'no page'))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('ops inject: FAILED (%s: %s); the pages stand as built' % (type(e).__name__, e))
    sys.exit(0)
