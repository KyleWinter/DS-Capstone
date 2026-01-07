import json
import urllib.parse
import urllib.request
from typing import List, Dict

BASE = "http://127.0.0.1:8000/api"


def get(path: str):
    url = BASE + path
    with urllib.request.urlopen(url) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def print_divider(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_hit(i: int, hit: Dict):
    print(f"{i:02d}. chunk_id = {hit['chunk_id']}")
    print(f"    file    = {hit['file_path']}")
    if hit.get("heading"):
        print(f"    heading = {hit['heading']}")
    print(f"    preview = {hit['preview']}")
    print()


def run_search(query: str, limit: int = 5):
    q = urllib.parse.quote(query)
    status, data = get(f"/search?q={q}&limit={limit}")

    print_divider(f"SEARCH: {query!r}")

    if status != 200:
        print(f"❌ HTTP {status}")
        return

    # New API shape: {"mode": "...", "total": ..., "items": [...]}
    print(f"mode  : {data.get('mode')}")
    print(f"total : {data.get('total')}")
    hits: List[Dict] = data.get("items", [])

    print(f"hits  : {len(hits)}\n")

    if not hits:
        print("(no results)")
        return

    for i, hit in enumerate(hits, start=1):
        print_hit(i, hit)


def main():
    queries = [
        "死锁",
        "线程池",
        "RPC",
        "共识",
    ]
    for q in queries:
        run_search(q, limit=5)


if __name__ == "__main__":
    main()
