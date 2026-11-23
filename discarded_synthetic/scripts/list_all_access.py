import json

with open('data/full_100_verified.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for k, v in data.items():
    print(f"ID {v['id']:2d}: {v['name']:20s} | {v['category'][:20]:20s} | Access: {v['access_model']:25s} | Blocker: {v['main_blocker']:25s}")
