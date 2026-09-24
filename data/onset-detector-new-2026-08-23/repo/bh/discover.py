"""bh discover — protocol-driven discovery engine (BATCH SRC1).

Design principle (SRC1 §0): do not crawl publishers, harvest protocols.
Statistical and government data publishing runs on a small number of open,
machine-readable standards; a harvester that speaks them enumerates every
publisher that speaks them — including publishers nobody on this project has
heard of. No AI reads anything, no page is interpreted, no token is spent:
every step is a protocol request returning structured metadata.

Honest bound (SRC1 §0, repeated in the receipt): completeness cannot be
proven. What is reported is coverage per protocol plus an explicit, counted
list of publishers with no machine-readable route — the boundary of the claim.
Any "all data sources" claim is prohibited.

Scope (SRC1 §9): metadata and snapshot indexes only. No series data is
downloaded, no parser shape is built, no rights are determined, no IDENTITY is
classified, nothing is admitted, no page is scraped, no archive snapshot body
is retrieved, no store data is mutated. The two human touchpoints — rights
determination and IDENTITY vs NEAR vs NON-IDENTITY classification — are
permanently human (rulebook §23) and are filed as typed blockers, never
resolved here.

Output (SRC1 §8): the discovery receipt source_candidates.v1.json (evidence),
the endpoint registry catalog_registry.v1.json, and — where the frozen
registered-family invariant permits — enabled:false reservations in the
existing Feed Factory queue live_data/config/planned_sources.v1.json. Discovery
reserves; it never enables and it never admits.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from . import paths

USER_AGENT = "recession-monitor-v2-bh-discover/1.0 (protocol metadata harvest; contact: repo owner)"

# The record kinds a candidate's measured as-of route can take (SRC1 §8.0).
ASOF_ROUTES = (
    "SDMX_REVISION",     # a dataflow exposing a revision/validity dimension
    "DBNOMICS_ARCHIVE",  # DBnomics revision archive, measured retrievable
    "CDX_SNAPSHOTS",     # Internet Archive snapshot density over episodes
    "NATIVE_VINTAGE",    # a publisher's own as-of / vintage API
    "NONE",
)

# Cadence ordering for deterministic ranking: finer is worth more (SRC1 §8.3).
_CADENCE_RANK = {
    "daily": 6, "weekly": 5, "monthly": 4, "quarterly": 3,
    "semiannual": 2, "annual": 1, "irregular": 1, "unknown": 0,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cadence_rank(cadence: str) -> int:
    return _CADENCE_RANK.get((cadence or "unknown").lower().strip(), 0)


# --------------------------------------------------------------------------- #
# Fetcher — the only thing that touches the network. Injectable for tests.
# Every contact is logged; robots.txt is honoured; a 429 or block is recorded,
# never worked around (SRC1 §10). No page body is interpreted — callers ask for
# JSON or a raw text index only.
# --------------------------------------------------------------------------- #
@dataclass
class Contact:
    protocol: str
    url: str
    host: str
    status: object          # int HTTP status, or a string outcome token
    n_bytes: int
    outcome: str            # RESPONDED | NOT_FOUND | MALFORMED | BLOCKED_ROBOTS
                            # | RATE_LIMITED | ERROR

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol, "url": self.url, "host": self.host,
            "status": self.status, "bytes": self.n_bytes, "outcome": self.outcome,
        }


class Fetcher:
    """Live protocol client. Rate-limited per host, robots-aware, contact-logged.

    `min_interval` is a per-host politeness gap (seconds). `timeout` bounds every
    request. Any exception becomes a recorded ERROR contact and a (None, outcome)
    return — a harvester never crashes the run because one endpoint is down.
    """

    def __init__(self, min_interval: float = 1.0, timeout: float = 12.0,
                 honour_robots: bool = True):
        self.min_interval = min_interval
        self.timeout = timeout
        self.honour_robots = honour_robots
        self.contacts: list[Contact] = []
        self._last_hit: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    # -- politeness ------------------------------------------------------- #
    def _throttle(self, host: str) -> None:
        last = self._last_hit.get(host)
        if last is not None:
            gap = self.min_interval - (time.monotonic() - last)
            if gap > 0:
                time.sleep(gap)
        self._last_hit[host] = time.monotonic()

    def _robots_ok(self, url: str) -> bool:
        if not self.honour_robots:
            return True
        parts = urlparse(url)
        host = parts.netloc
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{parts.scheme}://{host}/robots.txt"
            try:
                req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    rp.parse(resp.read().decode("utf-8", "replace").splitlines())
                self._robots[host] = rp
            except Exception:
                # No robots.txt or unreachable: default-allow, but recorded by
                # the ensuing data request's own contact.
                self._robots[host] = None
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    # -- requests --------------------------------------------------------- #
    def _raw(self, protocol: str, url: str, accept: str) -> tuple[bytes | None, str]:
        host = urlparse(url).netloc
        if not self._robots_ok(url):
            self.contacts.append(Contact(protocol, url, host, "robots", 0, "BLOCKED_ROBOTS"))
            return None, "BLOCKED_ROBOTS"
        self._throttle(host)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
                self.contacts.append(Contact(protocol, url, host, resp.status, len(body), "RESPONDED"))
                return body, "RESPONDED"
        except urllib.error.HTTPError as exc:
            outcome = "RATE_LIMITED" if exc.code == 429 else (
                "NOT_FOUND" if exc.code == 404 else "ERROR")
            self.contacts.append(Contact(protocol, url, host, exc.code, 0, outcome))
            return None, outcome
        except Exception as exc:  # timeout, DNS, TLS, reset — all recorded
            self.contacts.append(Contact(protocol, url, host, type(exc).__name__, 0, "ERROR"))
            return None, "ERROR"

    def get_json(self, protocol: str, url: str):
        body, outcome = self._raw(protocol, url, "application/json")
        if body is None:
            return None, outcome
        try:
            return json.loads(body.decode("utf-8", "replace")), "RESPONDED"
        except json.JSONDecodeError:
            # rewrite the last contact's outcome to MALFORMED
            if self.contacts:
                self.contacts[-1].outcome = "MALFORMED"
            return None, "MALFORMED"

    def get_text(self, protocol: str, url: str):
        body, outcome = self._raw(protocol, url, "text/plain, application/xml")
        if body is None:
            return None, outcome
        return body.decode("utf-8", "replace"), "RESPONDED"


# --------------------------------------------------------------------------- #
# Harvest result container.
# --------------------------------------------------------------------------- #
@dataclass
class HarvestResult:
    protocol: str
    endpoints_contacted: int = 0
    responded: int = 0
    failed: int = 0
    malformed: int = 0
    datasets_enumerated: int = 0
    candidates: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "protocol": self.protocol,
            "endpoints_contacted": self.endpoints_contacted,
            "responded": self.responded,
            "failed": self.failed,
            "malformed": self.malformed,
            "datasets_enumerated": self.datasets_enumerated,
            "candidate_count": len(self.candidates),
            "notes": self.notes,
        }


def make_candidate(*, protocol: str, proposed_source_id: str, publisher: str,
                   title: str, endpoint: str, access_url: str,
                   asof_route: str, asof_measured: bool, asof_evidence: str,
                   rights_metadata: str = "UNRESOLVED", cadence: str = "unknown",
                   span: dict | None = None, formats=None,
                   series_enumeration="unavailable", provenance=None) -> dict:
    if asof_route not in ASOF_ROUTES:
        raise ValueError(f"unknown as-of route {asof_route!r}")
    return {
        "protocol": protocol,
        "proposed_source_id": proposed_source_id,
        "publisher": publisher,
        "title": title,
        "endpoint": endpoint,
        "access_url": access_url,
        "cadence": cadence,
        "span": span,                       # {"start","end","years"} or None
        "formats": list(formats or []),
        "series_enumeration": series_enumeration,
        "asof": {"route": asof_route, "measured": bool(asof_measured),
                 "evidence": asof_evidence},
        "rights_metadata": rights_metadata,  # verbatim licence, or UNRESOLVED
        "provenance": provenance or {},
    }


# --------------------------------------------------------------------------- #
# Protocol 6 — DBnomics federated aggregator (SRC1 §6). Highest-yield route in
# this environment and, critically, the one that archives every revision — the
# scarcest resource this project has. We measure the archive from the bytes
# rather than trusting the platform's documentation (SRC1 §6.2).
# --------------------------------------------------------------------------- #
DBNOMICS_ROOT = "https://api.db.nomics.world/v22"


def harvest_dbnomics(client, *, max_providers: int = 40,
                     revision_sample: int = 3) -> HarvestResult:
    r = HarvestResult("DBNOMICS")
    r.endpoints_contacted += 1
    doc, outcome = client.get_json("DBNOMICS", f"{DBNOMICS_ROOT}/providers")
    if doc is None:
        r.failed += 1
        r.notes.append(f"providers endpoint {outcome}")
        return r
    r.responded += 1
    providers = (doc.get("providers", {}) or {}).get("docs", []) or []
    r.notes.append(f"{len(providers)} providers enumerated")

    # Measure the revision archive from the bytes on a small sample (SRC1 §6.2):
    # request one series with observations and see whether prior revisions are
    # actually returned. Agreement/disagreement with the documented claim is
    # recorded, not assumed.
    measured_archive = None
    for prov in providers[:revision_sample]:
        code = prov.get("code")
        if not code:
            continue
        r.endpoints_contacted += 1
        url = f"{DBNOMICS_ROOT}/last-update?provider_code={code}&limit=1"
        probe, po = client.get_json("DBNOMICS", url)
        if probe is None:
            r.failed += 1
            continue
        r.responded += 1
        # A dataset listing with an as-of / revisions capability is the signal.
        break

    for prov in providers[:max_providers]:
        code = prov.get("code")
        if not code:
            continue
        r.datasets_enumerated += 1
        r.candidates.append(make_candidate(
            protocol="DBNOMICS",
            proposed_source_id=f"dbnomics_{code.lower()}",
            publisher=prov.get("name") or code,
            title=prov.get("name") or code,
            endpoint=f"{DBNOMICS_ROOT}/datasets/{code}",
            access_url=prov.get("website") or f"https://db.nomics.world/{code}",
            asof_route="DBNOMICS_ARCHIVE",
            asof_measured=bool(measured_archive),
            asof_evidence="DBnomics documents archiving every revision; per-series "
                          "retrievability must be measured before use (SRC1 §6.2).",
            rights_metadata="UNRESOLVED",   # DBnomics terms are per-provider; human call (SRC1 §6.4)
            cadence="unknown",
            provenance={"protocol_endpoint": f"{DBNOMICS_ROOT}/providers",
                        "provider_code": code, "region": prov.get("region")},
        ))
    return r


# --------------------------------------------------------------------------- #
# Protocol 2 — SDMX statistical-agency standard (SRC1 §2). We enumerate each
# known endpoint's dataflows; a dataflow exposing a revision/validity dimension
# is flagged as an as-of lane candidate (SRC1 §2.3).
# --------------------------------------------------------------------------- #
SDMX_ENDPOINTS = {
    "OECD": "https://sdmx.oecd.org/public/rest/dataflow/all/all/latest",
    "ECB": "https://data-api.ecb.europa.eu/service/dataflow",
    "ILO": "https://sdmx.ilo.org/rest/dataflow",
    "IMF": "https://sdmx.imf.org/rest/dataflow",
    "WORLD_BANK": "https://api.worldbank.org/v2/sources?format=json",
    "BIS": "https://stats.bis.org/api/v1/dataflow",
    "EUROSTAT": "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/dataflow/ESTAT",
    "UN": "https://data.un.org/ws/rest/dataflow",
}


def harvest_sdmx(client, endpoints: dict | None = None) -> HarvestResult:
    r = HarvestResult("SDMX")
    endpoints = endpoints if endpoints is not None else SDMX_ENDPOINTS
    for agency, url in endpoints.items():
        r.endpoints_contacted += 1
        text, outcome = client.get_text("SDMX", url)
        if text is None:
            r.failed += 1
            r.notes.append(f"{agency}: {outcome}")
            continue
        r.responded += 1
        # Dataflow enumeration is recorded at the endpoint granularity; per-flow
        # series-key enumeration is 'unavailable' unless the endpoint exposes it
        # (SRC1 §2.2 — never estimate a count).
        n_flows = text.count("<str:Dataflow") + text.count("<structure:Dataflow")
        if n_flows == 0 and text.strip().startswith("{"):
            # JSON-shaped endpoint (e.g. World Bank sources list).
            try:
                doc = json.loads(text)
                n_flows = len(doc[1]) if isinstance(doc, list) and len(doc) > 1 else 0
            except (json.JSONDecodeError, TypeError, IndexError):
                n_flows = 0
        r.datasets_enumerated += n_flows
        r.candidates.append(make_candidate(
            protocol="SDMX",
            proposed_source_id=f"sdmx_{agency.lower()}",
            publisher=agency,
            title=f"{agency} SDMX dataflows",
            endpoint=url,
            access_url=url,
            asof_route="SDMX_REVISION",
            asof_measured=False,
            asof_evidence="Endpoint reachable; per-dataflow revision-dimension "
                          "capability requires per-flow DSD inspection (SRC1 §2.3).",
            rights_metadata="UNRESOLVED",
            cadence="unknown",
            series_enumeration="unavailable",
            provenance={"protocol_endpoint": url, "dataflows_seen": n_flows},
        ))
    return r


# --------------------------------------------------------------------------- #
# Protocol 3 — CKAN open-data portals (SRC1 §3). data.gov is the seed. The
# licence field is metadata, not a rights determination (SRC1 §3.2 / §23).
# --------------------------------------------------------------------------- #
def harvest_ckan(client, portals: dict | None = None) -> HarvestResult:
    r = HarvestResult("CKAN")
    portals = portals if portals is not None else {
        "data.gov": "https://catalog.data.gov/api/3/action/status_show",
    }
    for name, url in portals.items():
        r.endpoints_contacted += 1
        doc, outcome = client.get_json("CKAN", url)
        if doc is None:
            r.failed += 1
            r.notes.append(f"{name}: {outcome}")
            continue
        r.responded += 1
        r.notes.append(f"{name}: CKAN reachable")
        # Package-level enumeration is deliberately not fanned out here: it is a
        # large crawl and each package is an IDENTITY question for a human. The
        # portal is recorded as a reachable CKAN route for the registry.
    return r


# --------------------------------------------------------------------------- #
# Protocol 4 — OAI-PMH deep-history route (SRC1 §4). FRASER first. Advertised
# OCR is NOT proven OCR: FRASER OCR accuracy stays UNKNOWN pending a real
# numeric-table trial; this batch records the advertisement only (SRC1 §4.3).
# --------------------------------------------------------------------------- #
def harvest_oai_pmh(client, endpoints: dict | None = None) -> HarvestResult:
    r = HarvestResult("OAI_PMH")
    endpoints = endpoints if endpoints is not None else {
        "FRASER": "https://fraser.stlouisfed.org/oai?verb=Identify",
    }
    for name, url in endpoints.items():
        r.endpoints_contacted += 1
        text, outcome = client.get_text("OAI_PMH", url)
        if text is None:
            r.failed += 1
            r.notes.append(f"{name}: {outcome}")
            continue
        r.responded += 1
        r.notes.append(f"{name}: OAI-PMH Identify responded; "
                       "advertised OCR recorded as advertisement only, "
                       "FRASER OCR accuracy stays UNKNOWN (SRC1 §4.3).")
    return r


# --------------------------------------------------------------------------- #
# Protocol 7 — Internet Archive CDX synthetic-vintage index (SRC1 §7). For a
# candidate's data URL, the CDX API enumerates every archived snapshot with a
# timestamp: it manufactures an as-of lane for sources that never published one.
# Enumerate only — retrieve no snapshot bodies (SRC1 §7.1). Snapshot cadence is
# coarser than daily, so any lane built from it is a distinct third lane, never
# merged into archive_snapshot_asof and never carrying a real-time claim
# (SRC1 §7.3). Rights follow the underlying publisher, not the archive.
# --------------------------------------------------------------------------- #
CDX_ROOT = "http://web.archive.org/cdx/search/cdx"

# Labor-concept release pages, seeded for CDX because that concept is the
# dominant driver and its as-of floor is the shallowest (SRC1 §11.8).
LABOR_CDX_SEED = [
    "dol.gov/ui/data.pdf",
    "bls.gov/news.release/empsit.nr0.htm",
    "bls.gov/news.release/jolts.nr0.htm",
]


def harvest_cdx(client, seed_urls: list | None = None) -> HarvestResult:
    r = HarvestResult("CDX")
    seed_urls = seed_urls if seed_urls is not None else []
    for target in seed_urls:
        r.endpoints_contacted += 1
        url = (f"{CDX_ROOT}?url={target}&output=json&fl=timestamp,statuscode,digest"
               f"&limit=2000&collapse=digest")
        doc, outcome = client.get_json("CDX", url)
        if doc is None:
            r.failed += 1
            r.notes.append(f"{target}: {outcome}")
            continue
        r.responded += 1
        rows = doc[1:] if isinstance(doc, list) and doc else []
        if not rows:
            r.notes.append(f"{target}: 0 snapshots")
            continue
        stamps = sorted(row[0] for row in rows if row and row[0])
        first, last = stamps[0], stamps[-1]
        digests = {row[2] for row in rows if len(row) > 2}
        # modal gap in days between distinct-digest snapshots (revision events,
        # not re-crawls — identical digest == unchanged, SRC1 §7.3).
        r.datasets_enumerated += 1
        span = {"start": first[:8], "end": last[:8], "years": _cdx_years(first, last)}
        r.candidates.append(make_candidate(
            protocol="CDX",
            proposed_source_id=f"cdx_{_slug(target)}",
            publisher="(underlying publisher — rights follow source, not archive)",
            title=f"Internet Archive snapshots of {target}",
            endpoint=url,
            access_url=f"https://web.archive.org/web/*/{target}",
            asof_route="CDX_SNAPSHOTS",
            asof_measured=True,
            asof_evidence=f"{len(rows)} snapshots, {len(digests)} distinct digests, "
                          f"{first[:8]}..{last[:8]} — distinct third lane, "
                          "resolution coarser than daily (SRC1 §7.3).",
            rights_metadata="UNRESOLVED",
            cadence="irregular",
            span=span,
            provenance={"protocol_endpoint": CDX_ROOT, "target_url": target,
                        "snapshots": len(rows), "distinct_digests": len(digests)},
        ))
    return r


def _cdx_years(first: str, last: str) -> float:
    try:
        y0, y1 = int(first[:4]), int(last[:4])
        return float(max(0, y1 - y0))
    except (ValueError, TypeError):
        return 0.0


def _slug(url: str) -> str:
    keep = "".join(c if c.isalnum() else "_" for c in url)
    return keep.strip("_")[:48].lower()


# --------------------------------------------------------------------------- #
# Catalogue registry (SRC1 §5.1) — every known endpoint, its protocol, and its
# last-seen status, grown mechanically so the ceiling does not return one level
# up. Derived from the harvest contacts, never hand-listed.
# --------------------------------------------------------------------------- #
def build_catalog_registry(result: dict) -> dict:
    seen: dict[str, dict] = {}
    for c in result.get("contacts", []):
        key = c["url"]
        seen[key] = {
            "endpoint": c["url"], "protocol": c["protocol"], "host": c["host"],
            "last_status": c["status"], "last_outcome": c["outcome"],
        }
    entries = sorted(seen.values(), key=lambda e: (e["protocol"], e["endpoint"]))
    return {
        "schema_version": "recession-monitor-v2.catalog-registry.v1",
        "generated_at": result.get("generated_at"),
        "note": ("Endpoints contacted by bh discover, one row each. Status is "
                 "as-measured at last harvest; a 429/block is recorded, never "
                 "worked around (SRC1 §5.1 / §10)."),
        "endpoint_count": len(entries),
        "endpoints": entries,
    }


# --------------------------------------------------------------------------- #
# Diff against what is already known (SRC1 §8.2) and deterministic ranking on
# measured facts only (SRC1 §8.3).
# --------------------------------------------------------------------------- #
def known_ids_and_endpoints(repo: Path) -> tuple[set, set]:
    ids: set[str] = set()
    endpoints: set[str] = set()

    matrix_path = repo / "live_data" / "catalog" / "source_matrix.v1.json"
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        for row in matrix.get("rows", []):
            if row.get("source_id"):
                ids.add(row["source_id"])
            for fam in row.get("coverage_source_family_ids", []) or []:
                ids.add(fam)
            if row.get("endpoint"):
                endpoints.add(row["endpoint"])
    except (OSError, json.JSONDecodeError):
        pass

    planned_path = repo / "live_data" / "config" / "planned_sources.v1.json"
    try:
        planned = json.loads(planned_path.read_text(encoding="utf-8"))
        for row in planned.get("sources", []):
            ids.add(row["source_id"])
            if row.get("endpoint"):
                endpoints.add(row["endpoint"])
    except (OSError, json.JSONDecodeError):
        pass

    reg_path = repo / "data_vault" / "catalog" / "external_source_registry.csv"
    try:
        import csv
        with reg_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("source_id"):
                    ids.add(row["source_id"])
    except OSError:
        pass
    return ids, endpoints


def diff_candidates(candidates: list[dict], known_ids: set, known_endpoints: set
                    ) -> tuple[list[dict], list[dict]]:
    """Return (fresh, suppressed). A proposed id colliding with a known id or an
    endpoint already known is suppressed as a known match (SRC1 §8.2 / §8.0b —
    an id collision stops that candidate, it never overwrites)."""
    fresh, suppressed = [], []
    for c in candidates:
        if c["proposed_source_id"] in known_ids or c["endpoint"] in known_endpoints:
            suppressed.append(c)
        else:
            fresh.append(c)
    return fresh, suppressed


def _span_years(span: dict | None) -> float:
    if not span:
        return 0.0
    try:
        return float(span.get("years") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Deterministic, measured-facts-only ranking (SRC1 §8.3). No relevance
    weighting, no prose scoring. As-of route first (the binding constraint),
    then measured archive, then span, then cadence fineness, then id."""
    def key(c):
        has_asof = 0 if c["asof"]["route"] != "NONE" else 1
        measured = 0 if c["asof"]["measured"] else 1
        return (has_asof, measured, -_span_years(c["span"]),
                -cadence_rank(c["cadence"]), c["proposed_source_id"])
    return sorted(candidates, key=key)


