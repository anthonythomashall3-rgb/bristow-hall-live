import json
from pathlib import Path

from rmv2_extension.publisher import execute_upload_plan


def plan():
    return {
        "schema_version": "recession-monitor-v2.r2-upload-plan.v1",
        "generation_sha256": "abc",
        "pointer_last": True,
        "steps": [
            {"key": "generations/abc/data/a.json", "command": "upload-a", "immutable": True},
            {"key": "current.json", "command": "upload-pointer", "immutable": False},
        ],
    }


def test_dry_run_executes_nothing():
    called = []
    receipt = execute_upload_plan(plan(), apply=False, runner=lambda command: called.append(command) or 0)
    assert receipt["status"] == "DRY_RUN"
    assert receipt["executed_steps"] == []
    assert called == []


def test_generation_failure_prevents_pointer_switch():
    called = []
    def runner(command):
        called.append(command)
        return 1 if command == "upload-a" else 0
    receipt = execute_upload_plan(plan(), apply=True, runner=runner)
    assert receipt["status"] == "FAILED"
    assert called == ["upload-a"]
    assert receipt["pointer_switched"] is False


def test_success_runs_pointer_last_and_writes_receipt(tmp_path):
    called = []
    receipt_path = tmp_path / "receipt.json"
    receipt = execute_upload_plan(plan(), apply=True, runner=lambda command: called.append(command) or 0, receipt_path=receipt_path)
    assert receipt["status"] == "SUCCESS"
    assert called == ["upload-a", "upload-pointer"]
    assert receipt["pointer_switched"] is True
    saved = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert saved["generation_sha256"] == "abc"
