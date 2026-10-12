-- Per-user chat history: the principal that owns a conversation (auth/principal.py).
--   a user id (the JWT `user_id` claim) while BE_JWT_ACTIVE=true
--   'local'                             while BE_JWT_ACTIVE=false (no login)
--   NULL                                rows created before this migration ("legacy"): visible to
--                                       'local' only, invisible to real users once JWT is on.

ALTER TABLE conversations ADD COLUMN owner_id text;

-- The history list: one owner's conversations, most recently active first.
CREATE INDEX conversations_owner_updated_at_idx ON conversations (owner_id, updated_at DESC);