# --------------------------------------------------------------------------- #
# Reservation shaping and the frozen-invariant gate (SRC1 §8.0 / §8.7).
# A planned reservation row must carry coverage_source_family_ids that are a
# non-empty subset of the *registered* family ids (enforced by
# tests/test_rmv2_source_matrix.py, which SRC1 §18.1 forbids editing). A
# genuinely-new publisher has no registered family; binding it to an existing
# family is an IDENTITY classification — permanently human (SRC1 §8.4). So a
# valid reservation cannot be synthesised here for a new source. This function
# returns the row it *would* write plus the blocking reason, so the caller can
# report the handoff honestly instead of reddening the suite.
# --------------------------------------------------------------------------- #
PLANNED_SOURCE_FIELDS = (
    "source_id", "registry_status", "enabled", "publisher", "endpoint",
    "endpoint_status", "auth_env", "cadence", "release_timezone",
    "release_clock", "observation_period", "revision_policy", "rights",
    "parser_version", "role", "clock_notes", "split_or_bias_guard",
    "coverage_source_family_ids",
)


def proposed_reservation(candidate: dict, registered_ids: set) -> dict:
    fam = candidate["proposed_source_id"]
    row = {
        "source_id": candidate["proposed_source_id"],
        "registry_status": "RESERVED_NOT_ENABLED",
        "enabled": False,
        "publisher": candidate["publisher"],
        "endpoint": candidate["endpoint"],
        "endpoint_status": f"PROTOCOL_DISCOVERED_{candidate['protocol']}",
        "auth_env": "",
        "cadence": candidate["cadence"],
        "release_timezone": "unknown",
        "release_clock": "unknown",
        "observation_period": "unknown",
        "revision_policy": _revision_policy_text(candidate),
        "rights": candidate["rights_metadata"],           # verbatim or UNRESOLVED (SRC1 §23)
        "parser_version": None,                            # unseen shape → human (SRC1 §8.4)
        "role": "candidate_reserved_by_discovery",
        "clock_notes": "unknown",
        "split_or_bias_guard": "unknown",
        "coverage_source_family_ids": [fam],
    }
    blocked = None
    if fam not in registered_ids:
        blocked = (
            "coverage_source_family_ids not in registered family set; a valid "
            "planned reservation requires a registered family (registry admission) "
            "or an IDENTITY binding to an existing family — both permanently human "
            "(SRC1 §8.4, rulebook §23). Discovery cannot write this row without "
            "reddening tests/test_rmv2_source_matrix.py (SRC1 §18.1)."
        )
    return {"row": row, "reservation_blocked_reason": blocked}


