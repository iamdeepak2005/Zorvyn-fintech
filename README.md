# 🏦 Zorvyn Fintech — Finance Dashboard Platform

A **production-grade backend system** for financial record management, dashboard analytics, and role-based access control. Built with FastAPI, PostgreSQL, and clean layered architecture.

---

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Access Control Matrix](#-access-control-matrix)
- [Database Design](#-database-design)
- [Key Features](#-key-features)
- [Testing](#-testing)
- [CI/CD Integration](#-cicd-integration)
- [Assumptions & Tradeoffs](#-assumptions--tradeoffs)

---

## 🏗️ Architecture

Clean layered architecture with strict separation of concerns:

```
app/
├── api/v1/              # Route handlers (controllers) — NO business logic
│   ├── auth.py          # POST /auth/login
│   ├── admin.py         # CRUD /admin/users
│   ├── records.py       # CRUD /records + CSV export
│   ├── dashboard.py     # Analytics endpoints
│   └── health.py        # Health check
├── core/                # Configuration, security, dependencies
│   ├── config.py        # Settings via pydantic-settings
│   ├── security.py      # JWT + bcrypt
│   ├── database.py      # SQLAlchemy engine/session
│   └── dependencies.py  # RBAC dependency injection
├── models/              # SQLAlchemy ORM models
│   ├── user.py          # Users with role enum
│   ├── financial_record.py  # Records with soft delete
│   ├── audit_log.py     # Audit trail
│   └── idempotency_key.py   # Deduplication keys
├── schemas/             # Pydantic validation schemas
│   ├── common.py        # ApiResponse, PaginatedData
│   ├── auth.py          # LoginRequest, TokenResponse
│   ├── user.py          # UserCreate, UserUpdate, UserResponse
│   ├── record.py        # RecordCreate, RecordUpdate, RecordResponse
│   └── dashboard.py     # Summary, Breakdown, Trends, Insights
├── services/            # Business logic layer
│   ├── auth_service.py      # Authentication logic
│   ├── user_service.py      # User management (atomic transactions)
│   ├── record_service.py    # Record CRUD + idempotency
│   ├── dashboard_service.py # Analytics orchestration
│   └── audit_service.py     # Audit logging
├── repositories/        # Database abstraction layer
│   ├── user_repository.py
│   ├── record_repository.py
│   ├── dashboard_repository.py  # SQL aggregations
│   └── audit_repository.py
├── middleware/           # Cross-cutting concerns
│   ├── request_id.py    # X-Request-ID generation
│   ├── rate_limiter.py  # Per-user/IP rate limiting
│   └── error_handler.py # Global error handling
├── utils/
│   └── csv_export.py    # Streaming CSV generation
└── tests/               # Comprehensive test suite
    ├── conftest.py      # Fixtures, test DB setup
    ├── test_rbac.py     # Access control tests
    ├── test_records.py  # Record CRUD + idempotency tests
    └── test_dashboard.py # Analytics calculation tests
```

### Data Flow

```
Request → Middleware → Route → Service → Repository → Database
                                  ↓
                            Audit Service (logging)
```

**Strict Rules:**

- ❌ No business logic in routes
- ✅ Services handle logic and transactions
- ✅ Repositories handle DB queries
- ✅ Permissions enforced BEFORE business logic

---

## ⚙️ Tech Stack

| Component        | Technology                 |
| ---------------- | -------------------------- |
| Framework        | FastAPI                    |
| Database         | PostgreSQL 16              |
| ORM              | SQLAlchemy 2.0             |
| Validation       | Pydantic 2.x               |
| Auth             | JWT (python-jose) + bcrypt |
| Migrations       | Alembic                    |
| Rate Limiting    | slowapi                    |
| Testing          | pytest + httpx             |
| Containerization | Docker + Docker Compose    |

---

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and start
git clone <repository-url>
cd zorvyn-fintech
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Default admin credentials:

- Email: `admin@example.com`
- Password: `admin123`

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL and create database
# Update .env with your DATABASE_URL

# Run migrations
alembic upgrade head

# Seed admin user
python -m app.seed

# Start server
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finance_db
SECRET_KEY=your-secure-random-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT=100/minute
ENV=development
CORS_ORIGINS=http://localhost:3000
```

---

## 📡 API Endpoints

All endpoints are prefixed with `/api/v1`.

### Authentication

| Method | Endpoint      | Description                            |
| ------ | ------------- | -------------------------------------- |
| POST   | `/auth/login` | Login with email/password, returns JWT |

### Admin — User Management (ADMIN only)

| Method | Endpoint            | Description            |
| ------ | ------------------- | ---------------------- |
| POST   | `/admin/users`      | Create user            |
| GET    | `/admin/users`      | List users (paginated) |
| PATCH  | `/admin/users/{id}` | Update user            |
| DELETE | `/admin/users/{id}` | Delete user            |

### Financial Records

| Method | Endpoint          | Description                            |
| ------ | ----------------- | -------------------------------------- |
| POST   | `/records`        | Create record (ADMIN)                  |
| GET    | `/records`        | List records (filtered, paginated)     |
| GET    | `/records/{id}`   | Get single record (ownership enforced) |
| PATCH  | `/records/{id}`   | Update record (ADMIN)                  |
| DELETE | `/records/{id}`   | Soft delete record (ADMIN)             |
| GET    | `/records/export` | CSV export (ADMIN, ANALYST)            |

**Filtering & Sorting:**

```
GET /api/v1/records?type=EXPENSE&category=Rent&start_date=2026-01-01&end_date=2026-12-31&search=monthly&page=1&limit=20&sort_by=date&order=desc
```

### Dashboard Analytics (ADMIN, ANALYST)

| Method | Endpoint                        | Description                                         |
| ------ | ------------------------------- | --------------------------------------------------- |
| GET    | `/dashboard/summary`            | Total income, expense, net balance                  |
| GET    | `/dashboard/category-breakdown` | Per-category breakdown with percentages             |
| GET    | `/dashboard/trends`             | Monthly income/expense trends                       |
| GET    | `/dashboard/recent`             | Recent records (paginated)                          |
| GET    | `/dashboard/insights`           | Actionable insights (top category, growth %, spike) |

### Health

| Method | Endpoint  | Description                |
| ------ | --------- | -------------------------- |
| GET    | `/health` | Returns `{"status": "ok"}` |

---

## 🔒 Access Control Matrix

| Endpoint                 | ADMIN    | ANALYST  | VIEWER   |
| ------------------------ | -------- | -------- | -------- |
| POST /auth/login         | ✅       | ✅       | ✅       |
| POST /admin/users        | ✅       | ❌       | ❌       |
| GET /admin/users         | ✅       | ❌       | ❌       |
| PATCH /admin/users/{id}  | ✅       | ❌       | ❌       |
| DELETE /admin/users/{id} | ✅       | ❌       | ❌       |
| POST /records            | ✅       | ❌       | ❌       |
| GET /records             | ✅ (all) | ✅ (own) | ✅ (own) |
| GET /records/{id}        | ✅ (all) | ✅ (own) | ✅ (own) |
| PATCH /records/{id}      | ✅       | ❌       | ❌       |
| DELETE /records/{id}     | ✅       | ❌       | ❌       |
| GET /dashboard/\*        | ✅       | ✅       | ❌       |
| GET /records/export      | ✅       | ✅       | ❌       |
| GET /health              | ✅       | ✅       | ✅       |

---

## 🗄️ Database Design

### Enums (PostgreSQL native)

- `user_role`: ADMIN, ANALYST, VIEWER
- `record_type`: INCOME, EXPENSE

### Tables

**users**

- `id`, `name`, `email` (unique), `password_hash`, `role`, `is_active`, `created_at`

**financial_records**

- `id`, `user_id` (FK → users, ON DELETE RESTRICT), `amount` (CHECK > 0), `type`, `category`, `date`, `notes`, `deleted_at`, `created_at`

**audit_logs**

- `id`, `user_id` (FK → users), `action`, `entity`, `entity_id`, `timestamp`

**idempotency_keys**

- `id`, `key` (unique), `user_id`, `response_body`, `status_code`, `created_at`

### Indexes (Performance)

```sql
CREATE INDEX idx_records_date ON financial_records(date);
CREATE INDEX idx_records_category ON financial_records(category);
CREATE INDEX idx_records_type ON financial_records(type);
CREATE INDEX idx_records_user_id ON financial_records(user_id);
CREATE INDEX idx_records_not_deleted ON financial_records(id) WHERE deleted_at IS NULL;  -- Partial index
```

---

## 🌟 Key Features

### 🔐 Security

- **bcrypt** password hashing (never plain text)
- **JWT** access tokens with user_id and role
- Inactive users rejected globally
- **IDOR prevention** via ownership checks in service layer

### 📊 DB-Level Analytics

All dashboard calculations use SQL aggregations (`SUM`, `GROUP BY`, conditional `CASE`) — no Python loops.

### 🔁 Idempotency

`POST /records` supports `Idempotency-Key` header to prevent duplicate creation.

### ♻️ Soft Delete

Records use `deleted_at` field. Non-deleted records optimized with a partial index.

### 📤 Streaming CSV Export

Uses `StreamingResponse` with `yield_per(100)` for memory-efficient export.

### 🔄 Atomic Transactions

Multi-step writes (e.g., create record + audit log) are wrapped in DB transactions. Rollback on any failure.

### 🧾 Audit Logging

All significant actions (CREATE, UPDATE, DELETE, LOGIN) are logged to the audit_logs table.

### ⚡ Rate Limiting

100 requests/minute per user (authenticated) or per IP (unauthenticated).

### 📡 Request ID Tracking

Every request gets a unique `X-Request-ID` in response headers and logs.

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest app/tests/test_rbac.py
pytest app/tests/test_records.py
pytest app/tests/test_dashboard.py
```

Tests use **SQLite in-memory** for speed and isolation. Each test gets a fresh database.

### Test Coverage

- **RBAC tests**: Full access control matrix verification
- **Record tests**: CRUD, validation, idempotency, ownership, soft delete, filtering
- **Dashboard tests**: Summary calculations, category breakdown, trends, insights

---

## 🔄 CI/CD Integration

Tests can be integrated into CI pipelines (e.g., GitHub Actions):

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest -v
```

---

## 📝 Assumptions & Tradeoffs

### Assumptions

- **Single currency system** — no multi-currency support
- **No multi-tenant support** — single organization/deployment
- **UTC-based timestamps** — all timestamps stored in UTC; clients handle localization
- **Roles are static** — ADMIN, ANALYST, VIEWER (no dynamic permission system)
- **Categories are free text** — not enum-constrained for flexibility
- **No refresh tokens** — access tokens only, per requirements

### Tradeoffs

| Decision                        | Rationale                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| SQLite for tests                | Fast, isolated, no external deps; trade: can't test PostgreSQL-specific features (e.g., partial indexes, `to_char`) |
| In-memory rate limiting         | Simpler setup; trade: not distributed (use Redis URI for multi-instance)                                            |
| Idempotency keys in DB          | Persistent; trade: requires cleanup job for expired keys                                                            |
| Soft delete                     | Data preservation; trade: requires `deleted_at IS NULL` filter on all queries (mitigated by partial index)          |
| `ON DELETE RESTRICT` on user FK | Prevents orphaned records; trade: must deactivate users instead of deleting if they have records                    |

### Timezone Policy

> All timestamps are stored in UTC. Clients are responsible for timezone conversion and localization.

---

## 📄 License

Private — Zorvyn Fintech





# Zorvyn Fintech - Financial Records & Dashboard API

A powerful, production-grade API backend built with **FastAPI** for managing financial records, analyzing expenses and income, and visualizing trends through a dynamic dashboard. It focuses heavily on security, robustness, and performant database operations.

---

## 🚀 Key Features

* **Advanced Role-Based Access Control (RBAC):** Three predefined tiers (`ADMIN`, `ANALYST`, `VIEWER`) determine what users can view, edit, or delete using native FastAPI Dependency Injection.
* **Complex Dashboard Analytics:** Computes high-level summaries, category breakdowns, monthly growth percentages, average daily spending, and anomaly detection (spikes) completely at the database layer using advanced SQLAlchemy window functions and groupings for maximum performance.
* **Formatted Excel Exports:** Converts record data streams into memory-efficient, conditionally formatted `.xlsx` files complete with custom coloring and dynamically calculated footers (Total Income, Total Expense, Net Balance).
* **Idempotent API Design:** Uses `Idempotency-Key` headers coupled with an intercept logic table in PostgreSQL to ensure multiple failed requests/retries do not result in double-booking a financial transaction.
* **Audit Logging:** Implements an internal audit log that silently records creation, update, and deletion traces for compliance and tracing.
* **Soft Deletes:** Records are never truly lost or permanently destroyed; soft deletes allow recovering previous application states.

---

## 🛠 Tech Stack

* **Framework:** FastAPI (Asynchronous Python backend)
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy (v2.0)
* **Migrations:** Alembic
* **Authentication:** JWT (JSON Web Tokens) with Passlib & Bcrypt
* **Rate Limiting:** SlowAPI (Redis supported)
* **Data Exports:** openpyxl (Excel/Spreadsheet Engine)

---

## 🔐 Access Control Flow (RBAC)

FastAPI's dependency injection (`app/core/dependencies.py`) enforces strict boundaries on what API endpoints users can access.

1. **VIEWER:**
   - Can access the Dashboard endpoints (Insights, Summary, Trends, etc.) to view statistical overviews.
   - Absolutely no access to fetch raw lists, intercepting logs, exporting data, or modifying resources. Forced to view data relating strictly to their own permissions.
2. **ANALYST:**
   - Inherits `VIEWER` privileges.
   - Authorized to view and filter the raw list of financial records.
   - Authorized to generate colorful, formatted Excel exports of data.
3. **ADMIN:**
   - Inherits `ANALYST` privileges.
   - Full read/write access (Create, Update, Delete) to all system data.
   - Only Admin is authorized to modify physical records to preserve financial integrity.

---

## 🏗 Architecture / Data Flow

The project follows a localized Domain-Driven Design (DDD) to keep components modular:

1. **Routers (`app/api/`):** Listens to JSON requests, extracts query/path parameters, handles Auth injection, and coordinates HTTP responses/errors. Contains no core business logic.
2. **Services (`app/services/`):** The business logic layer. Determines whether an object can technically be deleted, performs idempotency checks, triggers audit mechanisms, and formats data into standard dicts.
3. **Repositories (`app/repositories/`):** The isolated database layer. Specifically translates data requests into raw SQLAlchemy queries. Most analytical heavy lifting (like the `dashboard_repository.py`) belongs physically here to make use of DB engines rather than iterating over data in pure Python memory.
4. **Models (`app/models/`):** Defines physical SQL tables (`users`, `financial_records`, `idempotency_keys`, `audit_logs`).
5. **Schemas (`app/schemas/`):** Pydantic schemas enforce strict validation of incoming requests and format outgoing responses.

---

## 💻 Local Setup & Running instructions

### 1. Set Up Environment
Create a Python Virtual Environment and install packages:
```bash
python -m venv venv
.\venv\Scripts\activate   # (Windows)
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root based on `.env.example` and set your PostgreSQL connection URL along with JWT parameters.
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/finance_db
```

### 3. Initialize Database Migrations
Ensure PostgreSQL is running, then run Alembic to create the tables natively:
```bash
alembic upgrade head
```

### 4. Seed Mock Data (Optional)
Populate the database with a system Admin, Analyst, and Viewer dummy users, alongside 500+ generated financial records to immediately test filtering and dashboard insights!
```bash
python -m app.seed_mock_data
```

### 5. Start the Server
Run the Uvicorn web server in development mode:
```bash
uvicorn app.main:app --reload
```

*Head over to **http://127.0.0.1:8000/docs** to see the interactive Swagger UI and start testing the API endpoints!*
`