"""B-LAND-11-R2 Step 1 — the publish firewall wired into the real emitters.

Proves the gate is actually invoked on the public emission paths CH-R72 named:
  P1  live public bundle writer  (publish_public_bundle.build)
  P4  content-addressed CF bundle (public_generation.build_generation)

X-STRICT contract (owner ruling 20260813T232611Z, B-NIGHTFIX-1-R2): the P1 public
bundle EXCLUDES internal_only series (licensed families are dropped from the public
feed, exactly as the P2 HTTP API filters them) while still publishing the public
set; ``assert_series_publishable`` is retained as a tripwire that must still raise
if a licensed series ever reaches it unfiltered. P4 continues to RAISE on any
internal_only member. A public-only emission still succeeds (no regression), and
reclassifying an excluded source back to public restores its publication.
"""

from pathlib import Path

import pytest

import json

import live_data.publish_public_bundle as ppb
from live_data.rmv2_live import publish_gate as pg
from live_data.rmv2_live.server import LiveDataApiHandler, LoopbackHttpServer
from tools.rmv2_data_cloudflare.rmv2_extension import public_generation as pgn


def _production_layout(root, licensed_publish_class="internal_only"):
    """A minimal <root>/data_vault + <root>/live_data tree with one licensed and
    one public family, wired to a source each — the real registry layout."""
    cat = root / "data_vault" / "catalog"
    cat.mkdir(parents=True)
    (cat / "external_source_registry.csv").write_text(
        "source_id,access_class,publish_class\n"
        "lic_fam,C,%s\n"
        "pub_fam,A,public\n" % licensed_publish_class,
        encoding="utf-8",
    )
    cfg = root / "live_data" / "config"
    cfg.mkdir(parents=True)
    (cfg / "sources.v1.json").write_text(json.dumps({"sources": [
        {"source_id": "lic_src", "coverage_source_ids": ["lic_fam"]},
        {"source_id": "pub_src", "coverage_source_ids": ["pub_fam"]},
    ]}), encoding="utf-8")
    public_root = root / "live_data" / "public"
    public_root.mkdir(parents=True)
    return public_root


def _latest(source_id, value, label, period):
    return {"latest": {
        "source_id": source_id, "value": value, "unit": "index",
        "label": label, "observation_period": period,
        "available_at": "2026-08-06", "value_status": "final",
        "information_set_mode": "current_revised",
        "forecast_horizon": None, "forecast_origin": None,
    }}


def _synthetic_generation(source_id, extra_series=None):
    """One SP500 series from ``source_id``; ``extra_series`` merges more rows
    keyed by series_id -> source_id, so a mixed public/internal_only bundle can
    be built to observe the X-STRICT exclusion filter (B-NIGHTFIX-1)."""
    series = {"SP500": _latest(source_id, "4321.0", "S&P 500", "2026-08-05")}
    for sid, src in (extra_series or {}).items():
        series[sid] = _latest(src, "1.0", sid, "2026-08-05")
    return {
        "members": {
            "status.json": {"generated_at": "2026-08-06T00:00:00Z",
                            "current_source_health_counts": {}},
            "coverage.json": {},
            "snapshot.json": {"series": series, "sources": []},
        },
        "pointer": {"generation_sha256": "deadbeef", "schema_version": "x"},
        "manifest": {"schema_version": "x"},
    }


def _mixed_generation(public_source, licensed_source):
    """Two-series generation: one public (PUB1), one licensed (LIC1)."""
    def _item(source_id, value):
        return {"latest": {
            "source_id": source_id, "value": value, "unit": "index",
            "label": source_id, "observation_period": "2026-08-05",
            "available_at": "2026-08-06", "value_status": "final",
            "information_set_mode": "current_revised",
            "forecast_horizon": None, "forecast_origin": None,
        }}
    gen = _synthetic_generation(public_source)
    gen["members"]["snapshot.json"]["series"] = {
        "PUB1": _item(public_source, "100.0"),
        "LIC1": _item(licensed_source, "200.0"),
    }
    return gen


