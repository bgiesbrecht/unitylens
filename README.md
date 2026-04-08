# UnityLens

A cross-platform metadata catalog browser for Databricks Unity Catalog, Snowflake, and Oracle. UnityLens crawls your data sources on a schedule, stores the metadata in a local SQLite catalog with FTS5 full-text search, and serves a React UI for browsing, searching, and exporting a data-dictionary view of every table and column you have access to.

## Features

- Pluggable `DataSource` architecture — add a new source type by subclassing one base class.
- First-class connectors for **Databricks Unity Catalog** and **Oracle Database** (Snowflake stub).
- Incremental per-catalog crawling with real-time UI updates.
- Hierarchical browse (Source → Catalog → Schema → Table → Column) with deep-link auto-expansion.
- Flat "data dictionary" view with search and filters across all tables.
- Natural-language search powered by SQLite FTS5 with stop-word filtering.
- Background scheduler (APScheduler) for periodic crawls.
- **Database-backed authentication** with `admin` and `viewer` roles, HTTP-only session cookies, and an in-app User Management screen.
- **Per-source crawl logs** with structured `info`/`warn`/`error` entries surfaced in the Admin UI.
- **Sliding 7-day sessions** stored in SQLite — no JWT, no extra dependencies.

## Architecture

```
React + Vite (frontend/)  ->  FastAPI (unitylens/api/)  ->  SQLite store (unitylens/store/)
       |                              |
       v                              +--> auth (users, sessions, roles)
   AuthProvider                       |
   role-filtered nav                  +--> DataSource plugins
                                            (unitylens/sources/*)
```

The same SQLite database holds metadata (`sources`, `catalogs`, `schemas`, `tables`, `columns`, `search_index`) **and** auth state (`users`, `sessions`). Schema migrations run idempotently on startup.

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

All connector drivers (`databricks-sdk`, `oracledb`) are pinned in `requirements.txt`, so a single `pip install -r requirements.txt` covers every source.

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

Open <http://localhost:8000>. The first request shows a login screen.

### Default accounts

On first startup, if the `users` table is empty, UnityLens seeds two accounts and logs a warning:

| Username | Password   | Role   | Visible pages                                          |
|----------|------------|--------|--------------------------------------------------------|
| `admin`  | `adminpwd` | admin  | Dashboard, Sources, Data Dictionary, Browse, Search, Admin |
| `public` | `public`   | viewer | Data Dictionary, Browse, Search                        |

To set non-default passwords on the *first* run, export them before starting the server:

```bash
export UNITYLENS_ADMIN_PASSWORD="something-strong"
export UNITYLENS_VIEWER_PASSWORD="something-else"
```

After the initial seed, change passwords from the **Admin → User Management** screen, where admins can also create new users, reset passwords, and delete accounts.

> **Production note:** the session cookie is currently set with `Secure=False` so it works on plain `http://localhost`. Before deploying behind HTTPS, flip it to `Secure=True` in `unitylens/api/routes/auth.py`.

### Triggering a crawl

Sign in as `admin`, open the **Admin** page, and click **Crawl** for any source — or:

```bash
curl -c cookies.txt -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"adminpwd"}'

curl -b cookies.txt -X POST http://localhost:8000/api/admin/crawl/local_oracle
```

Tables appear in the Dashboard, Browse tree, and Data Dictionary as each catalog finishes. Per-source crawl logs are visible from the **Logs** button on the Admin page.

For production-style runs, use Gunicorn with the bundled config:

```bash
gunicorn unitylens.api.main:app -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py
```

## Configuring data sources

All sources are declared in [`unitylens/config/sources.yaml`](unitylens/config/sources.yaml). Values of the form `${VAR}` are interpolated from environment variables at load time, and `${VAR:-default}` is supported for local-dev fallbacks (production credentials should always come from real env vars). Secrets stay out of the repo.

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

