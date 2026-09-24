from rmv2_extension.repair_recipes import build_fred_repair_recipes


def test_builds_candidate_only_fred_recipes_for_malformed_series():
    registry = {"items": [
        {"gap_type": "malformed_payload", "entity_type": "series", "entity_id": "PAYEMS"},
        {"gap_type": "frequency_metadata", "entity_type": "series", "entity_id": "OTHER"},
    ]}
    metrics = [{"series_id": "PAYEMS", "provider": "fred", "rights_status": "public_source_reuse_terms_and_attribution_review_required"}]
    doc = build_fred_repair_recipes(registry, metrics)
    assert len(doc["recipes"]) == 1
    recipe = doc["recipes"][0]
    assert recipe["url"].endswith("id=PAYEMS")
    assert recipe["destination"] == "repair_candidates/fred/PAYEMS.csv"
    assert recipe["enabled"] is True
    assert recipe["candidate_only"] is True
    assert recipe["public_eligible"] is False
    assert recipe["required_prefix"] == "observation_date,PAYEMS"
