import struct
from src.kb.store.repo import KBRepo, ChunkRow


def pack_f32(vec):
    return struct.pack("<%sf" % len(vec), *vec)


def test_embeddings_blob_length_matches_dims(tmp_db):
    repo = KBRepo(tmp_db)
    repo.insert_chunks([ChunkRow(file_path="x.md", heading=None, ordinal=0, content="some content")])
    repo.commit()

    chunk_id = tmp_db.execute("SELECT id FROM chunks LIMIT 1").fetchone()["id"]

    dims = 6
    blob = pack_f32([0.1, 0.0, -0.2, 0.3, 0.4, 0.5])

    tmp_db.execute(
        """
        INSERT OR REPLACE INTO embeddings(chunk_id, model, dims, vec)
        VALUES (?, ?, ?, ?)
        """,
        (chunk_id, "fake-model", dims, blob),
    )
    tmp_db.commit()

    r = tmp_db.execute(
        "SELECT dims, length(vec) AS nbytes FROM embeddings WHERE chunk_id=?",
        (chunk_id,),
    ).fetchone()

    assert int(r["dims"]) == dims
    assert int(r["nbytes"]) == dims * 4
