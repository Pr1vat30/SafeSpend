# SafeSpend

SafeSpend is a preventive decision-support tool. It estimates how much you can spend today
(the **Safe-to-Spend** figure) without putting upcoming expenses at risk.

This repository holds the **backend API** (Python, FastAPI, PostgreSQL 18), the **frontend**
(Next.js, React, TypeScript) and the project's documentation. Everything is
**cross-platform** and runs on **Windows**, **macOS** and **Linux**.

> [!NOTE]
> Both apps are scaffolds for now. They contain the architecture, the tooling and empty
> template files. The business features aren't built yet.

---

## Repository layout

```
SafeSpend/
├── .gitattributes           Enforces consistent LF line endings across Windows and Unix
├── .env.example             Docker Compose settings (ports, database credentials)
├── docker-compose.yml       PostgreSQL 18 + schema init + backend + frontend + backup tools
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── main.py          App factory: middleware, exception handlers, routers
│   │   ├── api/
│   │   │   ├── router.py    Puts every module's router under /api/v1
│   │   │   ├── controller/  HTTP layer: routes only, no business logic
│   │   │   └── dto/         Pydantic request/response schemas (+ common APIResponse)
│   │   ├── service/         Business logic, raises domain exceptions
│   │   ├── dao/             Data access: SQLAlchemy queries only
│   │   ├── models/          SQLAlchemy ORM models (mirror database/schema.sql)
│   │   ├── config/          Settings (.env), database engine/session, logging
│   │   ├── core/            Shared dependencies, exception handling, init_db
│   │   └── constants/       Messages, route prefixes and tags
│   ├── tests/               pytest test suite
│   ├── pyproject.toml       Dependencies and tool config (uv, pytest, ruff)
│   ├── uv.lock              Pinned dependency versions
│   ├── Dockerfile
│   └── .env.example
├── frontend/                Next.js application (App Router, TypeScript)
│   ├── src/
│   │   ├── app/             Routes, layouts and pages (layout.tsx, page.tsx)
│   │   ├── components/      Reusable UI components
│   │   ├── services/        One file per backend module, wraps its endpoints
│   │   ├── lib/             api-client.ts (fetch wrapper), config.ts
│   │   └── types/           Shared TypeScript types (APIResponse mirror)
│   ├── public/              Static assets
│   ├── package.json         Dependencies and scripts (npm)
│   ├── Dockerfile
│   └── .env.example
├── database/
│   ├── schema.sql           Database schema (the source of truth)
│   ├── init_db.py           Cross-platform Python script to create DB & apply schema
│   ├── start.sh             macOS/Linux script to start PostgreSQL and apply schema
│   ├── start.ps1            Windows PowerShell script to start PostgreSQL and apply schema
│   └── backups/             Database dumps created by db-backup (git-ignored)
├── docs/, docx/, meetings/  Project documentation (RAD, SDD, SOW, minutes, ...)
└── README.md
```

### How a request flows

```
Browser → frontend service → api-client ──HTTP──▶ controller → service → dao → PostgreSQL
                                                     ↑            │
                                                    DTO     domain exceptions → APIResponse error
```

**Backend**

- **Controllers** (`api/controller/<module>/`) declare routes, check input through DTOs and
  call a service. They hold no business rules.
- **Services** (`service/<module>/`) hold the business logic. They raise `NotFoundError`,
  `ConflictError` and other `AppException`s, and never `HTTPException`, so they stay
  independent of HTTP.
- **DAOs** (`dao/<module>/`) run the database queries. They `flush()` but don't commit: the
  `get_db` dependency commits once per request, or rolls back on error.
- **Models** (`models/<module>/`) map the tables defined in `database/schema.sql`.
- **DTOs** (`api/dto/<module>/`) are Pydantic schemas. Every endpoint returns the same
  envelope:

  ```json
  { "success": true, "message": "Success", "error": null, "data": { } }
  ```

**Frontend**

- **`lib/api-client.ts`**: `apiFetch<T>(path)` prefixes the API URL, unwraps the envelope and
  throws `ApiError` when `success` is `false`.
- **`services/`**: one file per backend module (start from `template-service.ts`). Components
  call services and never build URLs themselves.
