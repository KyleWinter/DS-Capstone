import json
import urllib.parse
import urllib.request
from typing import Dict, List

BASE = "http://127.0.0.1:8000/api"


# -------------------------
# HTTP helper
# -------------------------

def get(path: str):
    url = BASE + path
    with urllib.request.urlopen(url) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def divider(title: str):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


# -------------------------
# Pretty printers
# -------------------------

def print_chunk_hit(i: int, hit: Dict):
    print(f"{i:02d}. chunk_id = {hit['chunk_id']}")
    print(f"    file    = {hit['file_path']}")
    if hit.get("heading"):
        print(f"    heading = {hit['heading']}")
    print(f"    preview = {hit['preview']}")
    print()


def print_related_chunk(i: int, item: Dict):
    print(f"{i:02d}. chunk_id = {item['chunk_id']}  score={item.get('score')}")
    print(f"    file    = {item['file_path']}")
    if item.get("heading"):
        print(f"    heading = {item['heading']}")
    print(f"    reason  = {item['reason']}")
    print(f"    preview = {item['preview']}")
    print()


def print_related_note(i: int, note: Dict):
    print(f"{i:02d}. file_path      = {note['file_path']}")
    print(f"    score          = {note['score']}")
    print(f"    reason         = {note['reason']}")
    print(f"    matched_chunks = {note['matched_chunks']}")
    print(f"    top_chunk_ids  = {note['top_chunk_ids']}")
    print()


# -------------------------
# Test flow
# -------------------------

def main():
    query = "死锁"

    # 1) SEARCH
    divider(f"1) SEARCH: {query!r}")
    q = urllib.parse.quote(query)
    _, search = get(f"/search?q={q}&limit=5")

    items: List[Dict] = search["items"]
    print(f"mode  : {search['mode']}")
    print(f"hits  : {len(items)}\n")

    if not items:
        print("❌ No search results, stop.")
        return

    for i, hit in enumerate(items, start=1):
        print_chunk_hit(i, hit)

    # pick first result
    chunk_id = items[0]["chunk_id"]

    # 2) CHUNK DETAIL
    divider(f"2) CHUNK DETAIL: chunk_id={chunk_id}")
    _, chunk = get(f"/chunks/{chunk_id}")

    print(f"file    = {chunk['file_path']}")
    print(f"heading = {chunk['heading']}")
    print(f"ordinal = {chunk['ordinal']}")
    print("\n--- content (first 300 chars) ---")
    print(chunk["content"][:300])
    print("...")

    # 3) RELATED CHUNKS
    divider("3) RELATED CHUNKS (chunk-level)")

    for mode in ["cluster", "embed"]:
        print(f"\n--- mode = {mode} ---")
        _, related = get(f"/chunks/{chunk_id}/related?mode={mode}&k=5")

        if not related:
            print("(no related chunks)")
            continue

        for i, item in enumerate(related, start=1):
            print_related_chunk(i, item)

    # 4) RELATED NOTES
    divider("4) RELATED NOTES (note-level)")

    for mode in ["cluster", "embed"]:
        print(f"\n--- mode = {mode} ---")
        _, notes = get(f"/chunks/{chunk_id}/related-notes?mode={mode}&k=5")

        items = notes["items"]
        if not items:
            print("(no related notes)")
            continue

        for i, note in enumerate(items, start=1):
            print_related_note(i, note)

    divider("DONE")


if __name__ == "__main__":
    main()
