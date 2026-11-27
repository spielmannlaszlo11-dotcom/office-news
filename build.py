"""One-shot feed refresh for GitHub Pages; no persistent web server required."""
import json
from pathlib import Path
import server

def build():
    server.cycle()
    root = Path(__file__).resolve().parent / 'site'
    payload = server.STATE
    health = {'mode':payload['mode'],'stale':payload['stale'],'items':len(payload['items']), 'updated':payload['updated'], 'feeds':list(server.HEALTH.values())}
    for name,data in [('news.json',payload),('health.json',health)]:
        (root/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    print(f"Published {health['items']} stories; mode={health['mode']}; stale={health['stale']}")

if __name__ == '__main__': build()
