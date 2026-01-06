from src.kb.store.repo import KBRepo, ChunkRow


def test_repo_insert_triggers_fts(tmp_db):
    repo = KBRepo(tmp_db)

    inserted = repo.insert_chunks(
        [
            ChunkRow(file_path="a.md", heading="H", ordinal=0, content="hello transformer attention"),
            ChunkRow(file_path="b.md", heading=None, ordinal=0, content="nothing related"),
        ]
    )
    repo.commit()
    assert inserted == 2

    # FTS should find transformer
    rows = tmp_db.execute(
        """
        SELECT c.id
        FROM chunks_fts
        JOIN chunks c ON c.id = chunks_fts.rowid
        WHERE chunks_fts MATCH ?
        """,
        ("transformer",),
    ).fetchall()
    assert len(rows) == 1
