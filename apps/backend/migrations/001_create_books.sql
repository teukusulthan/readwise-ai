-- Books: catalog metadata + full-text ingestion status.
-- ingestion_status = 'none' means "metadata only" (not searchable by RAG).

CREATE TABLE books (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- catalog metadata
    title             text NOT NULL CHECK (length(btrim(title)) > 0),
    authors           text[] NOT NULL DEFAULT '{}',
    description       text,
    isbn              text,
    cover_url         text,
    publisher         text,
    published_year    integer CHECK (published_year BETWEEN 0 AND 3000),
    language          text,
    subjects          text[] NOT NULL DEFAULT '{}',
    metadata_source   text NOT NULL DEFAULT 'manual'
                      CHECK (metadata_source IN ('manual', 'openlibrary', 'upload')),
    external_id       text,

    -- uploaded document
    file_name         text,
    file_path         text,
    file_sha256       text,
    file_size_bytes   bigint,
    page_count        integer,

    -- full-text ingestion
    ingestion_status  text NOT NULL DEFAULT 'none'
                      CHECK (ingestion_status IN ('none', 'queued', 'processing', 'indexed', 'failed')),
    ingestion_error   text,
    chunk_count       integer NOT NULL DEFAULT 0,
    embedding_model   text,
    indexed_at        timestamptz,

    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

-- Duplicate protection: one book per ISBN, per uploaded file, per external record.
CREATE UNIQUE INDEX books_isbn_key        ON books (isbn)        WHERE isbn IS NOT NULL;
CREATE UNIQUE INDEX books_file_sha256_key ON books (file_sha256) WHERE file_sha256 IS NOT NULL;
CREATE UNIQUE INDEX books_external_key    ON books (metadata_source, external_id) WHERE external_id IS NOT NULL;

CREATE INDEX books_ingestion_status_idx ON books (ingestion_status);
CREATE INDEX books_created_at_idx       ON books (created_at DESC);
