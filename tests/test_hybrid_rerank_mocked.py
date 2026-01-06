import types

from src.kb.store.repo import KBRepo, ChunkRow
from src.kb.search.lexical import fts_search
import src.kb.search.hybrid as hybrid_mod


def test_hybrid_uses_semantic_rerank_and_orders(tmp_db, monkeypatch):
    repo = KBRepo(tmp_db)
    repo.insert_chunks(
        [
            ChunkRow(file_path="a.md", heading="A", ordinal=0, content="transformer attention basics"),
            ChunkRow(file_path="b.md", heading="B", ordinal=0, content="transformer architecture overview"),
            ChunkRow(file_path="c.md", heading="C", ordinal=0, content="completely unrelated"),
        ]
    )
    repo.commit()

    lexical = fts_search(tmp_db, "transformer", limit=50)
    cand_ids = [h.chunk_id for h in lexical]
    assert len(cand_ids) >= 2

    def fake_semantic_rerank(conn, query, candidate_chunk_ids, model=None):
        ordered = sorted(candidate_chunk_ids)
        top = ordered[-1]
        rest = [x for x in ordered if x != top]
        hits = [types.SimpleNamespace(chunk_id=top, score=0.99)]
        hits += [types.SimpleNamespace(chunk_id=x, score=0.10) for x in rest]
        return hits

    monkeypatch.setattr(hybrid_mod, "semantic_rerank", fake_semantic_rerank)

    results = hybrid_mod.hybrid_search(tmp_db, "transformer", fts_k=50, top_k=2)
    assert len(results) == 2
    assert results[0].semantic_score >= results[1].semantic_score
