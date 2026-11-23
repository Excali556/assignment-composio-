import json

with open('data/full_100_verified.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('--- APPS WITH EXISTING MCP == TRUE ---')
true_count = 0
for k, v in data.items():
    if v.get('existing_mcp'):
        true_count += 1
        print(f"{v['id']}. {v['name']} ({v.get('mcp_type')}): {v.get('mcp_url')}")
print(f"Total marked true: {true_count}")

print('\n--- CHECKING TARGET VENDORS ---')
targets = [
    'GitHub', 'Stripe', 'Notion', 'Linear', 'Sentry', 'Cloudflare', 
    'Otter AI', 'Devin', 'Slack', 'PostgreSQL', 'Supabase', 'Airtable', 
    'Docker', 'GitLab', 'Discord', 'Telegram', 'Jira', 'Confluence', 
    'Asana', 'Zendesk', 'Intercom', 'Twilio', 'Sherlock', 'Mermaid CLI', 'iPayX'
]
for k, v in data.items():
    name = v['name']
    if any(t.lower() == name.lower() for t in targets):
        print(f"ID {v['id']}: {name} | MCP: {v.get('existing_mcp')} | Type: {v.get('mcp_type')} | URL: {v.get('mcp_url')} | Access: {v.get('access_model')} | Blocker: {v.get('main_blocker')}")
