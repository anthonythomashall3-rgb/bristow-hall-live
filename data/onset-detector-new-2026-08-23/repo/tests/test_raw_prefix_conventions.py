import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_raw_prefix_registry_is_scope_aware_and_matches_inventory_builder():
    registry = json.loads(
        (ROOT / "data_vault/catalog/raw_prefix_conventions.v1.json").read_text()
    )
    conventions = registry["conventions"]
    assert conventions["_r_"]["predecessor_raw_meaning"] == "refresh_snapshot_audit_copy"
    assert conventions["_r_"]["predecessor_candidate_eligible"] is False
    assert conventions["_r_"]["retained_vault_meaning"] == "legacy_filename_prefix_only"

    tree = ast.parse(
        (ROOT / "data_vault/scripts/build_local_inventory.py").read_text()
    )
    declared = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", None) == "ROOT_SERIES_PREFIXES" for target in node.targets)
    )
    assert tuple(registry["recognized_root_series_prefixes"]) == declared