class TestP1PublicBundleWiring:
    def test_build_excludes_internal_only_series(self, tmp_path, monkeypatch):
        # X-STRICT (owner ruling 20260813T232611Z): internal_only series are
        # EXCLUDED from the public bundle, not refused. The public series still
        # ships; the licensed one is dropped; the tripwire never fires.
        monkeypatch.setattr(
            ppb, "read_verified_generation",
            lambda *a, **k: _mixed_generation("pub_live", "vix_live"),
        )
        monkeypatch.setattr(
            ppb, "load_source_publish_class_map",
            lambda *a, **k: {"pub_live": "public", "vix_live": "internal_only"},
        )
        out_root = tmp_path / "out"
        ppb.build(tmp_path, out_root=out_root)
        latest = out_root / "data" / "live" / "series_latest.json"
        assert latest.exists()                 # public bundle still written
        body = latest.read_bytes()
        assert b"PUB1" in body                 # public series published
        assert b"LIC1" not in body             # internal_only series excluded
        assert b"vix_live" not in body

    def test_build_publishes_public_only(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ppb, "read_verified_generation",
            lambda *a, **k: _synthetic_generation("gdp_live"),
        )
        monkeypatch.setattr(
            ppb, "load_source_publish_class_map",
            lambda *a, **k: {"gdp_live": "public"},
        )
        out_root = tmp_path / "out"
        ppb.build(tmp_path, out_root=out_root)
        latest = out_root / "data" / "live" / "series_latest.json"
        assert latest.exists()
        assert b"SP500" in latest.read_bytes()

    def test_reclassifying_to_public_restores_publication(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            ppb, "read_verified_generation",
            lambda *a, **k: _synthetic_generation("sp_live"),
        )
        out_root = tmp_path / "out"
        latest = out_root / "data" / "live" / "series_latest.json"
        # internal_only: SP500 EXCLUDED from public bundle, but bundle still
        # writes (X-STRICT exclusion, not fail-closed refusal).
        monkeypatch.setattr(ppb, "load_source_publish_class_map",
                            lambda *a, **k: {"sp_live": "internal_only"})
        ppb.build(tmp_path, out_root=out_root)
        assert latest.exists()
        assert b"SP500" not in latest.read_bytes()
        # reclassify to public: SP500 restored to the public feed.
        monkeypatch.setattr(ppb, "load_source_publish_class_map",
                            lambda *a, **k: {"sp_live": "public"})
        ppb.build(tmp_path, out_root=out_root)
        assert b"SP500" in latest.read_bytes()

    def test_tripwire_still_raises_on_unfiltered_internal_only(self):
        # The publish-set filter drops internal_only series, but the retained
        # assert_series_publishable tripwire MUST still raise if a licensed
        # series ever reaches it unfiltered — the gate is not weakened
        # (B-NIGHTFIX-1-R2: fix the publish SET, never the gate).
        with pytest.raises(pg.PublishGateError):
            pg.assert_series_publishable(
                [{"series_id": "X", "source_id": "lic_src"}],
                {"lic_src": "internal_only"},
            )


class TestP4CloudflareBundleWiring:
    def _entry(self, source_file, **over):
        base = {
            "public_path": "members/x.json",
            "source": source_file.name,
            "public_eligible": True,
            "rights_status": "cleared_for_publication",
            "source_name": "x",
            "attribution": "Test",
        }
        base.update(over)
        return base

    def test_build_generation_refuses_internal_only(self, tmp_path):
        source_root = tmp_path / "src"
        source_root.mkdir()
        f = source_root / "x.json"
        f.write_text("{}")
        out_root = tmp_path / "out"
        entry = self._entry(f, publish_class="internal_only")
        with pytest.raises(ValueError, match="internal_only"):
            pgn.build_generation(source_root, out_root, [entry])
        assert not (out_root / "generations").exists()

    def test_build_generation_allows_public(self, tmp_path):
        source_root = tmp_path / "src"
        source_root.mkdir()
        f = source_root / "x.json"
        f.write_text("{}")
        out_root = tmp_path / "out"
        entry = self._entry(f, publish_class="public")
        result = pgn.build_generation(source_root, out_root, [entry])
        assert result is not None


class TestProjectRootDiscovery:
    def test_discovers_deploy_layout_from_public_root(self, tmp_path):
        public_root = _production_layout(tmp_path)
        assert pg.discover_project_root(public_root) == tmp_path.resolve()

    def test_returns_none_when_no_registry(self, tmp_path):
        (tmp_path / "public").mkdir()
        assert pg.discover_project_root(tmp_path / "public") is None

    def test_loader_noops_without_registry(self, tmp_path):
        assert pg.load_source_publish_class_map(tmp_path) == {}

    def test_loader_builds_map_from_real_layout(self, tmp_path):
        _production_layout(tmp_path)
        m = pg.load_source_publish_class_map(tmp_path)
        assert m["lic_src"] == "internal_only"
        assert m["pub_src"] == "public"


class TestP2ServerRightsMap:
    def test_server_map_flags_licensed_and_filters_snapshot(self, tmp_path):
        public_root = _production_layout(tmp_path)
        generations = tmp_path / "live_data" / "store" / "generations"
        server = LoopbackHttpServer(
            ("127.0.0.1", 0), LiveDataApiHandler, public_root, generations,
            bind_and_activate=False,
        )
        try:
            m = server.publish_class_map()
            assert m["lic_src"] == "internal_only"
            assert m["pub_src"] == "public"
            snapshot = {"series": {
                "L": {"source_id": "lic_src", "observations": [1]},
                "P": {"source_id": "pub_src", "observations": [2]},
            }}
            filtered = pg.filter_snapshot_series(snapshot, m)
            assert set(filtered["series"]) == {"P"}
        finally:
            server.server_close()

    def test_server_map_noops_on_synthetic_tree(self, tmp_path):
        public_root = tmp_path / "public"
        public_root.mkdir()
        server = LoopbackHttpServer(
            ("127.0.0.1", 0), LiveDataApiHandler, public_root,
            tmp_path / "gens", bind_and_activate=False,
        )
        try:
            assert server.publish_class_map() == {}
        finally:
            server.server_close()
