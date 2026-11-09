-- Runs once when the database volume is first created.
-- pgvector is enabled now; vector columns are added only after the embedding model and dimensions are fixed (PRD 10.4).
CREATE EXTENSION IF NOT EXISTS vector;
