# UnityLens

A cross-platform metadata catalog browser for Databricks Unity Catalog, Snowflake, and Oracle. UnityLens crawls your data sources on a schedule, stores the metadata in a local SQLite catalog with FTS5 full-text search, and serves a React UI for browsing, searching, and exporting a data-dictionary view of every table and column you have access to.

## Features

- Pluggable `DataSource` architecture — add a new source type by subclassing one base class.
- Incremental per-catalog crawling with real-time UI updates.
- Hierarchical browse (Source → Catalog → Schema → Table → Column) with deep-link auto-expansion.
- Flat "data dictionary" view with search and filters across all tables.
- Natural-language search powered by SQLite FTS5 with stop-word filtering.
- Background scheduler (APScheduler) for periodic crawls.

## Architecture

```
React + Vite (frontend/)  ->  FastAPI (unitylens/api/)  ->  SQLite store (unitylens/store/)
                                         |
                                         v
                              DataSource plugins
                              (unitylens/sources/*)
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm (only needed to build the frontend)
- Git

### 1. Clone and create a virtual environment

```bash
git clone git@github-personal:bgiesbrecht/unitylens.git
cd unitylens

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Add per-source drivers as needed, e.g. `pip install oracledb` for Oracle.

### 3. Build the frontend

The FastAPI app serves the compiled React bundle from `unitylens/static/`. Build it once (and rebuild after any UI change):

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Configure data sources

Edit [`unitylens/config/sources.yaml`](unitylens/config/sources.yaml) and export the credentials referenced by the `${VAR}` placeholders. See the [Databricks](#databricks-unity-catalog) and [Oracle](#oracle-database) sections below for details.

The simplest pattern is a local `.env` file (already in `.gitignore`):

```bash
cat > .env <<'EOF'
DATABRICKS_HOST=https://adb-xxxx.cloud.databricks.com
DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXX
DATABRICKS_WAREHOUSE_ID=abcd1234efgh5678
EOF

set -a && source .env && set +a
```

## Running the app

```bash
python -m uvicorn unitylens.api.main:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. From the **Admin** page click **Run crawl** (or `curl -X POST http://localhost:8000/api/admin/crawl`) to populate the catalog. Tables will appear in the dashboard, browse tree, and dictionary as each catalog finishes.

For production-style runs, use Gunicorn with the bundled config:

```bash
gunicorn unitylens.api.main:app -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py
```

## Configuring data sources

All sources are declared in [`unitylens/config/sources.yaml`](unitylens/config/sources.yaml). Values of the form `${VAR}` are interpolated from environment variables at load time, so secrets stay out of the repo.

### Databricks Unity Catalog

UnityLens uses the Databricks SDK with your personal access token, so it sees exactly the catalogs/schemas/tables your user has permission to read.

1. **Create a PAT** in your workspace: *User Settings → Developer → Access tokens → Generate new token*.
2. **Grab the workspace host** (e.g. `https://adb-1234567890.12.azuredatabricks.net`).
3. **(Optional) Warehouse ID** — only needed if you want to fall back to the SQL Statement API. Copy it from *SQL Warehouses → \<your warehouse\> → Connection details*.
4. **Export env vars:**

   ```bash
   export DATABRICKS_HOST="https://adb-xxxx.cloud.databricks.com"
   export DATABRICKS_TOKEN="dapiXXXXXXXXXXXXXXXX"
   export DATABRICKS_WAREHOUSE_ID="abcd1234efgh5678"   # optional
   ```

5. **Confirm the entry** in `sources.yaml`:

   ```yaml
   sources:
     - name: prod_databricks
       type: databricks
       host: ${DATABRICKS_HOST}
       token: ${DATABRICKS_TOKEN}
       warehouse_id: ${DATABRICKS_WAREHOUSE_ID}
       catalog_filter: []        # empty = crawl every catalog the PAT can see
       deny_tags: {}
       allow_tags: {}
   ```

   To restrict the crawl to specific catalogs, list them: `catalog_filter: [main, analytics, bg]`.

6. Restart the server and kick off a crawl. You should see catalogs populate incrementally on the dashboard.

**Permissions note:** the SDK path uses your PAT directly, so you only need `USE CATALOG` / `USE SCHEMA` / `SELECT` (or at minimum `BROWSE`) on the objects you want visible. Objects your token cannot see are silently skipped.

### Oracle Database

> **Status:** the Oracle source is a structural stub — the crawl interface is wired up but the connector logic is not yet implemented. The steps below describe the intended setup.

1. **Install the driver:**

   ```bash
   pip install oracledb
   ```

2. **Get connection details** from your DBA. You'll need:
   - **DSN** — either an Easy Connect string (`host:port/service_name`, e.g. `db01.example.com:1521/ORCLPDB1`) or a full TNS descriptor.
   - **User** with `SELECT` on `ALL_USERS`, `ALL_TABLES`, and `ALL_TAB_COLUMNS` (read-only is enough; `SELECT_CATALOG_ROLE` covers it).
   - **Password**.

3. **Export env vars:**

   ```bash
   export ORACLE_DSN="db01.example.com:1521/ORCLPDB1"
   export ORACLE_USER="unitylens_reader"
   export ORACLE_PASSWORD="••••••••"
   ```

4. **Enable the source** in `sources.yaml`:

   ```yaml
   sources:
     - name: prod_oracle
       type: oracle
       dsn: ${ORACLE_DSN}
       user: ${ORACLE_USER}
       password: ${ORACLE_PASSWORD}
   ```

5. Restart and trigger a crawl. Oracle has no "catalog" concept in the Unity Catalog sense, so the database/service name maps to a single synthetic catalog and Oracle schemas (users) map to UnityLens schemas.

## Development

```bash
# Frontend dev server with hot reload
cd frontend && npm run dev

# Backend with auto-reload
python -m uvicorn unitylens.api.main:app --reload
```

Rebuild the bundled frontend before committing UI changes:

```bash
cd frontend && npm run build
```

## Project layout

```
unitylens/
  api/            FastAPI routes (browse, admin, dictionary, stats)
  config/         sources.yaml + settings loader
  crawler/        Crawl orchestrator + APScheduler job
  sources/        DataSource plugins (databricks, snowflake, oracle)
  store/          SQLite schema, FTS5 search, CRUD
  static/         Built frontend (generated)
frontend/         React + TypeScript + Vite UI
requirements.txt
```
