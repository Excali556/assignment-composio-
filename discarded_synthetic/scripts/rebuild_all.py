import json
import os
from collections import Counter, defaultdict

# Verified live MCP links confirmed with HTTP 200
CONFIRMED_MCP = {
    "1": {"type": "Official", "url": "https://github.com/salesforcecli/mcp"},
    "5": {"type": "Official", "url": "https://github.com/twentyhq/twenty"},
    "27": {"type": "Community", "url": "https://github.com/chigwell/telegram-mcp"},
    "56": {"type": "Official", "url": "https://github.com/mendableai/firecrawl-mcp-server"},
    "58": {"type": "Community", "url": "https://github.com/Burnsedia/sherlock-mcp"},
    "61": {"type": "Official", "url": "https://github.com/github/github-mcp-server"},
    "65": {"type": "Community", "url": "https://github.com/supabase-community/mcp-server-supabase"},
    "66": {"type": "Community", "url": "https://github.com/neo4j-contrib/mcp-neo4j"},
    "71": {"type": "Community", "url": "https://github.com/suekou/mcp-notion-server"},
    "81": {"type": "Official", "url": "https://github.com/stripe/agent-toolkit"}
}

with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Clean MCP data: only keep verified URLs, rest are marked "None Confirmed"
for k, rec in data.items():
    if k in CONFIRMED_MCP:
        rec["existing_mcp"] = True
        rec["mcp_type"] = CONFIRMED_MCP[k]["type"]
        rec["mcp_url"] = CONFIRMED_MCP[k]["url"]
    else:
        rec["existing_mcp"] = False
        rec["mcp_type"] = "None Confirmed"
        rec["mcp_url"] = None

# Save cleaned dataset
with open("data/full_100_verified.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

# Dynamic counts computation
total_apps = len(data)

# Auth calculations
oauth2_count = sum(1 for r in data.values() if "OAuth2" in r["auth_methods"])
bearer_count = sum(1 for r in data.values() if "Bearer Token" in r["auth_methods"])
token_or_oauth_count = sum(1 for r in data.values() if ("OAuth2" in r["auth_methods"] or "Bearer Token" in r["auth_methods"]))
api_key_count = sum(1 for r in data.values() if "API Key" in r["auth_methods"])
basic_count = sum(1 for r in data.values() if "Basic" in r["auth_methods"])
none_auth_count = sum(1 for r in data.values() if "None" in r["auth_methods"])

# Single unified definition of Gated
# Gated: blocker != None OR access_model in [Enterprise, Paid]
gated_apps = []
self_serve_apps = []

category_counts = defaultdict(lambda: {"self_serve": 0, "gated": 0, "total": 0})

for r in data.values():
    cat = r["category"]
    category_counts[cat]["total"] += 1
    
    is_gated = (r["main_blocker"] != "None") or (r["access_model"] in ["Enterprise / Contact Sales", "Paid Plan Required"])
    if is_gated:
        gated_apps.append(r)
        category_counts[cat]["gated"] += 1
    else:
        self_serve_apps.append(r)
        category_counts[cat]["self_serve"] += 1

# MCP counts
official_mcp_count = sum(1 for r in data.values() if r.get("mcp_type") == "Official")
community_mcp_count = sum(1 for r in data.values() if r.get("mcp_type") == "Community")
total_confirmed_mcp = official_mcp_count + community_mcp_count
none_confirmed_mcp = total_apps - total_confirmed_mcp

# Buildability
buildable_yes = sum(1 for r in data.values() if r["buildable_today"] == "Yes")
buildable_partial = sum(1 for r in data.values() if r["buildable_today"] == "Partial")
buildable_no = sum(1 for r in data.values() if r["buildable_today"] == "No")

# Blockers breakdown
blockers_dist = Counter(r["main_blocker"] for r in data.values())

patterns_summary = {
    "total_apps": total_apps,
    "auth": {
        "oauth2_count": oauth2_count,
        "bearer_count": bearer_count,
        "token_or_oauth_count": token_or_oauth_count,
        "token_or_oauth_pct": f"{(token_or_oauth_count/total_apps)*100:.1f}%",
        "api_key_count": api_key_count,
        "basic_count": basic_count,
        "none_count": none_auth_count
    },
    "access_reality": {
        "self_serve_count": len(self_serve_apps),
        "self_serve_pct": f"{(len(self_serve_apps)/total_apps)*100:.1f}%",
        "gated_count": len(gated_apps),
        "gated_pct": f"{(len(gated_apps)/total_apps)*100:.1f}%",
        "category_breakdown": dict(category_counts)
    },
    "mcp": {
        "official_count": official_mcp_count,
        "community_confirmed_count": community_mcp_count,
        "total_confirmed": total_confirmed_mcp,
        "none_confirmed_count": none_confirmed_mcp
    },
    "buildability": {
        "yes": buildable_yes,
        "partial": buildable_partial,
        "no": buildable_no
    },
    "blockers": dict(blockers_dist)
}

with open("data/patterns_summary.json", "w", encoding="utf-8") as f:
    json.dump(patterns_summary, f, indent=2)

print("Patterns recalculated dynamically:")
print(f"Self-Serve: {len(self_serve_apps)}% | Gated: {len(gated_apps)}%")
print(f"OAuth2 or Bearer: {token_or_oauth_count}% (OAuth2 alone: {oauth2_count}%, Bearer alone: {bearer_count}%)")
print(f"Official MCP: {official_mcp_count} | Community Confirmed: {community_mcp_count} | None Confirmed: {none_confirmed_mcp}")
print("Category Gating Breakdown:")
for cat, d in category_counts.items():
    print(f"  - {cat:35}: {d['self_serve']} Self-Serve / {d['gated']} Gated")
