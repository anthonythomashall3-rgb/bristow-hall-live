import functools
import http.server
import threading

import pytest

from rmv2_extension.archive_scraper import ArchiveRecipe, discover_archive


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@pytest.fixture
def server(tmp_path):
    source = tmp_path / "site"; source.mkdir()
    handler = functools.partial(QuietHandler, directory=str(source))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True); thread.start()
    try:
        yield source, "http://127.0.0.1:%d" % httpd.server_port
    finally:
        httpd.shutdown(); thread.join(timeout=5)


def test_discovers_sorted_relative_archive_links_and_excludes_cross_host(server):
    source, base = server
    (source / "index.html").write_text('''<a href="files/b.xlsx">B</a><a href="/files/a.pdf">A</a><a href="https://evil.test/x.csv">X</a><a href="notes.txt">N</a>''', encoding="utf-8")
    recipe = ArchiveRecipe(
        archive_id="test", page_url=base + "/index.html", allowed_hosts=["127.0.0.1"],
        allowed_suffixes=[".pdf", ".xlsx"], include_pattern=r"/files/",
    )
    result = discover_archive(recipe)
    assert result["status"] == "SUCCESS"
    assert result["links"] == [base + "/files/a.pdf", base + "/files/b.xlsx"]


def test_page_host_must_be_allowlisted(server):
    _source, base = server
    recipe = ArchiveRecipe("test", base + "/index.html", ["example.com"], [".pdf"])
    with pytest.raises(ValueError, match="allowlist"):
        discover_archive(recipe)


def test_non_html_response_is_rejected(server):
    source, base = server
    (source / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    recipe = ArchiveRecipe("test", base + "/data.csv", ["127.0.0.1"], [".csv"])
    result = discover_archive(recipe)
    assert result["status"] == "FAILED"
    assert "HTML" in result["error"]
