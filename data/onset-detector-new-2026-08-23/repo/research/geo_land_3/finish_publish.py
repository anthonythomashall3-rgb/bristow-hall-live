"""B-GEO-LAND-3: finish the interrupted commit-staged publish.

commit-staged admitted the four bea_cainc1 heads AND extended config to 538,
but the publish (build_snapshot/status/coverage + publish_generation, O(store))
was killed by a 2-minute wall before it finished. Measured divergence:
config 538, store heads 538 (all four bea_cainc1 present), published generation
binding 534 (pre-landing), runtime_binding != generation_binding.

This drives the pipeline's OWN publish over current heads -- exactly the tail
run_commit runs -- to publish ONE generation over all 538 heads and rewrite the
pointer + operational_status. No refetch, no data change, no code/test edit
(section 18.1 clean): the heads are genuine committed output; only the
generation pointer had not caught up. Same interrupted-publish class as
geo_land_1 / geo_land_2 / STATE-CLAIMS.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/Users/anthonyhall/Projects/bristow-hall/repo")
sys.path.insert(0, str(REPO))

from bh import produce as bhp, writer_lock


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pipeline, cfg = bhp.load_pipeline(REPO)
    with writer_lock.writer_lock("B-GEO-LAND-3 finish publish", REPO):
        heads = pipeline.store.all_source_heads()
        rt = pipeline._runtime_head_binding_map(heads)
        pipeline._validate_generation_recovery_heads(heads)
        pointer = bhp._publish_current_heads(pipeline, stamp)
        print("published generation over %d heads" % len(heads))
        print("pointer generation_sha256:",
              pointer.get("generation_sha256") if isinstance(pointer, dict)
              else pointer)


if __name__ == "__main__":
    main()
