import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCANNED_ROOTS = (ROOT / "method_source", ROOT / "live_data")


def _silent_handlers():
    findings = []
    for scanned_root in SCANNED_ROOTS:
        for path in sorted(scanned_root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                if node.type is None:
                    findings.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}:bare-except"
                    )
                elif len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    findings.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}:except-pass"
                    )
    return findings


def test_science_and_live_data_have_no_bare_or_silent_pass_handlers():
    assert _silent_handlers() == []
