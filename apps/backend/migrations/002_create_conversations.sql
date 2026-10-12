-- Chat history: one conversation = an ordered list of user questions and assistant answers.
-- Assistant messages keep a snapshot of their sources, so old answers stay readable
-- (with their citations) even after a book is re-indexed or deleted.

CREATE TABLE conversations (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title       text NOT NULL CHECK (length(btrim(title)) > 0),
    -- Book scope of the latest question; '{}' = every indexed book. No FK: books may be deleted.
    book_ids    uuid[] NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX conversations_updated_at_idx ON conversations (updated_at DESC);

CREATE TABLE conversation_messages (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Insertion order (timestamps can tie); messages are always read ORDER BY seq.
    seq              bigint GENERATED ALWAYS AS IDENTITY,
    conversation_id  uuid NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role             text NOT NULL CHECK (role IN ('user', 'assistant')),
    content          text NOT NULL DEFAULT '',
    -- assistant only: llm | insufficient_context | no_context | no_indexed_books | retrieval_only
    --                 | error (generation failed) | stopped (user cancelled; content = partial text)
    mode             text,
    grounded         boolean,
    sources          jsonb NOT NULL DEFAULT '[]',
    skipped_books    jsonb NOT NULL DEFAULT '[]',
    model            text,
    error            text,
    -- user only: the book scope the question was asked with ('{}' = all indexed books)
    book_ids         uuid[] NOT NULL DEFAULT '{}',
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX conversation_messages_conversation_seq_idx ON conversation_messages (conversation_id, seq);
