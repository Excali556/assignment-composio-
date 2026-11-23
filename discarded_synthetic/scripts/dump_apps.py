import csv
import json

with open("apps.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    apps = list(reader)

with open("data/full_100_verified.json", "r", encoding="utf-8") as f:
    verified = json.load(f)

for row in apps:
    app_id = row['id']
    v = verified.get(str(app_id), {})
    print(f"ID {app_id:2s} | Cat: {row['category'][:22]:22s} | App: {row['name'][:20]:20s} | MCP: {str(v.get('existing_mcp')):5s} ({v.get('mcp_type', 'none')}) | Access: {v.get('access_model')} | Blocker: {v.get('main_blocker')}")
