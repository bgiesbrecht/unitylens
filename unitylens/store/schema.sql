-- UnityLens metadata store DDL (SQLite)

CREATE TABLE IF NOT EXISTS sources (
    source_name   TEXT PRIMARY KEY,
    source_type   TEXT NOT NULL,
    host          TEXT NOT NULL DEFAULT '',
    last_crawl_at TEXT,                       -- ISO-8601 timestamp
    last_status   TEXT NOT NULL DEFAULT 'idle', -- idle | running | success | error
    last_error    TEXT NOT NULL DEFAULT '',
    config_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS catalogs (
    source_name   TEXT NOT NULL,
    catalog_name  TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    comment       TEXT NOT NULL DEFAULT '',
    owner         TEXT NOT NULL DEFAULT '',
    tags_json     TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_name, catalog_name)
);

CREATE TABLE IF NOT EXISTS schemas (
    source_name   TEXT NOT NULL,
    catalog_name  TEXT NOT NULL,
    schema_name   TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    comment       TEXT NOT NULL DEFAULT '',
    owner         TEXT NOT NULL DEFAULT '',
    tags_json     TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_name, catalog_name, schema_name)
);

CREATE TABLE IF NOT EXISTS tables (
    source_name   TEXT NOT NULL,
    catalog_name  TEXT NOT NULL,
    schema_name   TEXT NOT NULL,
    table_name    TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    table_type    TEXT NOT NULL DEFAULT 'TABLE',
    comment       TEXT NOT NULL DEFAULT '',
    owner         TEXT NOT NULL DEFAULT '',
    tags_json     TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_name, catalog_name, schema_name, table_name)
);

CREATE TABLE IF NOT EXISTS columns (
    source_name      TEXT NOT NULL,
    catalog_name     TEXT NOT NULL,
    schema_name      TEXT NOT NULL,
    table_name       TEXT NOT NULL,
    column_name      TEXT NOT NULL,
    full_name        TEXT NOT NULL,
    data_type        TEXT NOT NULL DEFAULT '',
    ordinal_position INTEGER NOT NULL DEFAULT 0,
    is_nullable      INTEGER NOT NULL DEFAULT 1,
    comment          TEXT NOT NULL DEFAULT '',
    tags_json        TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (source_name, catalog_name, schema_name, table_name, column_name)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_catalogs_source ON catalogs(source_name);
CREATE INDEX IF NOT EXISTS idx_schemas_source_catalog ON schemas(source_name, catalog_name);
CREATE INDEX IF NOT EXISTS idx_tables_source_catalog_schema ON tables(source_name, catalog_name, schema_name);
CREATE INDEX IF NOT EXISTS idx_columns_table ON columns(source_name, catalog_name, schema_name, table_name);

-- Full-text search support
CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
    full_name,
    object_type,
    comment,
    extra,
    tokenize='porter unicode61'
);