UnityLens uses [`python-oracledb`](https://python-oracledb.readthedocs.io/) in **thin mode** — no Oracle Instant Client install required.

1. **Driver** is included in `requirements.txt` (`oracledb>=2.0.0`); no extra install step.

2. **Get connection details:**
   - **DSN** — Easy Connect (`host:port/service_name`, e.g. `localhost:1521/FREEPDB1`) or a full TNS descriptor.
   - **User** with read access to `ALL_USERS`, `ALL_TABLES`, `ALL_VIEWS`, `ALL_TAB_COLUMNS`, `ALL_TAB_COMMENTS`, and `ALL_COL_COMMENTS`. `SELECT_CATALOG_ROLE` is sufficient.
   - **Password**.

3. **Per-source env vars** — namespace by source name so you can run multiple Oracle databases side by side:

   ```bash
   export ORACLE_LOCAL_DSN="localhost:1521/FREEPDB1"
   export ORACLE_LOCAL_USER="system"
   export ORACLE_LOCAL_PASSWORD="••••••••"
   ```

4. **Add the source** in `sources.yaml`:

   ```yaml
   sources:
     - name: local_oracle
       type: oracle
       dsn: ${ORACLE_LOCAL_DSN:-localhost:1521/FREEPDB1}
       user: ${ORACLE_LOCAL_USER:-system}
       password: ${ORACLE_LOCAL_PASSWORD:-password123}
       include_views: true
       schema_filter: [GEO, SOLAR]   # optional; empty/omitted = all non-system schemas
   ```

5. **Sign in as `admin`** and trigger a crawl from the Admin page (or `POST /api/admin/crawl/local_oracle`).

**Mapping:** Oracle has no "catalog" concept, so the connector surfaces a single synthetic catalog named after the service (parsed from the DSN, e.g. `FREEPDB1`). Oracle schemas (users) become UnityLens schemas. System schemas (`SYS`, `SYSTEM`, `XDB`, etc.) are skipped by default — set `include_system_schemas: true` to include them.

**Comments are first-class:** the connector pulls `ALL_TAB_COMMENTS` and `ALL_COL_COMMENTS` and stores them as table/column descriptions. Edit comments with native Oracle DDL (`COMMENT ON TABLE …`, `COMMENT ON COLUMN …`) and re-crawl to refresh.

### Quick local Oracle for testing

The official `gvenzl/oracle-free` image is the fastest way to get a local Oracle database for trying UnityLens:

```bash
docker run -d --name oracle-free \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=password123 \
  gvenzl/oracle-free
```

It exposes service `FREEPDB1` on port 1521; the defaults in the example `local_oracle` block above match it out of the box.

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
  __init__.py     __version__ — single source of truth (exposed via /api/version)
  api/
    main.py       FastAPI app, lifespan, CORS, static mount
    routes/       browse, search, admin (admin-only), auth (login, users)
  auth/           pbkdf2 password hashing, sessions, role-based deps
  config/         sources.yaml + settings loader (${VAR:-default} interpolation)
  crawler/        Crawl orchestrator + APScheduler job (per-source structured logs)
  sources/        DataSource plugins (databricks, oracle, snowflake stub)
  store/          SQLite schema, FTS5 search, CRUD, idempotent migrations
  static/         Built frontend (generated)
frontend/
  src/
    auth/         AuthProvider, AuthGate, useAuth
    pages/        Dashboard, Sources, Browse, Dictionary, Search, Admin, Login
    components/   Sidebar (role-filtered), DataTable, etc.
    api/client.ts Cookie-aware fetch + typed API helpers
requirements.txt
```

## API surface

| Endpoint                                | Auth          | Notes                                |
|-----------------------------------------|---------------|--------------------------------------|
| `GET  /api/health`                      | public        | liveness, returns version            |
| `GET  /api/version`                     | public        | `{ "version": "x.y.z" }`             |
| `POST /api/auth/login`                  | public        | sets HTTP-only session cookie        |
| `POST /api/auth/logout`                 | authenticated | clears cookie + invalidates sessions |
| `GET  /api/auth/me`                     | authenticated | current user                         |
| `POST /api/auth/password`               | authenticated | change own password                  |
| `GET  /api/auth/users`                  | admin         | list users                           |
| `POST /api/auth/users`                  | admin         | create user                          |
| `POST /api/auth/users/{u}/password`     | admin         | reset another user's password        |
| `DELETE /api/auth/users/{u}`            | admin         | delete user (self-delete blocked)    |
| `GET  /api/sources`                     | authenticated | merged YAML + DB view                |
| `GET  /api/browse/...`, `/api/dictionary`, `/api/search`, `/api/stats` | authenticated | metadata browsing |
| `POST /api/admin/crawl[/{source}]`      | admin         | trigger background crawl             |
| `GET  /api/admin/sources/{name}/status` | admin         | per-source status + structured log   |