- **`types/api.ts`**: TypeScript mirror of the backend `APIResponse`.

### Adding a module

**Backend:** each layer has an empty `template/` package. Copy it to `<module>/`, rename the
files and classes, map the table (from `schema.sql`) in the model, export the model from
`app/models/__init__.py`, and register the router in `app/api/router.py`.

**Frontend:** copy `src/services/template-service.ts` to `src/services/<module>-service.ts`, and
add pages under `src/app/<route>/page.tsx`.

---

## Prerequisites

| Tool | Version | macOS | Windows | Linux |
| --- | --- | --- | --- | --- |
| **Docker** (recommended) | latest | [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) | [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) | [Docker Engine + Compose](https://docs.docker.com/engine/install/) |
| **uv** (backend) | 0.5+ | `brew install uv` | `winget install astral-sh.uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Python** (backend) | 3.12+ | Installed by uv (`uv python install 3.12`) | Installed by uv | Installed by uv |
| **Node.js** (frontend) | 20.9+ (22 LTS recommended) | `brew install node@22` | [Node.js installer](https://nodejs.org/) or `winget install OpenJS.NodeJS.LTS` | [NodeSource](https://github.com/nodesource/distributions) or `nvm` |
| **PostgreSQL** (only without Docker) | 18 | `brew install postgresql@18` | [PostgreSQL Windows Installer](https://www.postgresql.org/download/windows/) | `sudo apt install postgresql` |

> [!TIP]
> With Docker you can run the whole stack without installing Python, Node.js or PostgreSQL.
> uv and Node.js are only needed for local development with hot reload.

> [!WARNING]
> **macOS: `docker: command not found`.** Docker Desktop installs its CLI in
> `~/.docker/bin`. Make sure Docker Desktop is **running**, then add the CLI to your `PATH`
> in `~/.zshrc` and open a new terminal:
>
> ```bash
> echo 'export PATH="$HOME/.docker/bin:$PATH"' >> ~/.zshrc
> ```

---

## Quick start with Docker (whole stack)

From the repository root:

```bash
docker compose up -d --build
```

| URL | Service |
| --- | --- |
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | API documentation (Swagger UI) |
| http://localhost:8000/api/v1/health/db | Backend + database health check |

### Services

| Service | Host port | Description |
| --- | --- | --- |
| `db` | 5433 | PostgreSQL 18. Data is stored in the named volume `safespend_pgdata`. |
| `db-init` | n/a | One-shot job: applies `database/schema.sql` on **every** start, then exits. |
| `backend` | 8000 | FastAPI, built from `backend/Dockerfile`. Starts after `db-init` succeeds. |
| `frontend` | 3000 | Next.js production server, built from `frontend/Dockerfile`. |
| `db-backup` / `db-restore` | n/a | On-demand tools (profile `tools`). See [Backup and restore](#backup-and-restore). |

The startup order is enforced with health checks: `db` (healthy), then `db-init`
(completed), then `backend` (healthy), then `frontend`. All long-running services use
`restart: unless-stopped`, so they come back automatically when Docker Desktop restarts.

### Data persistence

Database data lives in the named Docker volume **`safespend_pgdata`**, not in the container.

| Command | Containers | Database data |
| --- | --- | --- |
| `docker compose stop` | Stopped | **Kept** |
| `docker compose down` | Removed | **Kept** and reloaded on the next `up` |
| `docker compose up -d` | Started | Existing data is loaded, and `schema.sql` adds any new tables |
| `docker compose down -v` | Removed | **Deleted** (the volume is removed) |

`schema.sql` uses `CREATE TABLE IF NOT EXISTS`, so `db-init` can run on every start without
touching existing data. It only creates what is missing. It never contains `DROP TABLE`: the CI
fails if applying the schema twice recreates a table. Changing a column of an existing table
therefore needs an `ALTER TABLE` statement, or a reset of your local database with
`docker compose down -v` (after a backup).

### Reset the database (start from empty)

To delete all data and start again from an empty database:

1. Optional: take a backup first. Deleting the volume can't be undone.

   ```bash
   docker compose run --rm db-backup
   ```

2. Stop the stack and delete the database volume:

   ```bash
   docker compose down -v
   ```

3. Start again. PostgreSQL creates an empty database and `db-init` applies `schema.sql`:

   ```bash
   docker compose up -d --build
   ```

If the containers were already removed and `down -v` leaves the volume in place, delete it by
name:

```bash
docker volume rm safespend_pgdata
```

### Backup and restore

Backups are SQL dumps written to `database/backups/` on your machine (git-ignored). The
commands work the same on every OS, and `db` must be running.

Create a backup (`database/backups/safespend_<timestamp>.sql`):

```bash
docker compose run --rm db-backup
```

Restore a backup. This replaces the current tables with the ones in the dump:

```bash
docker compose run --rm -e BACKUP_FILE=safespend_20261120_103000.sql db-restore
```

Use backups to move data between machines, or to keep data before running `down -v`.

### Configuration (Docker)

Docker Compose reads an optional `.env` in the repository root. Every value has a default.

```bash
cp .env.example .env
```

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `postgres` / `safespend` | Database credentials (used on first creation of the volume) |
| `DB_PORT` | `5433` | Host port for PostgreSQL. It differs from 5432 to avoid clashing with a local PostgreSQL. |
| `BACKEND_PORT` | `8000` | Host port for the API |
| `FRONTEND_PORT` | `3000` | Host port for the frontend |
If a port is already in use (`port is already allocated`), change it in `.env`. Credentials
are applied only when the volume is **first** created. To change them later, run
`docker compose down -v` (after a backup).

### Useful commands

```bash
docker compose ps
```

```bash
docker compose logs -f backend
```

```bash
docker compose up -d --build backend
```

```bash
docker compose up -d db db-init
```

The third command rebuilds and restarts only the backend after code changes. The last one
starts only the database, for local development.

---

## Local development (hot reload)

Run the database in Docker and the apps directly on your machine.

### 1. Database

**Option A: Docker (recommended).** This starts PostgreSQL on `localhost:5433` and applies
the schema:

```bash
docker compose up -d db db-init
```

**Option B: native PostgreSQL.** Use `./database/start.sh` (macOS/Linux),
`.\database\start.ps1` (Windows), or the cross-platform script:

```bash
cd backend && uv run python -m app.core.init_db
```

With a native PostgreSQL, set `DATABASE_URL` in `backend/.env` to its port (usually 5432).

### 2. Backend

Copy `.env.example` to `.env` (PowerShell: `Copy-Item backend\.env.example backend\.env`):

```bash
cp backend/.env.example backend/.env
```

Install the dependencies:

```bash
cd backend && uv sync
```

Start the API with auto-reload:

```bash
cd backend && uv run uvicorn app.main:app --reload
```

The API runs at **http://localhost:8000**.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `SafeSpend API` | Title shown in the API docs |
| `ENVIRONMENT` | `development` | Environment label |
| `DEBUG` | `false` | FastAPI debug mode |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `API_V1_PREFIX` | `/api/v1` | Prefix for every API route |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list of allowed frontend origins |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/safespend` | Async SQLAlchemy URL (requires `+asyncpg`) |
| `DATABASE_ECHO` | `false` | Log every SQL statement |

### 3. Frontend

Copy `.env.example` to `.env.local` (PowerShell: `Copy-Item frontend\.env.example frontend\.env.local`):

```bash
cp frontend/.env.example frontend/.env.local
```

Install the dependencies:

```bash
cd frontend && npm install
```

Start Next.js with hot reload:

```bash
cd frontend && npm run dev
```

The frontend runs at **http://localhost:3000**.

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL as reached from the browser. It is inlined at build time. |

---

## API documentation

FastAPI generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI schema:** http://localhost:8000/openapi.json

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness: the process is running |
| `GET` | `/api/v1/health/db` | Readiness: the database connection works (returns 503 if not) |

---

## Development tooling

**Backend**, from `backend/`:

| Command | Purpose |
| --- | --- |
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv add <package>` / `uv add --dev <package>` | Add a dependency |

**Frontend**, from `frontend/`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server with hot reload |
| `npm run build` | Production build |
| `npm run lint` | ESLint (Next.js rules) |
| `npm run typecheck` | TypeScript type check |
| `npm install <package>` / `npm install -D <package>` | Add a dependency |
