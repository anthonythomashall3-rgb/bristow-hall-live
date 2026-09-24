from rmv2_extension.archive_fetch_recipes import build_archive_fetch_recipes


def test_builds_candidate_only_download_recipes_with_collision_safe_paths():
    discovery = {
        "results": [
            {
                "archive_id": "qss",
                "status": "SUCCESS",
                "links": [
                    "https://www2.census.gov/services/qss/2026/report.pdf",
                    "https://www2.census.gov/services/qss/2025/report.pdf",
                    "https://www2.census.gov/services/qss/2026/data.xlsx?download=1",
                ],
            },
            {"archive_id": "failed", "status": "FAILED", "links": []},
        ]
    }
    doc = build_archive_fetch_recipes(discovery)
    assert doc["candidate_only"] is True
    assert len(doc["recipes"]) == 3
    destinations = {row["destination"] for row in doc["recipes"]}
    assert len(destinations) == 3
    assert all(path.startswith("archive_candidates/qss/") for path in destinations)
    assert all(row["public_eligible"] is False for row in doc["recipes"])
    assert all(row["allowed_hosts"] == ["www2.census.gov"] for row in doc["recipes"])
    pdf_rows = [row for row in doc["recipes"] if row["url"].endswith(".pdf")]
    assert all(row["required_prefix"] == "%PDF" for row in pdf_rows)
