"""THE WARN NOTICES. Every state that must be given sixty days' notice before a mass layoff publishes the notices
it receives. The notice is filed BEFORE the job ends, by statute, so this is the only labour datum in the country
that leads the event by law rather than by correlation. biglocalnews' scrapers read each state's own page."""
import sys, os, traceback, warn
from warn.cache import Cache
from pathlib import Path
OUT = Path('/home/claude/warn/out')
OUT.mkdir(parents=True, exist_ok=True)
states = sys.argv[1].split(',')
import importlib
for st in states:
    try:
        m = importlib.import_module(f'warn.scrapers.{st}')
        p = m.scrape(data_dir=OUT, cache_dir=Path('/home/claude/warn/cache'))
        n = sum(1 for _ in open(p)) - 1
        print(f'{st.upper()}: OK {n} rows -> {p}', flush=True)
    except Exception as e:
        print(f'{st.upper()}: FAILED {type(e).__name__}: {str(e)[:120]}', flush=True)
