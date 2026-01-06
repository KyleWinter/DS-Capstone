-- Track3 KB schema (SQLite + FTS5)
PRAGMA foreign_keys = ON;

-- -------------------------
-- Files (optional but recommended)
-- -------------------------
CREATE TABLE IF NOT EXISTS files (
  id            INTEGER PRIMARY KEY,
  path          TEXT NOT NULL UNIQUE,
  mtime         REAL NOT NULL,
  size_bytes    INTEGER NOT NULL,
  sha256        TEXT,              -- optional: content hash
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);

-- -------------------------
-- Chunks
-- -------------------------
CREATE TABLE IF NOT EXISTS chunks (
  id            INTEGER PRIMARY KEY,
  file_path     TEXT NOT NULL,
  heading       TEXT,              -- best-effort; can be NULL in v1
  start_line    INTEGER,           -- optional
  end_line      INTEGER,           -- optional
  ordinal       INTEGER NOT NULL DEFAULT 0, -- chunk order within file
  content       TEXT NOT NULL,
  content_len   INTEGER NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_file_path ON chunks(file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_file_ordinal ON chunks(file_path, ordinal);

-- -------------------------
-- Full Text Search (FTS5)
-- Using external content table with triggers to keep in sync.
-- -------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
USING fts5(
  content,
  heading,
  file_path,
  content='chunks',
  content_rowid='id',
  tokenize='unicode61'
);

-- -------------------------
-- Triggers to sync FTS with chunks
-- -------------------------
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, content, heading, file_path)
  VALUES (new.id, new.content, COALESCE(new.heading, ''), new.file_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, heading, file_path)
  VALUES ('delete', old.id, old.content, COALESCE(old.heading, ''), old.file_path);
END;

CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, content, heading, file_path)
  VALUES ('delete', old.id, old.content, COALESCE(old.heading, ''), old.file_path);

  INSERT INTO chunks_fts(rowid, content, heading, file_path)
  VALUES (new.id, new.content, COALESCE(new.heading, ''), new.file_path);
END;

-- -------------------------
-- Embeddings (store vectors for chunks)
-- -------------------------
CREATE TABLE IF NOT EXISTS embeddings (
  chunk_id    INTEGER PRIMARY KEY,
  model       TEXT NOT NULL,
  dims        INTEGER NOT NULL,
  vec         BLOB NOT NULL,  -- float32 packed bytes
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
