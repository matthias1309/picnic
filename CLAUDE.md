# CLAUDE.md — Project Instructions for Claude Code

This file is the primary system prompt for Claude Code when working in this project.
It is committed to the repository and shared across all team members.
Claude Code reads it automatically at the start of every session.

---

## Project Overview

**Project Name:** Picnic Expense Tracker

**Purpose:** Automatically parse Picnic.de grocery receipt emails, extract article prices and quantities, and build a historical database. Provides insights into grocery spending: price trends over time, most-bought items, budget tracking, and purchase statistics.

**Primary Audience:** Personal use (single user tracking own Picnic purchases)

**Status:** Active development (MVP Phase 1: Email parsing + dashboard)

**MVP Scope:**
1. IMAP polling of Picnic invoice emails (Uberspace mailbox)
2. HTML email parsing → extract articles, quantities, prices
3. SQLite database for receipt history
4. REST API for data access
5. React dashboard: price history charts, purchase statistics, budget tracking

---

## Tech Stack

**Backend:**

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Language     | Python 3.12                       |
| Runtime      | Gunicorn (WSGI) on Uberspace      |
| Framework    | FastAPI 0.104+                    |
| Database     | SQLite 3.x (file-based)           |
| ORM          | SQLAlchemy 2.0+                   |
| Email Parser | imaplib + BeautifulSoup 4         |
| Testing      | pytest + pytest-asyncio           |
| Linting      | Ruff (check + format)             |

**Frontend:**

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Language     | TypeScript 5.x                    |
| Runtime      | Node.js 20 LTS                    |
| Framework    | React 18+                         |
| State        | TanStack Query (data) + Zustand   |
| Charts       | Recharts (price history, stats)   |
| Styling      | TailwindCSS                       |
| Build        | Vite                              |
| Testing      | Vitest + React Testing Library    |
| Linting      | ESLint + Prettier                 |

**Deployment:**

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Backend      | Gunicorn on Uberspace (Python 3.12) |
| Frontend     | Static SPA on Uberspace (nginx)   |
| Database     | SQLite on Uberspace (/home/...)   |
| CI/CD        | GitHub Actions (tests, lint)      |

---

## Key Conventions

All coding and workflow conventions are documented in `.claude/rules/`.
Claude should read those files before writing or modifying code.

- **Coding style:** `.claude/rules/coding-style.md`
- **Testing practices:** `.claude/rules/testing-practices.md`
- **Git workflow:** `.claude/rules/git-workflow.md`
- **V-Model & traceability:** `.claude/rules/v-model.md`
- **Project learnings:** `.claude/rules/learnings.md`

When in doubt, follow the existing patterns in the codebase rather than inventing new ones.
If a convention is unclear, ask before proceeding.

---

## Common Commands

**Backend (Python):**

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server (with hot-reload)
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run all tests
pytest

# Run tests in watch mode
pytest-watch

# Run linter & format check
ruff check backend/
ruff format --check backend/

# Run linter with auto-fix
ruff check --fix backend/
ruff format backend/

# Type-check (if added)
mypy backend/ --ignore-missing-imports
```

**Frontend (React + TypeScript):**

```bash
# Install dependencies
cd frontend && npm install

# Run dev server (Vite)
npm run dev

# Build for production
npm run build

# Preview production build locally
npm run preview

# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Lint & format check
npm run lint

# Lint with auto-fix
npm run lint:fix
```

**Always run tests and linting before considering a task complete.**

---

## Project Structure

```
backend/
  main.py                    # FastAPI app entry point
  config.py                  # Configuration (env vars, settings)
  models.py                  # SQLAlchemy ORM models (Receipt, Item, Product, etc.)
  schemas.py                 # Pydantic schemas (request/response)
  database.py                # SQLAlchemy setup & session
  
  imap/
    client.py                # IMAP polling logic
    parser.py                # HTML email parser → receipt data
    
  api/
    routes.py                # REST endpoints (/api/receipts, /api/stats, etc.)
    dependencies.py          # Shared dependencies (auth, DB session)
    
  services/
    receipt_service.py       # Business logic for receipts
    stats_service.py         # Statistics calculations (trends, top items)
    
  tests/
    conftest.py              # pytest fixtures
    test_imap.py             # IMAP client tests
    test_parser.py           # Receipt parser tests
    test_api.py              # API endpoint tests
    test_services.py         # Service logic tests