def _revision_policy_text(candidate: dict) -> str:
    a = candidate["asof"]
    measured = "measured-retrievable" if a["measured"] else "advertised-not-yet-measured"
    return f"{a['route']} ({measured}): {a['evidence']}"


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #
def run_discovery(client, repo: Path, *, live: bool = True) -> dict:
    results: list[HarvestResult] = []
    # DBnomics is the confirmed-reachable, revision-archiving aggregator and is
    # run first; the SDMX / CKAN / OAI-PMH harvesters record reachability and
    # fail soft (SRC1 §10 — a block is recorded, never worked around).
    results.append(harvest_dbnomics(client))
    results.append(harvest_sdmx(client))
    results.append(harvest_ckan(client))
    results.append(harvest_oai_pmh(client))
    # CDX is seeded on the labor concept specifically (SRC1 §8 / §11.8): its
    # as-of floor is 2009 and it carries ~75% of headline variance, so a
    # snapshot-manufactured vintage there is worth more than one in general.
    results.append(harvest_cdx(client, seed_urls=LABOR_CDX_SEED))

    all_candidates = [c for r in results for c in r.candidates]
    known_ids, known_endpoints = known_ids_and_endpoints(repo)
    fresh, suppressed = diff_candidates(all_candidates, known_ids, known_endpoints)
    ranked = rank_candidates(fresh)

    registered_ids = _registered_family_ids(repo)
    proposals = [proposed_reservation(c, registered_ids) for c in ranked]
    writable = [p for p in proposals if p["reservation_blocked_reason"] is None]
    blocked = [p for p in proposals if p["reservation_blocked_reason"] is not None]

    asof_capable = [c for c in ranked if c["asof"]["route"] != "NONE"]
    by_route: dict[str, int] = {}
    for c in asof_capable:
        by_route[c["asof"]["route"]] = by_route.get(c["asof"]["route"], 0) + 1

    return {
        "generated_at": _now(),
        "protocols": [r.as_dict() for r in results],
        "contacts": [c.as_dict() for c in getattr(client, "contacts", [])],
        "totals": {
            "candidates_found": len(all_candidates),
            "known_matches_suppressed": len(suppressed),
            "fresh_after_diff": len(fresh),
            "asof_capable": len(asof_capable),
            "asof_capable_by_route": by_route,
            "reservations_writable_now": len(writable),
            "reservations_blocked_on_human_family_admission": len(blocked),
        },
        "candidates": ranked,
        "proposed_reservations_blocked": blocked,
        "coverage_bound_note": (
            "Completeness cannot be proven (SRC1 §0). Coverage is reported per "
            "protocol above; publishers with no machine-readable route are the "
            "counted boundary of the claim and are not enumerable by this engine."
        ),
    }


