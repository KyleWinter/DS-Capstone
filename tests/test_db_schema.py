def test_schema_objects_exist(tmp_db):
    rows = tmp_db.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    names = {r["name"] for r in rows}

    assert "chunks" in names
    assert "files" in names
    assert "chunks_fts" in names


def test_fts_match_query_runs(tmp_db):
    # 空库也应该能执行 MATCH（返回 0）
    r = tmp_db.execute(
        "SELECT count(*) AS c FROM chunks_fts WHERE chunks_fts MATCH ?",
        ("test",),
    ).fetchone()
    assert int(r["c"]) == 0
