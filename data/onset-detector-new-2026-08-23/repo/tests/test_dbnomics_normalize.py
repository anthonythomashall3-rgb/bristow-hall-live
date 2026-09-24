"""B-ACQ-AGGREGATORS — TDD for the DBnomics aggregator normalize path.

DBnomics is an aggregator tier (lead institution CEPREMAP). Per the batch's binding
rules an aggregator lane may only fill where publisher-direct/FRED reach nothing, and
§3.1 requires the lineage back to the original publisher survive verbatim:
provider_code/dataset_code/series_code recorded per record.

Four proofs pin the NEW shape ``dbnomics_json`` -> ``parse_dbnomics_json``:
(a) one record per (period, value); value copied verbatim as a string; the
    provider/dataset/series triple is recorded for lineage (§3.1/§7.3).
(b) §5.6 cross-check — if the aggregator's own doc identity disagrees with the
    configured identity the lane REFUSES (SourceUnavailable), it does not silently
    relabel someone else's series.
(c) a DBnomics "NA"/null observation is absence, not a hole (dropped, not zero).
(d) value_status/information_set_mode/unit come from the source config, not guessed.
"""
import json

from live_data.rmv2_live import adapters


def _source():
    return {
        "adapter": "dbnomics_json",
        "endpoint": "https://api.db.nomics.world/v22/series/ISM/pmi/pm?observations=true",
        "information_set_mode": "current_revised",
        "method_version": "dbnomics_aggregator_offline.v1",
        "publisher": "Institute for Supply Management (ISM)",
        "publisher_release_clock": "monthly ISM release; DBnomics daily re-index",
        "rights_status": "aggregator_mirror_published_index",
        "source_id": "dbnomics_ism_manufacturing_pmi_current_offline",
        "value_status": "observed",
        "series": {
            "index_label": "ISM Manufacturing PMI headline (via DBnomics)",
            "unit": "diffusion index",
            "members": [
                {
                    "series_id": "DBNOMICS_ISM_MANUF_PMI",
                    "provider_code": "ISM",
                    "dataset_code": "pmi",
                    "series_code": "pm",
                    "upstream_publisher": "Institute for Supply Management (ISM)",
                    "label": "ISM Manufacturing PMI headline",
                }
            ],
        },
    }


def _body(provider="ISM", dataset="pmi", series="pm",
          periods=("2020-05", "2020-06", "2020-07"),
          values=(43.1, 52.2, None)):
    return json.dumps({
        "errors": None,
        "series": {
            "docs": [
                {
                    "provider_code": provider,
                    "dataset_code": dataset,
                    "series_code": series,
                    "series_name": "PMI",
                    "@frequency": "monthly",
                    "period": list(periods),
                    "value": list(values),
                }
            ]
        },
    }).encode("utf-8")


def test_a_one_record_per_obs_verbatim_with_lineage():
    records = adapters.normalize(_source(), _body(), "2026-08-09T11:00:00Z")
    # third obs is null -> dropped, so 2 records.
    assert len(records) == 2
    r = next(r for r in records if r["observation_period"] == "2020-05")
    assert r["series_id"] == "DBNOMICS_ISM_MANUF_PMI"
    assert r["value"] == "43.1" and isinstance(r["value"], str)
    assert r["unit"] == "diffusion index"
    # lineage back to the original publisher survives verbatim (§3.1/§7.3).
    assert r["dbnomics_series_ref"] == "ISM/pmi/pm"
    assert r["upstream_publisher"] == "Institute for Supply Management (ISM)"


def test_b_identity_mismatch_refuses():
    # aggregator doc claims a different dataset than configured -> refuse, never relabel.
    body = _body(dataset="nm-pmi")
    try:
        adapters.normalize(_source(), body, "2026-08-09T11:00:00Z")
    except adapters.SourceUnavailable:
        return
    raise AssertionError("mismatched DBnomics identity must raise SourceUnavailable")


def test_c_na_observation_is_absence():
    records = adapters.normalize(_source(), _body(), "2026-08-09T11:00:00Z")
    got = {r["observation_period"] for r in records}
    assert "2020-07" not in got   # null value dropped
    assert {"2020-05", "2020-06"} <= got


def test_d_labels_come_from_config_not_guessed():
    records = adapters.normalize(_source(), _body(), "2026-08-09T11:00:00Z")
    r = records[0]
    assert r["value_status"] == "observed"
    assert r["information_set_mode"] == "current_revised"
    assert r["source_id"] == "dbnomics_ism_manufacturing_pmi_current_offline"
    assert r["provider_vintage_kind"] == "dbnomics_aggregator_mirror"


def test_e_factory_onboarding_exact_output_ids():
    # B-ACQ-AGGREGATORS landing: the dbnomics_json complete output identity is the
    # member series_id declared in config (exactly one member per source, per the
    # adapter), so factory onboarding must derive it (EXPLICIT_OUTPUT_ID_ADAPTERS).
    from live_data.rmv2_live import feed_factory
    ids = feed_factory._adapter_output_series_ids(_source(), require_complete=True)
    assert ids == frozenset({"DBNOMICS_ISM_MANUF_PMI"})