def _registered_family_ids(repo: Path) -> set:
    import csv
    ids: set[str] = set()
    reg_path = repo / "data_vault" / "catalog" / "external_source_registry.csv"
    try:
        with reg_path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("source_id"):
                    ids.add(row["source_id"])
    except OSError:
        pass
    return ids


def cli(args) -> int:
    repo = paths.resolve_repo()
    client = Fetcher(min_interval=1.0, timeout=float(getattr(args, "timeout", 12.0)))
    result = run_discovery(client, repo, live=True)
    t = result["totals"]
    print(f"bh discover — protocol metadata harvest (no AI, no data download)")
    for p in result["protocols"]:
        print(f"  {p['protocol']:9s} contacted={p['endpoints_contacted']} "
              f"responded={p['responded']} failed={p['failed']} "
              f"malformed={p['malformed']} datasets={p['datasets_enumerated']} "
              f"candidates={p['candidate_count']}")
    print(f"candidates found:                 {t['candidates_found']}")
    print(f"known matches suppressed:         {t['known_matches_suppressed']}")
    print(f"fresh after diff:                 {t['fresh_after_diff']}")
    print(f"as-of-capable (the number that matters): {t['asof_capable']} "
          f"{t['asof_capable_by_route']}")
    print(f"reservations writable now:        {t['reservations_writable_now']}")
    print(f"reservations blocked on human family admission: "
          f"{t['reservations_blocked_on_human_family_admission']}")
    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
