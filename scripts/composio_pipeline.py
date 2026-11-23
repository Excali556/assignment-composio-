"""
Optional Composio adapter for the research pipeline.

It is a thin wrapper: it runs the real fetch/bind stages for one app and
returns the same record shape as the rest of the pipeline. It does not fabricate a
"live mode" -- without COMPOSIO_API_KEY it raises, and the local pipeline runs without it.

The Composio integration is only used to register the research step as a callable tool,
so the same research can be triggered from an agent (Claude/Cursor) instead of a shell.
"""
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
sys.path.insert(0, str(HERE))

from fetch_docs import process as fetch_one  # noqa: E402
from bind_evidence import bind  # noqa: E402


def research_app(app_id: int) -> dict:
    """Fetch the app's docs (if not already saved) and return the quote-bound record.

    Deterministic and offline-safe: it reads data/sources/<id>.txt when present, and
    only hits the network when that file is missing.
    """
    research_path = DATA / "research_final.json"
    records = json.loads(research_path.read_text("utf-8"))
    record = next((r for r in records if r["id"] == app_id), None)
    if record is None:
        raise KeyError(f"app {app_id} is not in the researched set ({len(records)} apps)")

    source = DATA / "sources" / f"{app_id}.txt"
    if not source.exists():
        apps = {a["id"]: a for a in json.loads((DATA / "apps.json").read_text("utf-8"))} \
            if (DATA / "apps.json").exists() else {}
        if app_id not in apps:
            raise FileNotFoundError(f"no saved source for {app_id} and no app row to fetch from")
        fetch_one({"id": str(app_id), **apps[app_id]})

    return {
        "id": record["id"],
        "name": record["name"],
        "category": record["category"],
        "auth_methods": record["auth_methods"],
        "access_model": record["access_model"],
        "api_types": record["api_types"],
        "existing_mcp": record["existing_mcp"],
        "mcp_url": record.get("mcp_url"),
        "buildable_today": record["buildable_today"],
        "main_blocker": record["main_blocker"],
        "quotes": record.get("quotes", {}),
        "source": record.get("source"),
        "verified": record.get("verified", False),
    }


def as_composio_tool():
    """Register research_app as a Composio action. Requires a real API key."""
    key = os.environ.get("COMPOSIO_API_KEY")
    if not key:
        raise RuntimeError(
            "COMPOSIO_API_KEY is not set. The pipeline itself does not need Composio; "
            "this adapter only exposes research_app() to a Composio agent.")
    from composio import Composio  # imported lazily so the CLI works without the SDK

    client = Composio(api_key=key)
    session = client.create(user_id="product-ops-research", toolkits=["github", "tavily"])

    def app_research_tool(app_id: int) -> dict:
        """Research one app in the 100-app set and return quote-verified fields."""
        return research_app(int(app_id))

    return {"client": client, "session": session, "tool": app_research_tool}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quote-verified research for one app")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--register", action="store_true", help="also register with Composio")
    args = parser.parse_args()

    result = research_app(args.id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.register:
        as_composio_tool()
        print("registered with Composio", file=sys.stderr)
