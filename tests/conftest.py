import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.kb.store.db import get_conn, init_db


@pytest.fixture()
def tmp_db(tmp_path: Path):
    db_path = tmp_path / "kb_test.sqlite"
    conn = get_conn(db_path)
    init_db(conn)
    yield conn
    conn.close()
