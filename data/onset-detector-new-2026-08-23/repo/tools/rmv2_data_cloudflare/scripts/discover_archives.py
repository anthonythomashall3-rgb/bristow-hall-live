#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rmv2_extension.archive_scraper import archive_recipe_from_mapping, discover_archive  # noqa: E402

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('config',type=Path); parser.add_argument('output',type=Path); args=parser.parse_args()
    doc=json.loads(args.config.read_text(encoding='utf-8')); rows=doc if isinstance(doc,list) else doc.get('archives',[])
    results=[discover_archive(archive_recipe_from_mapping(row)) for row in rows if row.get('enabled',True)]
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps({'schema_version':'recession-monitor-v2.archive-discovery.v1','results':results},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'success':sum(r['status']=='SUCCESS' for r in results),'failed':sum(r['status']!='SUCCESS' for r in results)},indent=2))
    if any(r['status']!='SUCCESS' for r in results): raise SystemExit(1)
if __name__=='__main__': main()
