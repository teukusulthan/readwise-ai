-- Self-healing indexing: how many times the worker has claimed a book (queued -> processing).
-- Startup recovery re-queues interrupted jobs while this is below BE_INGESTION_MAX_ATTEMPTS;
-- POST /book/reindex resets it to 0.

ALTER TABLE books ADD COLUMN ingestion_attempts integer NOT NULL DEFAULT 0
    CHECK (ingestion_attempts >= 0);
