import ast
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
BENCH = (
    REPO
    / "model_authority"
    / "forecaster"
    / "forecaster.v2.spec.g1"
    / "regression_bench.v1.json"
)
SOURCE = REPO / "method_source" / "forecaster_site.py"


def _literal_for_key(tree, wanted):
    matches = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == wanted:
                matches.append(ast.literal_eval(value))
    assert len(matches) == 1, "%s occurred %d times" % (wanted, len(matches))
    return matches[0]


def test_forecaster_regression_bench_pins_frozen_disclosures():
    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    assert bench["schema_version"] == "recession-monitor-v2.forecaster-regression-bench.v1"
    assert bench["source"] == "method_source/forecaster_site.py:445-478"
    assert bench["provenance"] == "inherited"
    assert bench["disposition"] == "pin_only_no_refit_or_retirement"

    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    actual_calibration = _literal_for_key(tree, "calibration")["publication_aware"]
    actual_intervals = _literal_for_key(tree, "auc_intervals_95")
    actual_brier_skill = _literal_for_key(
        tree, "brier_skill_displayed_publication_aware"
    )

    expected = bench["baselines"]
    assert actual_brier_skill == expected["brier_skill_displayed_publication_aware"]
    assert actual_calibration["ece"] == expected["ece"]
    assert actual_calibration["base_rate"] == expected["base_rate"]
    assert actual_intervals == expected["auc_intervals_95"]
