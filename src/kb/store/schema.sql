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
  tokenize='unicode61 remove_diacritics 0'
);

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


-- -------------------------
-- Clusters
-- -------------------------
CREATE TABLE IF NOT EXISTS clusters (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  method     TEXT NOT NULL,              -- e.g. "kmeans"
  k          INTEGER,
  name       TEXT,
  summary    TEXT,
  size       INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cluster_members (
  cluster_id INTEGER NOT NULL,
  chunk_id   INTEGER NOT NULL,
  PRIMARY KEY (cluster_id, chunk_id),
  FOREIGN KEY(cluster_id) REFERENCES clusters(id) ON DELETE CASCADE,
  FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_chunk ON cluster_members(chunk_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_cluster ON cluster_members(cluster_id);

CREATE TABLE IF NOT EXISTS modules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  created_at REAL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS file_modules (
  file_path TEXT PRIMARY KEY,
  module_id INTEGER NOT NULL,
  score REAL DEFAULT 1.0,
  updated_at REAL DEFAULT (strftime('%s','now')),
  FOREIGN KEY(module_id) REFERENCES modules(id)
);

CREATE INDEX IF NOT EXISTS idx_file_modules_module_id ON file_modules(module_id);
