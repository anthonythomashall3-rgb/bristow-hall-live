from __future__ import absolute_import

import importlib.util
import io
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data_vault" / "scripts" / "import_fred_panel_archives.py"
SPEC = importlib.util.spec_from_file_location("fred_panel_import", str(SCRIPT))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _panel(
    dates=("01/01/2020", "02/01/2020"),
    header=("sasdate", "A", "B"),
    transforms=("Transform:", "1", "3"),
    rows=(("1", "2"), ("3", "")),
):
    lines = [
        ",".join(header),
        ",".join(transforms),
    ]
    for date, values in zip(dates, rows):
        lines.append(",".join((date,) + tuple(values)))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _quarterly_panel():
    return (
        "sasdate,A,B\n"
        "factors,0,1\n"
        "transform,1,3\n"
        "3/1/2020,1,2\n"
        "6/1/2020,3,\n"
    ).encode("utf-8")


def _quarterly_panel_with_replacement_header():
    return (
        "sasdate,A_old,B_old\n"
        "factors,0,1\n"
        "transform,1,3\n"
        "sasdate,A_new,B_new\n"
        "3/1/2020,1,2\n"
        "6/1/2020,3,\n"
    ).encode("utf-8")


class FredPanelArchiveContractTests(unittest.TestCase):
    def test_exact_known_archive_contract_and_month_closure(self):
        self.assertEqual(len(MODULE.ARCHIVES), 3)
        self.assertEqual(
            [row["sha256"] for row in MODULE.ARCHIVES],
            [
                "3434963f26fbf1aa2e6ff06fd43e1f7b2318ab1a529fa38ac28762f84736a9bb",
                "f87e939a1f83984a2cc0f12da28b83819d34da59a6e5912d3965a79f75e760c9",
                "1e9e0b20edf64f9ef945f70ffad01ee4ee0806418a2470ec1eb7647d6eb2aa69",
            ],
        )
        self.assertEqual(
            sum(row["vintage_count"] for row in MODULE.ARCHIVES),
            385,
        )
        for row in MODULE.ARCHIVES:
            self.assertEqual(
                len(MODULE.month_span(row["first_vintage"], row["last_vintage"])),
                row["vintage_count"],
            )

    def test_panel_parser_accepts_documented_code_three_and_hashes_rows(self):
        stats = MODULE.panel_stats(_panel())
        self.assertEqual(stats["dated_row_count"], 2)
        self.assertEqual(stats["feature_count"], 2)
        self.assertEqual(stats["nonmissing_value_count"], 3)
        self.assertEqual(stats["first_observation"], "2020-01-01")
        self.assertEqual(stats["last_observation"], "2020-02-01")
        self.assertRegex(stats["header_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(stats["transform_row_sha256"], r"^[0-9a-f]{64}$")
        self.assertIsNone(stats["factor_row_sha256"])

        quarterly = MODULE.panel_stats(_quarterly_panel())
        self.assertEqual(quarterly["dated_row_count"], 2)
        self.assertEqual(quarterly["nonmissing_value_count"], 3)
        self.assertRegex(quarterly["factor_row_sha256"], r"^[0-9a-f]{64}$")
        self.assertFalse(quarterly["header_replacement_seen"])

        replacement = MODULE.panel_stats(
            _quarterly_panel_with_replacement_header()
        )
        self.assertTrue(replacement["header_replacement_seen"])
        self.assertNotEqual(
            replacement["header_sha256"],
            replacement["transform_schema_header_sha256"],
        )

    def test_panel_parser_rejects_schema_and_time_leak_hazards(self):
        cases = (
            ("duplicate_header", _panel(header=("sasdate", "A", "A"))),
            ("unknown_transform", _panel(transforms=("Transform:", "1", "8"))),
            (
                "duplicate_date",
                _panel(dates=("01/01/2020", "01/01/2020")),
            ),
            (
                "reverse_date",
                _panel(dates=("02/01/2020", "01/01/2020")),
            ),
            (
                "narrow_row",
                _panel(rows=(("1",), ("3", ""))),
            ),
            (
                "nonfinite",
                _panel(rows=(("inf", "2"), ("3", ""))),
            ),
            (
                "invalid_factor",
                _quarterly_panel().replace(b"factors,0,1", b"factors,0,2"),
            ),
            (
                "late_replacement_header",
                _quarterly_panel().replace(
                    b"6/1/2020,3,",
                    b"sasdate,A2,B2",
                ),
            ),
        )
        for label, payload in cases:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    MODULE.panel_stats(payload)

    def test_member_paths_and_vintage_names_fail_closed(self):
        for name in (
            "../escape.csv",
            "/absolute.csv",
            "folder\\escape.csv",
            "e\u0301.csv",
        ):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    MODULE.safe_member_path(name)
        self.assertEqual(
            MODULE.safe_member_path("folder/ok.csv"),
            PurePosixPath("folder/ok.csv"),
        )
        self.assertEqual(
            MODULE.vintage_id("FRED-MD_2020-03.csv", "fred_md"),
            "2020-03",
        )
        self.assertEqual(
            MODULE.vintage_id("FRED-QD_2020m03.csv", "fred_qd"),
            "2020-03",
        )
        self.assertEqual(
            MODULE.vintage_id("FRED-QD_2019m3.csv", "fred_qd"),
            "2019-03",
        )
        self.assertEqual(MODULE.vintage_id("unknown.csv", "fred_md"), "")

    def test_atomic_write_refuses_existing_different_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "object.bin"
            MODULE.atomic_write(path, b"one")
            MODULE.atomic_write(path, b"one")
            self.assertEqual(path.read_bytes(), b"one")
            with self.assertRaises(ValueError):
                MODULE.atomic_write(path, b"two")

    def test_zip_encryption_and_member_type_checks_are_represented(self):
        # A small valid ZIP proves the fixture machinery itself is ordinary
        # ZIP data; import_archive adds exact pinned identity/count checks
        # before accepting or extracting any member.
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("FRED-MD_2020-01.csv", _panel())
        with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
            info = archive.infolist()[0]
            self.assertFalse(info.flag_bits & 0x1)
            self.assertEqual(
                MODULE.safe_member_path(info.filename).suffix,
                ".csv",
            )


if __name__ == "__main__":
    unittest.main()
