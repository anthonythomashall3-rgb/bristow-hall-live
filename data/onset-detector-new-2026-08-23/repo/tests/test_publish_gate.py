"""B-LAND-11-R2 Step 1 — publish-side rights firewall.

Authority: `_mailbox/answers/20260806T131145Z_B-LAND-11_FINCONDITIONS_INPUTS.md`
and `OWNER_RULING_20260806_RIGHTS_ALL_CHANNELS.md`. This batch lands licensed
Tier-2 financial-conditions inputs as `publish_class: internal_only` (strictest
class) and MUST build the fail-closed publish firewall FIRST.

`_validate_family_bindings` (feed_factory.py) gates whether bytes may ENTER the
store (admission). This module is the mirror at the EMIT boundary: the site
publisher and every public-artifact generator REFUSES to publish any series whose
family carries `publish_class: internal_only`. Internal scientific USE stays
unrestricted — only publication is refused.

Fail-closed default (CH-R72): an UNSET `publish_class` on a LICENSED family
(access_class C/D) resolves to `internal_only` — absence of the flag is never
treated as permission for licensed data. Non-licensed families default to
`public`, so nothing already landed changes behaviour.
"""

import pytest

from live_data.rmv2_live import publish_gate as pg


class TestResolvePublishClass:
    def test_explicit_public_is_public(self):
        assert pg.resolve_publish_class({"publish_class": "public", "access_class": "A"}) == "public"

    def test_explicit_internal_only_is_internal_only(self):
        assert pg.resolve_publish_class(
            {"publish_class": "internal_only", "access_class": "C"}
        ) == "internal_only"

    def test_unset_on_licensed_C_fails_closed_to_internal_only(self):
        assert pg.resolve_publish_class({"publish_class": "", "access_class": "C"}) == "internal_only"

    def test_unset_on_licensed_D_fails_closed_to_internal_only(self):
        assert pg.resolve_publish_class({"access_class": "D"}) == "internal_only"

    def test_unset_on_public_B_is_public(self):
        assert pg.resolve_publish_class({"access_class": "B"}) == "public"

    def test_unset_on_public_A_is_public(self):
        assert pg.resolve_publish_class({"access_class": "A"}) == "public"

    def test_whitespace_flag_is_stripped(self):
        assert pg.resolve_publish_class(
            {"publish_class": "  internal_only  ", "access_class": "C"}
        ) == "internal_only"


class TestSourceClassMap:
    def _registry(self):
        return {
            "cboe_vix": {"source_id": "cboe_vix", "access_class": "C", "publish_class": "internal_only"},
            "moody_corporate_yields": {"source_id": "moody_corporate_yields", "access_class": "B", "publish_class": "public"},
            "us_treasury": {"source_id": "us_treasury", "access_class": "A", "publish_class": ""},
            "licensed_unflagged": {"source_id": "licensed_unflagged", "access_class": "C", "publish_class": ""},
        }

    def test_licensed_source_maps_internal_only(self):
        sources = [{"source_id": "vix_live", "coverage_source_ids": ["cboe_vix"]}]
        m = pg.build_source_publish_class_map(sources, self._registry())
        assert m["vix_live"] == "internal_only"

    def test_public_source_maps_public(self):
        sources = [{"source_id": "tsy_live", "coverage_source_ids": ["us_treasury"]}]
        m = pg.build_source_publish_class_map(sources, self._registry())
        assert m["tsy_live"] == "public"

    def test_mixed_families_take_worst_class(self):
        sources = [{"source_id": "mix", "coverage_source_ids": ["us_treasury", "cboe_vix"]}]
        m = pg.build_source_publish_class_map(sources, self._registry())
        assert m["mix"] == "internal_only"

    def test_unflagged_licensed_family_fails_closed(self):
        sources = [{"source_id": "lic", "coverage_source_ids": ["licensed_unflagged"]}]
        m = pg.build_source_publish_class_map(sources, self._registry())
        assert m["lic"] == "internal_only"


class TestAssertSeriesPublishable:
    def test_raises_on_internal_only_series(self):
        series = [
            {"series_id": "SP500", "source_id": "sp_live"},
            {"series_id": "GDP", "source_id": "gdp_live"},
        ]
        source_map = {"sp_live": "internal_only", "gdp_live": "public"}
        with pytest.raises(pg.PublishGateError) as exc:
            pg.assert_series_publishable(series, source_map)
        assert "SP500" in str(exc.value)

    def test_passes_when_all_public(self):
        series = [{"series_id": "GDP", "source_id": "gdp_live"}]
        pg.assert_series_publishable(series, {"gdp_live": "public"})

    def test_unknown_source_id_is_not_licensed(self):
        # A series whose source is absent from the map is not a licensed family;
        # the fail-closed default is scoped to licensed families in the registry.
        series = [{"series_id": "X", "source_id": "orphan"}]
        pg.assert_series_publishable(series, {})

    def test_removing_the_flag_restores_publication(self):
        series = [{"series_id": "SP500", "source_id": "sp_live"}]
        # was internal_only -> raises
        with pytest.raises(pg.PublishGateError):
            pg.assert_series_publishable(series, {"sp_live": "internal_only"})
        # reclassified to public -> publishes
        pg.assert_series_publishable(series, {"sp_live": "public"})


