"""Complete the interrupted commit: publish ONE generation over current heads.

commit-staged already bound all 51 state heads and persisted config (482
sources); the publish_generation half was killed by a 120s wrapper timeout.
run_commit will not republish (no live drafts remain), so run the exact publish
half it runs, under the writer lock.
"""
import sys
from pathlib import Path

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

from datetime import datetime, timezone
from bh import produce as bhp, writer_lock


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pipeline, config = bhp.load_pipeline(REPO)
    print("config sources:", len(config["sources"]))
    with writer_lock.writer_lock("finish publish state-claims", REPO):
        pointer = bhp._publish_current_heads(pipeline, stamp)
    print("published generation:", pointer["generation_sha256"] if pointer else None)


if __name__ == "__main__":
    main()
