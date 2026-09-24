"""Integrity guard for the transparently recovered forecaster companions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METHOD = ROOT / "method_source"
MANIFEST = METHOD / "forecaster" / "artifacts" / "registration_manifest.json"


def test_recovered_forecaster_companions_are_pinned_without_backdating():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema"] == "bh.forecaster.registration.v2"
    recovery = manifest["recovery"]
    assert recovery["status"] == "reconstructed_companions"
    assert recovery["historical_results_already_viewed"] is True
    assert recovery["companions_are_preregistration_evidence"] is False
    assert manifest["authentic_original_registration"] == {
        "path": "forecaster/protocol_v2.json",
        "sha256": "a9ebc23d693024d2d8eed93fe62fc4c28c10f9e2b7935afacf9bb0115711d08f",
        "scope": (
            "The JSON protocol is the only materialized byte proven to exist at "
            "original registration. Its original status is not transferred to "
            "later companion documents."
        ),
    }
    assert len(manifest["superseded_unmaterialized_pins"]) == 6

    for relative, expected in manifest["pinned_files"].items():
        path = METHOD / relative
        assert path.is_file(), relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
        if relative.startswith("research/"):
            text = path.read_text()
            assert "Post-registration reconstruction" in text
            disclosure = text[:700].lower()
            assert "preregistration" in disclosure
            assert "not" in disclosure
