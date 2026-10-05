-- ============================================================
--  Gemini Notebook — initial database schema
--  Runs once when the Docker Postgres container first starts.
-- ============================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- for fast text search later

-- ─── Users ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    username    VARCHAR(100) UNIQUE NOT NULL,
    full_name   VARCHAR(255),
    hashed_password TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Notebooks ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notebooks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL DEFAULT 'Untitled Notebook',
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Sources (uploaded files / URLs per notebook) ──────────
CREATE TABLE IF NOT EXISTS sources (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id     UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    source_type     VARCHAR(50) NOT NULL CHECK (source_type IN ('pdf', 'txt', 'md', 'markdown', 'docx', 'url', 'youtube', 'pasted_text')),
    title           VARCHAR(500),
    file_path       TEXT,          -- local storage path if uploaded file
    raw_url         TEXT,          -- original URL if web source
    content_text    TEXT,          -- extracted plain text
    token_count     INTEGER,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'error', 'failed')),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Chat Messages ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    notebook_id     UUID NOT NULL REFERENCES notebooks(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,
    source_refs     JSONB,         -- which source chunks were cited
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Refresh tokens ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Indexes ───────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_notebooks_user_id    ON notebooks(user_id);
CREATE INDEX IF NOT EXISTS idx_sources_notebook_id  ON sources(notebook_id);
CREATE INDEX IF NOT EXISTS idx_chat_notebook_id     ON chat_messages(notebook_id);
CREATE INDEX IF NOT EXISTS idx_refresh_user_id      ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email          ON users(email);

-- ─── Seed: demo user (password = "demo1234") ───────────────
-- bcrypt hash of "demo1234" — replace in production
INSERT INTO users (email, username, full_name, hashed_password, is_active, is_verified)
VALUES (
    'demo@gemini.local',
    'demo',
    'Demo User',
    '$2b$12$KIX/L3LoaRIXCQPX0q3pWuSxphcUGFqsm7kQzaxwkHKkJHfzHYi2C',
    TRUE,
    TRUE
)
ON CONFLICT (email) DO NOTHING;
