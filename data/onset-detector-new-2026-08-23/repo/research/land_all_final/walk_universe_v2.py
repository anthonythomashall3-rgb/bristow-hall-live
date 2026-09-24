#!/usr/bin/env python3
"""B-LAND-ALL-FINAL STEP 0 (WAVE 26): fresh recursive SHA walk of the CURRENT
full ~/Projects/bristow-hall tree, unlimited depth, all archives/backups/snapshots.
Physical dirs only (symlink shims NOT followed -> no double count). Writes
data_universe_index.v2.json + a compact summary. Read-only; zero store writes."""
import os, hashlib, json, sys, time

HOME = os.path.expanduser("~")
BH = os.path.join(HOME, "Projects/bristow-hall")
# physical roots (no symlink shims); + read-only Codex outputs
ROOTS = [os.path.join(BH, d) for d in
         ("archive","inbox","inventories","ops","papers","projects-old",
          "queue","repo","rulebooks","site")]
ROOTS.append(os.path.join(HOME, "Documents/Codex"))

SKIP_DIR = {".git", "__pycache__", ".pytest_cache", "node_modules",
            ".remember", ".mypy_cache", ".ruff_cache", ".venv", "venv",
            ".ipynb_checkpoints", ".idea", ".vscode"}
SKIP_NAME = {".DS_Store"}

DATA_EXT = {".csv",".tsv",".json",".ndjson",".jsonl",".parquet",".npz",".npy",
            ".xls",".xlsx",".xlsm",".xlsb",".dta",".sav",".h5",".hdf5",".feather",
            ".arrow",".pkl",".pickle",".dat",".xml",".zip",".gz",".bz2",".xz",
            ".7z",".tar",".db",".sqlite",".sqlite3"}
CODE_EXT = {".py",".sh",".js",".ts",".tsx",".jsx",".c",".h",".cpp",".go",".rs",
            ".rb",".java",".pl",".lua",".r",".sql",".yaml",".yml",".toml",".ini",
            ".cfg",".mk",".makefile",".plist",".lock"}
DOC_EXT = {".md",".txt",".rst",".pdf",".html",".htm",".tex",".rtf",".csl"}
IMG_EXT = {".png",".jpg",".jpeg",".gif",".svg",".webp",".ico",".pdf"}

def klass_of(name, path):
    ext = os.path.splitext(name)[1].lower()
    low = path.lower()
    if ext in CODE_EXT: return "code", ext
    if ext in DATA_EXT: return "data", ext
    if ext in IMG_EXT:  return "image", ext
    if ext in DOC_EXT:  return "doc", ext
    return "other", ext

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def tree_of(path):
    rel = os.path.relpath(path, BH)
    return rel.split(os.sep)[0] if not rel.startswith("..") else "Codex"

def main():
    out_dir = os.path.join(BH, "repo/research/land_all_final")
    os.makedirs(out_dir, exist_ok=True)
    files = []
    n = 0; t0 = time.time(); errs = 0
    prog = open(os.path.join(out_dir, "walk_progress.txt"), "w")
    for root in ROOTS:
        if not os.path.isdir(root):
            prog.write(f"MISSING ROOT {root}\n"); prog.flush(); continue
        for dp, dns, fns in os.walk(root, followlinks=False):
            dns[:] = [d for d in dns if d not in SKIP_DIR]
            for fn in fns:
                if fn in SKIP_NAME: continue
                fp = os.path.join(dp, fn)
                try:
                    if os.path.islink(fp): continue
                    st = os.stat(fp)
                    sz = st.st_size
                    sh = sha256(fp)
                except Exception as e:
                    errs += 1; continue
                kl, ext = klass_of(fn, fp)
                files.append({"path": fp, "tree": tree_of(fp), "size": sz,
                              "name": fn, "ext": ext, "sha256": sh, "klass": kl})
                n += 1
                if n % 5000 == 0:
                    prog.write(f"{n} files  {time.time()-t0:.0f}s  cur={root}\n"); prog.flush()
    prog.write(f"DONE walk n={n} errs={errs} {time.time()-t0:.0f}s\n"); prog.close()

    # unique by sha
    by_sha = {}
    total_bytes = 0
    per_tree = {}; per_class = {}
    for r in files:
        total_bytes += r["size"]
        per_tree[r["tree"]] = per_tree.get(r["tree"], 0) + 1
        per_class[r["klass"]] = per_class.get(r["klass"], 0) + 1
        by_sha.setdefault(r["sha256"], r)  # first occurrence
    uniq = list(by_sha.values())
    uniq_bytes = sum(r["size"] for r in uniq)

    index = {
        "schema_version": "recession-monitor-v2.data-universe-index.v2",
        "generated_by": "B-LAND-ALL-FINAL STEP0 walk_universe_v2.py (WAVE 26)",
        "roots": ROOTS,
        "total_files": n,
        "total_bytes": total_bytes,
        "unique_files_by_sha": len(uniq),
        "unique_bytes": uniq_bytes,
        "walk_errors": errs,
        "per_tree": per_tree,
        "per_class": per_class,
        "files": files,
    }
    with open(os.path.join(BH, "repo/data_universe_index.v2.json"), "w") as f:
        json.dump(index, f)
    # compact summary (no file list) for reading back
    summ = {k: v for k, v in index.items() if k != "files"}
    with open(os.path.join(out_dir, "walk_summary.json"), "w") as f:
        json.dump(summ, f, indent=2)
    print("WALK COMPLETE", json.dumps(summ)[:400])

if __name__ == "__main__":
    main()