class TestSnapshotFilter:
    def _snapshot(self):
        return {
            "series": {
                "GDP": {"source_id": "gdp_live", "series_id": "GDP", "observations": [1]},
                "VIX": {"source_id": "vix_live", "series_id": "VIX", "observations": [2]},
            },
            "sources": [],
        }

    def _map(self):
        return {"gdp_live": "public", "vix_live": "internal_only"}

    def test_series_item_publishable(self):
        assert pg.series_item_is_publishable(
            {"source_id": "gdp_live"}, self._map()) is True

    def test_series_item_internal_only_not_publishable(self):
        assert pg.series_item_is_publishable(
            {"source_id": "vix_live"}, self._map()) is False

    def test_unknown_source_item_publishable(self):
        assert pg.series_item_is_publishable({"source_id": "z"}, self._map()) is True

    def test_filter_drops_internal_only_keeps_public(self):
        out = pg.filter_snapshot_series(self._snapshot(), self._map())
        assert set(out["series"]) == {"GDP"}

    def test_filter_does_not_mutate_input(self):
        snap = self._snapshot()
        pg.filter_snapshot_series(snap, self._map())
        assert set(snap["series"]) == {"GDP", "VIX"}


class TestAggregatePublishable:
    def test_all_public_publishable(self):
        assert pg.aggregate_is_publishable(["public", "public"]) is True

    def test_single_licensed_member_not_publishable(self):
        assert pg.aggregate_is_publishable(["internal_only"]) is False

    def test_licensed_plus_one_public_still_recoverable(self):
        # one licensed + one public: licensed leg recoverable by subtraction
        assert pg.aggregate_is_publishable(["internal_only", "public"]) is False

    def test_licensed_plus_two_public_not_recoverable(self):
        assert pg.aggregate_is_publishable(["internal_only", "public", "public"]) is True


class TestPublishAllGoodData:
    """B-RIGHTS-1 — OWNER_RULING_20260808_PUBLISH_ALL_GOOD_DATA.md.

    The ruling adds an explicit publishable class `publish_all_good_data` and
    migrates the 7 class-C families to it. Publishability is `!= internal_only`;
    the class is fail-closed to the ruling-certified 7 (three-leg 'good data'
    determination made per-family by the ruling), so it cannot silently extend.
    """

    def test_constant_exists(self):
        assert pg.PUBLISH_ALL_GOOD_DATA == "publish_all_good_data"

    def test_explicit_good_data_resolves_unchanged(self):
        assert pg.resolve_publish_class(
            {"publish_class": "publish_all_good_data", "access_class": "C"}
        ) == "publish_all_good_data"

    def test_good_data_is_publishable(self):
        assert pg.is_publishable_class("publish_all_good_data") is True

    def test_internal_only_not_publishable(self):
        assert pg.is_publishable_class("internal_only") is False

    def test_good_data_series_item_publishable(self):
        item = {"series_id": "VIXCLS", "source_id": "vix_live"}
        assert pg.series_item_is_publishable(item, {"vix_live": "publish_all_good_data"}) is True

    def test_ruling_families_are_the_seven(self):
        assert pg.RULING_20260808_GOOD_DATA_FAMILIES == frozenset((
            "moody_corporate_yields", "ice_bofa_spreads", "sp_equity",
            "nasdaq_equity", "cboe_vix", "freddie_pmms", "michigan_consumers",
        ))

    def test_gate_rejects_unlisted_family_claiming_good_data(self):
        # fail-closed: a family NOT in the ruling set may not carry the class
        with pytest.raises(pg.PublishGateError):
            pg.assert_registry_publish_classes([
                {"source_id": "some_new_family", "access_class": "C",
                 "publish_class": "publish_all_good_data"},
            ])

    def test_gate_rejects_unknown_class(self):
        with pytest.raises(pg.PublishGateError):
            pg.assert_registry_publish_classes([
                {"source_id": "x", "access_class": "A", "publish_class": "totally_bogus"},
            ])

    def test_gate_rejects_blank_class(self):
        with pytest.raises(pg.PublishGateError):
            pg.assert_registry_publish_classes([
                {"source_id": "x", "access_class": "A", "publish_class": ""},
            ])

    def test_gate_accepts_the_seven(self):
        rows = [
            {"source_id": fam, "access_class": "C",
             "publish_class": "publish_all_good_data"}
            for fam in pg.RULING_20260808_GOOD_DATA_FAMILIES
        ]
        pg.assert_registry_publish_classes(rows)  # no raise
