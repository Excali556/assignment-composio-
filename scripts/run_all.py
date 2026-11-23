"""
Run the pipeline in the only order that produces consistent numbers.

Stage order matters: bind_evidence.py rewrites data/research.json from the extraction
files, so MCP verification must run *after* it (an earlier manual run lost the verified
MCP links and silently changed the audit result).

    python scripts/run_all.py               # rebuild from saved sources (fast, ~20s)
    python scripts/run_all.py --fetch       # also re-fetch all 100 docs pages (~80s)
    python scripts/run_all.py --extract     # also re-run the model extraction (~25min, needs a key)
    python scripts/run_all.py --pricing     # also re-run the pricing-page pass (~2min)
"""
import argparse
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def run(script, *args):
    cmd = [sys.executable, str(HERE / script), *args]
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"stage failed: {script}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-fetch documentation first")
    ap.add_argument("--extract", action="store_true", help="re-run the model extraction (needs a key)")
    ap.add_argument("--pricing", action="store_true", help="re-run the pricing-page pass")
    args = ap.parse_args()

    if args.fetch:
        run("fetch_docs.py")
    run("make_digest.py")
    if args.extract:
        run("extract.py", "--retry-failed", "--workers", "4")
    run("bind_evidence.py", "data/extraction_api.json")
    run("mcp_check.py")
    if args.pricing:
        run("resolve_access.py")
    run("audit_sample.py")
    run("patterns.py")
    run("build_page.py")
    print("\nPipeline complete: index.html rebuilt from data/*.json")


if __name__ == "__main__":
    main()
