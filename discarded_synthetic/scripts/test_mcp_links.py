import urllib.request
import urllib.error

mcp_candidates = {
    "GitHub": ("Official", "https://github.com/github/github-mcp-server"),
    "Stripe": ("Official", "https://github.com/stripe/agent-toolkit"),
    "Linear": ("Official", "https://mcp.linear.app/mcp"),
    "Sentry": ("Official", "https://mcp.sentry.dev"),
    "Cloudflare": ("Official", "https://github.com/cloudflare/mcp-server-cloudflare"),
    "Docker": ("Official", "https://github.com/docker/mcp-server"),
    "Notion": ("Official", "https://developers.notion.com"), # or https://github.com/suekou/mcp-notion-server
    "Devin": ("Official", "https://docs.devin.ai/integrations/mcp"),
    "Slack": ("Official", "https://github.com/modelcontextprotocol/servers"),
    "Salesforce": ("Official", "https://github.com/salesforcecli/mcp"),
    "Twenty": ("Official", "https://github.com/twentyhq/twenty"),
    "Firecrawl": ("Official", "https://github.com/mendableai/firecrawl-mcp-server"),
    "Supabase": ("Community", "https://github.com/supabase-community/mcp-server-supabase"),
    "Neo4j": ("Community", "https://github.com/neo4j-contrib/mcp-neo4j"),
    "Telegram": ("Community", "https://github.com/chigwell/telegram-mcp"),
    "Sherlock": ("Community", "https://github.com/Burnsedia/sherlock-mcp"),
    "Tavily": ("Official", "https://github.com/tavily-ai/tavily-mcp"),
    "Airtable": ("Community", "https://github.com/domdomegg/airtable-mcp"),
    "Jira": ("Community", "https://github.com/soopwr/jira-mcp"),
}

for app, (mtype, url) in mcp_candidates.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"OK ({resp.status}): {app} -> {url}")
    except Exception as e:
        print(f"FAIL ({e}): {app} -> {url}")
