# SafeSpend

SafeSpend is a preventive decision-support tool: it estimates how much you can spend today
(the **Safe-to-Spend** figure) without putting upcoming expenses at risk.

This repository holds the **backend API** (Python, FastAPI, PostgreSQL 18) and the project's
documentation. The backend is configured to be **100% cross-platform**, running seamlessly on
**Windows**, **macOS**, and **Linux**.

---

## Repository layout

```
SafeSpend/
├── .gitattributes           Enforces consistent LF line endings across Windows and Unix
├── .vscode/                 Recommended VS Code configuration and extensions
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
├── database/
│   ├── schema.sql           Database schema (the source of truth)
│   ├── init_db.py           Cross-platform Python script to create DB & apply schema
│   ├── start.sh             macOS/Linux script to start PostgreSQL and apply schema
│   └── start.ps1            Windows PowerShell script to start PostgreSQL and apply schema
├── docker-compose.yml       PostgreSQL 18 + backend (runs identically on Windows/Mac/Linux)
├── docs/, docx/, meetings/  Project documentation (RAD, SDD, SOW, minutes, ...)
└── README.md
```

### How a request flows

```
HTTP request → controller → service → dao → model / PostgreSQL
                    ↑            │
                   DTO     domain exceptions → core/exceptions.py → APIResponse error
```

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

---

## Prerequisites

| Tool | Version | macOS | Windows | Linux |
| --- | --- | --- | --- | --- |
| **uv** | 0.5+ | `brew install uv` | `winget install astral-sh.uv`<br>_or_ `irm https://astral.sh/uv/install.ps1 \| iex` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Python** | 3.12+ | Handled by uv (`uv python install 3.12`) or `brew install python@3.12` | Handled by uv (`uv python install 3.12`) or Windows installer | Handled by uv (`uv python install 3.12`) or apt |
| **Docker** (recommended) | latest | [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/) | [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) | [Docker Engine + Compose](https://docs.docker.com/engine/install/) |
| **PostgreSQL** (if not using Docker) | 18 | `brew install postgresql@18` | [PostgreSQL Windows Installer](https://www.postgresql.org/download/windows/) | `sudo apt install postgresql` |

> [!TIP]
> **uv** automatically installs and manages the correct Python version if you don't have Python 3.12 installed on your system. Simply install `uv`, and it handles the rest!

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd SafeSpend
   ```

2. **Synchronize dependencies:**

   ```bash
   cd backend
   uv sync
   ```

   `uv sync` automatically creates `backend/.venv` and installs the required packages and development tools from `uv.lock`.

---

## Configuration

Settings are read from environment variables or `backend/.env`.

Copy the example configuration file:

- **macOS / Linux / Git Bash:**
  ```bash
  cp backend/.env.example backend/.env
  ```
- **Windows (PowerShell):**
  ```powershell
  Copy-Item backend\.env.example backend\.env
  ```
- **Windows (Command Prompt):**
  ```cmd
  copy backend\.env.example backend\.env
  ```

### Main configuration parameters

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `SafeSpend API` | Title shown in the API docs |
| `ENVIRONMENT` | `development` | Environment label (`development`, `production`, etc.) |
| `DEBUG` | `false` | FastAPI debug mode |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `API_V1_PREFIX` | `/api/v1` | Prefix for every API route |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON list of allowed frontend origins |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/safespend` | Async SQLAlchemy URL (requires `+asyncpg`) |
| `DATABASE_ECHO` | `false` | Log every SQL statement to stdout |

---

## Running locally

### 1. Start the Database

Choose the option that fits your setup:

#### Option A: Docker Compose (Recommended for both Windows & macOS)
No need to install PostgreSQL locally on your OS:

```bash
docker compose up -d db
```

The database container runs on port 5432 and automatically applies `database/schema.sql` on first launch.

#### Option B: Local PostgreSQL (Native on your OS)
If you prefer running PostgreSQL natively on your machine:

- **On macOS / Linux:**
  ```bash
  ./database/start.sh
  ```
- **On Windows (PowerShell):**
  ```powershell
  .\database\start.ps1
  ```
- **Any OS (Universal Python runner):**
  ```bash
  cd backend
  uv run python -m app.core.init_db
  ```
  *(This cross-platform script connects to your PostgreSQL instance, creates the `safespend` database if it doesn't exist, and applies `schema.sql` without needing `psql` or `brew`.)*

---

### 2. Start the FastAPI API

From the `backend/` directory:

- **macOS / Linux / PowerShell / Git Bash:**
  ```bash
  cd backend
  uv run uvicorn app.main:app --reload
  ```
- **Windows (CMD):**
  ```cmd
  cd backend
  uv run uvicorn app.main:app --reload
  ```

The API will be available at **http://localhost:8000**.

Test connectivity:
- In your browser: [http://localhost:8000/api/v1/health/db](http://localhost:8000/api/v1/health/db)
- Via terminal:
  ```bash
  curl http://localhost:8000/api/v1/health/db
  ```

---

## Running completely with Docker

To run both the PostgreSQL database and the backend in containers:

```bash
docker compose up --build
```

| Service | Port | Description |
| --- | --- | --- |
| `db` | 5432 | PostgreSQL 18 container. Data is stored in volume `pgdata`. |
| `backend` | 8000 | FastAPI container built from `backend/Dockerfile`. |

Useful Docker commands:

```bash
# Follow backend logs
docker compose logs -f backend

# Stop containers
docker compose down

# Stop and wipe database volume (schema.sql will re-run on next start)
docker compose down -v
```

---

## API documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI schema:** http://localhost:8000/openapi.json

Current endpoints:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness: the process is running |
| `GET` | `/api/v1/health/db` | Readiness: database connection is established |

---

## Development tooling

All development tools are run through `uv` from the `backend/` folder on any operating system:

```bash
# Run unit & integration tests
uv run pytest

# Check code formatting and linting
uv run ruff check .

# Automatically apply formatting
uv run ruff format .

# Add a runtime dependency
uv add <package>

# Add a development dependency
uv add --dev <package>
```