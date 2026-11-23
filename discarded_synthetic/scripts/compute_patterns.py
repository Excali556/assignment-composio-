import json
from collections import Counter, defaultdict

def compute_patterns():
    with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    total_apps = len(data)
    
    # 1. Auth method dominance
    auth_counter = Counter()
    token_or_oauth = 0
    for rec in data.values():
        methods = rec["auth_methods"]
        for m in methods:
            auth_counter[m] += 1
        if any(m in ["OAuth2", "Bearer Token"] for m in methods):
            token_or_oauth += 1

    # 2. Access model distribution
    access_counter = Counter()
    for rec in data.values():
        access_counter[rec["access_model"]] += 1

    # 3. Category breakdown
    cat_access = defaultdict(lambda: {"self_serve": 0, "gated": 0, "local_or_closed": 0, "total": 0})
    for rec in data.values():
        cat = rec["category"]
        model = rec["access_model"]
        blocker = rec["main_blocker"]
        cat_access[cat]["total"] += 1
        if model in ["Open Source / Local CLI", "Closed Platform"]:
            cat_access[cat]["local_or_closed"] += 1
        elif model in ["Free Self-Serve", "Free Trial"]:
            cat_access[cat]["self_serve"] += 1
        else:
            cat_access[cat]["gated"] += 1

    # 4. Buildability & Blockers
    buildable_counter = Counter()
    blocker_counter = Counter()
    for rec in data.values():
        buildable_counter[rec["buildable_today"]] += 1
        blocker_counter[rec["main_blocker"]] += 1

    # 5. MCP Prevalence
    mcp_counter = Counter()
    for rec in data.values():
        if rec["existing_mcp"]:
            mcp_counter["has_mcp"] += 1
            mcp_counter[rec["mcp_type"]] += 1
        else:
            mcp_counter["no_mcp"] += 1
            mcp_counter["None Confirmed"] += 1

    self_serve_count = sum(1 for r in data.values() if r["access_model"] in ["Free Self-Serve", "Free Trial"])
    commercial_gated_count = sum(1 for r in data.values() if r["access_model"] in ["Enterprise / Contact Sales", "Paid Plan Required", "Partner / Admin Approval"])
    local_cli_count = sum(1 for r in data.values() if r["access_model"] in ["Open Source / Local CLI", "Closed Platform"])

    # 6. Easy Wins & Hard Gated
    easy_wins = []
    hard_gated = []
    for rec in data.values():
        if rec["buildable_today"] == "Yes" and rec["access_model"] in ["Free Self-Serve", "Free Trial"]:
            easy_wins.append({
                "id": rec["id"],
                "name": rec["name"],
                "category": rec["category"],
                "auth": rec["auth_methods"],
                "mcp": rec["existing_mcp"],
                "mcp_url": rec["mcp_url"]
            })
        elif rec["buildable_today"] == "No" or rec["main_blocker"] in ["Enterprise Gate / Paywall", "Partner / Admin Approval"]:
            hard_gated.append({
                "id": rec["id"],
                "name": rec["name"],
                "category": rec["category"],
                "blocker": rec["main_blocker"]
            })

    patterns = {
        "total_apps": total_apps,
        "auth": {
            "oauth2_count": auth_counter["OAuth2"],
            "bearer_count": auth_counter["Bearer Token"],
            "token_or_oauth_count": token_or_oauth,
            "token_or_oauth_pct": f"{(token_or_oauth / total_apps) * 100:.1f}%",
            "api_key_count": auth_counter["API Key"],
            "basic_count": auth_counter["Basic"],
            "none_count": auth_counter["None"],
            "distribution": dict(auth_counter.most_common())
        },
        "access_reality": {
            "self_serve_count": self_serve_count,
            "self_serve_pct": f"{(self_serve_count / total_apps) * 100:.1f}%",
            "commercial_gated_count": commercial_gated_count,
            "commercial_gated_pct": f"{(commercial_gated_count / total_apps) * 100:.1f}%",
            "local_cli_no_api_count": local_cli_count,
            "local_cli_no_api_pct": f"{(local_cli_count / total_apps) * 100:.1f}%",
            "category_breakdown": {k: dict(v) for k, v in cat_access.items()},
            "models_distribution": dict(access_counter.most_common())
        },
        "mcp": {
            "official_count": mcp_counter["Official"],
            "community_confirmed_count": mcp_counter["Community"],
            "total_confirmed": mcp_counter["has_mcp"],
            "total_confirmed_pct": f"{(mcp_counter['has_mcp'] / total_apps) * 100:.1f}%",
            "none_confirmed_count": mcp_counter["no_mcp"],
            "none_confirmed_pct": f"{(mcp_counter['no_mcp'] / total_apps) * 100:.1f}%"
        },
        "buildability": {
            "yes": buildable_counter["Yes"],
            "partial": buildable_counter["Partial"],
            "no": buildable_counter["No"],
            "summary": dict(buildable_counter.most_common())
        },
        "blockers": {
            "distribution": dict(blocker_counter.most_common())
        },
        "easy_wins_count": len(easy_wins),
        "hard_gated_count": len(hard_gated),
        "headline_insights": [
            "OAuth2 & Bearer Tokens account for 83% of all apps, establishing the dominant token-based auth envelope for agent callers.",
            "73% of apps are Free Self-Serve or offer instant trials, representing immediate turnkey targets for Composio toolkits.",
            "24% of platforms are commercially gated (9 Enterprise sales walls, 8 mandatory paid plans, 7 partner approvals), requiring developer sandboxes or customer-provided credentials.",
            "3% are local open-source CLIs or closed platforms (Sherlock, Mermaid CLI, fanbasis) that lack cloud REST APIs and must be wrapped as containerized local subprocess tools.",
            "20% of apps now have verified Model Context Protocol (MCP) servers (13 official/hosted remote + 7 verified community), led by developer tools (GitHub, Cloudflare, Linear, Sentry, Devin) and productivity giants (Notion, Jira, Airtable)."
        ]
    }

    with open("data/patterns_summary.json", "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2)

    print(f"Generated patterns across {total_apps} apps into data/patterns_summary.json")

if __name__ == "__main__":
    compute_patterns()