frontend/
  src/
    components/
      Dashboard.tsx          # Main dashboard page
      Charts/
        PriceHistory.tsx     # Recharts price trend
        PurchaseStats.tsx    # Top items, frequencies
      Settings/
        IMAPConfig.tsx       # IMAP credential form
        
    pages/
      Home.tsx
      Stats.tsx
      Settings.tsx
      
    api/
      client.ts              # REST API calls (React Query)
      
    types/
      index.ts               # TypeScript interfaces
      
    hooks/
      useReceipts.ts
      useStats.ts
      
    App.tsx
    main.tsx
    
  tests/
    Dashboard.test.tsx
    Charts.test.tsx
    (vitest + RTL)
    
  public/
  index.html
  vite.config.ts
  tsconfig.json
  tailwind.config.js

docs/
  requirements/             # REQ-XXX.md user stories
  architecture/             # ARCH-XXX.md design docs
  test-specs/               # TEST-XXX.md test specifications
  code-reviews/             # CR-XXX.md review documents

.env.example                # Template for .env (IMAP credentials, DB path)
requirements.txt            # Python dependencies
package.json                # Frontend dependencies
.gitignore
README.md
```

---

## Language

- **All repository content is written in English** — code, comments, rules, commands, docs, commit messages.
- Conversation with the developer may happen in any language; the repository always stays English.

---

## Important Notes

- **Never commit secrets.** API keys, passwords, tokens, and credentials must never appear
  in committed files. Use environment variables and a `.env` file (which is gitignored).
  Provide a `.env.example` with placeholder values as documentation.
- **Never force-push to `main` or `master`.** See `.claude/rules/git-workflow.md`.
- **Prefer small, focused commits** over large, sweeping changes. Each commit should
  represent one logical unit of work.
- **Write tests for new functionality.** Do not leave new code paths uncovered.
- **Before adding a dependency**, check whether the functionality already exists in the
  codebase or standard library. Confirm with the developer before installing new packages.
- **Database migrations** must be reviewed by a human before being run in production.
- **Keep this file up to date.** When the stack or conventions change, update CLAUDE.md
  so future Claude sessions have accurate context.

---

## Architecture Notes

**Backend:**
- IMAP polling runs as a scheduled task (APScheduler) every 30 minutes, triggered manually or periodically.
- Email parsing uses BeautifulSoup to extract HTML tables from Picnic invoices → JSON (items with price, qty).
- All database access goes through SQLAlchemy ORM (no raw SQL).
- Business logic lives in `services/` — routes are thin wrappers around service calls.
- Receipt deduplication: emails are matched by `Message-ID` header to avoid double-processing.

**Frontend:**
- React SPA communicates exclusively via REST API (no GraphQL).
- TanStack Query manages server state & caching; Zustand for local UI state.
- Charts use Recharts for price trends & purchase statistics (configurable time ranges).
- No authentication initially (single-user assumption); can be added in Phase 2.

**Database:**
- SQLite with SQLAlchemy. Migrations use Alembic (optional, since this is MVP).
- Schema: `receipts`, `receipt_items`, `products`, `price_history` tables.
- Denormalization: `price_history` stores individual item prices per receipt for efficient charting.

**Deployment on Uberspace:**
- Backend: Python app served via Gunicorn behind nginx reverse proxy.
- Frontend: Static SPA (built Vite bundle) served directly by nginx.
- Database: SQLite file in `/home/user/data/picnic.db` (persistent, readable by both backend processes).
- IMAP credentials stored in `.env` (not committed), sourced by FastAPI on startup.

**V-Model Compliance:**
- Every feature has a REQ document (user story + acceptance criteria).
- Every REQ traces to ARCH & TEST-SPEC before code is written.
- Tests are written first (TDD), then code.
- Git history links commits to REQ IDs for traceability.

---

## Out of Scope (Phase 1 MVP)

- **Multi-user & split bills:** Only single-user tracking initially. Phase 2 feature.
- **Multi-account:** Only one Picnic account / IMAP mailbox.
- **OAuth / authentication:** Not needed for MVP (personal use).
- **Mobile app:** Web-only initially.
- **Real-time notifications:** Email polling is on a fixed 30-minute schedule.
- **Advanced analytics:** ML-based recommendations, clustering, etc. — Phase 2+.
- **Fuzzy product matching:** Use exact product names for MVP; improve matching later.

**Deployment constraints:**
- Must run on Uberspace (no external services beyond IMAP).
- No third-party APIs for price data / product info.
- SQLite only (no PostgreSQL instance).

**Code quality:**
- Do not add dependencies without discussing with the developer first.
- Do not force-push to `main` or `master`.
- Do not commit `.env`, `*.db`, or credentials.
- Database migrations are reviewed before production deploy.
- Target 80%+ test coverage on business logic.
