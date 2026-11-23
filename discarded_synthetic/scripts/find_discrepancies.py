import json

with open('data/full_100_verified.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("--- DISCREPANCY BETWEEN ACCESS MODEL AND MAIN BLOCKER ---")
for k, v in data.items():
    is_self = v['access_model'] in ['Free Self-Serve', 'Free Trial']
    has_no_blocker = v['main_blocker'] == 'None'
    if is_self != has_no_blocker:
        print(f"ID {v['id']:2d}: {v['name']:20s} | Category: {v['category']:30s} | Access: {v['access_model']:25s} | Blocker: {v['main_blocker']:25s}")
