import functools
import http.server
import json
import threading
from pathlib import Path

import pytest

from rmv2_extension.collector import FetchRecipe, collect_recipes


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@pytest.fixture
def server(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    handler = functools.partial(QuietHandler, directory=str(source))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield source, "http://127.0.0.1:%d" % httpd.server_port
    finally:
        httpd.shutdown()
        thread.join(timeout=5)


def recipe(url, destination="raw/data.csv", **overrides):
    values = dict(
        recipe_id="test",
        url=url,
        destination=destination,
        allowed_hosts=["127.0.0.1"],
        allowed_content_types=["text/csv", "application/octet-stream"],
        min_bytes=4,
        max_bytes=1000,
        required_prefix="date,value",
        retries=0,
        timeout_seconds=3,
    )
    values.update(overrides)
    return FetchRecipe(**values)


def test_valid_download_is_atomic_and_receipted(server, tmp_path):
    source, base = server
    (source / "data.csv").write_text("date,value\n2026-01-01,1\n", encoding="utf-8")
    out = tmp_path / "out"
    result = collect_recipes([recipe(base + "/data.csv")], out, max_workers=2)
    assert result[0]["status"] == "SUCCESS"
    assert (out / "raw/data.csv").read_text(encoding="utf-8").startswith("date,value")
    receipt = json.loads((out / "receipts/test.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "SUCCESS"
    assert len(receipt["sha256"]) == 64


def test_html_masquerading_as_csv_is_rejected_and_lkg_is_preserved(server, tmp_path):
    source, base = server
    (source / "data.csv").write_text("<html>bad</html>", encoding="utf-8")
    out = tmp_path / "out"
    target = out / "raw/data.csv"
    target.parent.mkdir(parents=True)
    target.write_text("date,value\n2025-01-01,7\n", encoding="utf-8")
    result = collect_recipes([recipe(base + "/data.csv")], out)
    assert result[0]["status"] == "FAILED"
    assert target.read_text(encoding="utf-8") == "date,value\n2025-01-01,7\n"


def test_failed_request_does_not_create_destination(tmp_path):
    out = tmp_path / "out"
    result = collect_recipes([recipe("http://127.0.0.1:1/nope.csv")], out)
    assert result[0]["status"] == "FAILED"
    assert not (out / "raw/data.csv").exists()


def test_unsafe_destination_is_rejected_before_network(server, tmp_path):
    _source, base = server
    with pytest.raises(ValueError, match="unsafe destination"):
        collect_recipes([recipe(base + "/data.csv", destination="../escape")], tmp_path)


def test_host_not_in_allowlist_is_rejected(server, tmp_path):
    _source, base = server
    blocked = recipe(base + "/data.csv", allowed_hosts=["example.com"])
    result = collect_recipes([blocked], tmp_path)
    assert result[0]["status"] == "FAILED"
    assert "host" in result[0]["error"].lower()
