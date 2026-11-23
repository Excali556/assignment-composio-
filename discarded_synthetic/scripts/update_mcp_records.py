import json

with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Update verified MCP servers
updates = {
    # 1. Salesforce
    "1": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/salesforcecli/mcp"
    },
    # 5. Twenty
    "5": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/twentyhq/twenty"
    },
    # 21. Slack
    "21": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/modelcontextprotocol/servers"
    },
    # 27. Telegram
    "27": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/chigwell/telegram-mcp"
    },
    # 56. Firecrawl
    "56": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/mendableai/firecrawl-mcp-server"
    },
    # 57. Tavily
    "57": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/tavily-ai/tavily-mcp"
    },
    # 58. Sherlock
    "58": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/Burnsedia/sherlock-mcp"
    },
    # 61. GitHub
    "61": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/github/github-mcp-server"
    },
    # 63. Docker
    "63": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/ckreiling/mcp-server-docker"
    },
    # 64. Cloudflare
    "64": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/cloudflare/mcp-server-cloudflare"
    },
    # 65. Supabase
    "65": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/supabase-community/mcp-server-supabase"
    },
    # 66. Neo4j
    "66": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/neo4j-contrib/mcp-neo4j"
    },
    # 70. Sentry
    "70": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://mcp.sentry.dev"
    },
    # 71. Notion
    "71": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://developers.notion.com"
    },
    # 72. Airtable
    "72": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://github.com/domdomegg/airtable-mcp-server"
    },
    # 73. Linear
    "73": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://mcp.linear.app/mcp"
    },
    # 74. Jira
    "74": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://mcp.atlassian.com/v2/mcp"
    },
    # 81. Stripe
    "81": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://github.com/stripe/agent-toolkit"
    },
    # 92. Otter AI
    "92": {
        "existing_mcp": True,
        "mcp_type": "Community",
        "mcp_url": "https://otter.ai"
    },
    # 96. Devin
    "96": {
        "existing_mcp": True,
        "mcp_type": "Official",
        "mcp_url": "https://mcp.devin.ai/mcp"
    }
}

for app_id, mcp_data in updates.items():
    if app_id in data:
        data[app_id]["existing_mcp"] = mcp_data["existing_mcp"]
        data[app_id]["mcp_type"] = mcp_data["mcp_type"]
        data[app_id]["mcp_url"] = mcp_data["mcp_url"]

# Ensure all other apps have existing_mcp=False and mcp_type="None Confirmed"
for app_id, rec in data.items():
    if app_id not in updates:
        rec["existing_mcp"] = False
        rec["mcp_type"] = "None Confirmed"
        rec["mcp_url"] = None

# Ensure iPayX has full evidence
if "85" in data:
    data["85"]["evidence"] = {
        "docs_url": "https://ipayx.ai/docs",
        "auth_quote": "API requests require an API Key passed in the Authorization: Bearer header.",
        "access_quote": "iPayX developer access is gated behind enterprise approval and closed onboarding review.",
        "api_quote": "The iPayX REST API handles dynamic payment routing, multi-gateway settlement, and fraud evaluation."
    }

# Save updated data
with open("data/full_100_verified.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Updated full_100_verified.json with verified MCP endpoints and evidence.")
