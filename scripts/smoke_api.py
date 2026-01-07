import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def get(path: str):
    url = BASE + path
    with urllib.request.urlopen(url) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def main():
    # 1) health
    status, data = get("/health")
    assert status == 200 and data.get("ok") is True
    print("✅ health ok")

    # 2) search (lexical / FTS)
    q = urllib.parse.quote("死锁")
    status, data = get(f"/search?q={q}&limit=5")
    assert status == 200 and isinstance(data, dict)
    assert data.get("mode") == "lexical"
    hits = data.get("items", [])
    assert isinstance(hits, list)
    print(f"✅ search ok ({len(hits)} hits)")

    if not hits:
        print("⚠️ No hits for query; stop here.")
        return

    chunk_id = hits[0]["chunk_id"]

    # 3) chunk detail
    status, chunk = get(f"/chunks/{chunk_id}")
    assert status == 200
    assert chunk["id"] == chunk_id
    assert "content" in chunk
    print("✅ chunk detail ok")

    # 4) related (cluster / topic-based)
    status, rel = get(f"/chunks/{chunk_id}/related?mode=cluster&k=5")
    assert status == 200 and isinstance(rel, list)
    if rel:
        item = rel[0]
        assert item.get("score") is None
        assert item.get("reason") == "same_topic"
    print("✅ related(cluster) ok")

    # 5) related (embedding / semantic)
    status, rel = get(f"/chunks/{chunk_id}/related?mode=embed&k=5")
    assert status == 200 and isinstance(rel, list)
    if rel:
        item = rel[0]
        assert isinstance(item.get("score"), (int, float))
        assert item.get("reason") == "semantic_similarity"
    print("✅ related(embed) ok")

    # 6) clusters list (allowed to be empty)
    status, clusters = get("/clusters?limit=5")
    assert status == 200 and isinstance(clusters, list)
    print(f"✅ clusters list ok ({len(clusters)} clusters)")

    print("\n🎉 All smoke tests passed.")


if __name__ == "__main__":
    main()
