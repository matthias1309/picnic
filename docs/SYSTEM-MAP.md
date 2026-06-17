# System Map — Picnic Expense Tracker

**Generated:** 2026-06-17 · **Source:** 15 REQs, 15 ARCHs · **Regenerate:** `/system-map`

> ⚠️ Generated artifact. Do not hand-edit — it will be overwritten. If a relationship here
> looks wrong, fix the underlying REQ/ARCH and regenerate. Treat this map as stale once any
> REQ/ARCH changes; regenerate before relying on it for an impact analysis.

## Domain Clusters

### Email/IMAP Parsing & Ingestion
- **REQs:** REQ-001 (IMAP Polling and Email Ingestion), REQ-010 (Filter Ingested Emails by Subject), REQ-002 (HTML Email Parsing and Structured Receipt Storage), REQ-008 (Fix Price Extraction for Forwarded Invoice Emails), REQ-012 (Robust Item-Row Detection for the Current Picnic Invoice Format), REQ-013 (Group Receipt Line Items by Picnic Order Number), REQ-014 (Parse the Delivery Date from the Invoice HTML)
- **Shared architecture:** `backend/imap/client.py`, `backend/imap/parser.py`, `backend/services/receipt_service.py`, `receipts`/`receipt_items` tables, APScheduler poll task in `backend/main.py`
- **Purpose:** Pull Picnic invoice emails over IMAP and turn their HTML into structured, deduplicated receipt data.

### Database & Persistence
- **REQs:** REQ-002 (HTML Email Parsing and Structured Receipt Storage), REQ-013 (order_number column), REQ-014 (delivery_date / effective_date), REQ-011 (Configure Monthly Budget)
- **Shared architecture:** `backend/models.py`, SQLAlchemy schema for `receipts`, `products`, `receipt_items`, `price_history`, `budget_settings`
- **Purpose:** Own the normalized schema that every other domain reads or writes.

### Stats/Analytics API & Data Exposure
- **REQs:** REQ-003 (REST API for Receipt and Product Data), REQ-004 (Statistics and Spending Insights), REQ-009 (Delete a Receipt), REQ-011 (Configure Monthly Budget)
- **Shared architecture:** `backend/api/routes.py`, `backend/schemas.py`, `backend/services/stats_service.py`, `backend/services/receipt_service.py`, `backend/services/budget_service.py`
- **Purpose:** Expose receipts, products, price history, and aggregated spending stats over REST.

### Dashboard & Frontend
- **REQs:** REQ-005 (React Dashboard), REQ-009 (delete button), REQ-011 (budget edit widget), REQ-013 (order-grouped item display), REQ-014 (effective-date-driven sorting, no direct UI change)
- **Shared architecture:** `src/pages/*`, `src/components/*`, `src/hooks/useReceipts.ts`, `useStats.ts`, `useProducts.ts`, `src/api/client.ts`, Zustand `useUiStore`, TanStack Query, Recharts
- **Purpose:** Visualize receipts, price trends, and spending statistics; let the user manage data (delete, budget edit).

### Platform/Security & Authentication
- **REQs:** REQ-006 (User Login & Authentication), REQ-007 (Login Rate Limiting)
- **Shared architecture:** `backend/auth/security.py`, `backend/auth/service.py`, `backend/auth/rate_limit.py`, `backend/api/auth_routes.py`, `users`/`sessions`/`login_attempts` tables, `src/pages/Login.tsx`, `src/components/ProtectedRoute.tsx`
- **Purpose:** Gate the dashboard and API behind session-cookie auth and protect login from brute-force.

### Settings & Configuration
- **REQs:** REQ-001 (IMAP credentials via `.env`), REQ-010 (subject filter via `.env`), REQ-004 (budget `.env` fallback), REQ-011 (budget persisted in DB, overrides `.env`)
- **Shared architecture:** `backend/config.py` (`Settings`), `budget_settings` table
- **Purpose:** Centralize environment-driven and DB-persisted configuration values.

### Platform & Infra
- **REQs:** REQ-015 (Staged Deployment with a Dev Acceptance Gate)
- **Shared architecture:** `.github/workflows/ci-cd.yml`, `scripts/deploy.sh`, `scripts/deploy_lib.sh`, `backend/tests/acceptance/`, `/picnic/health`
- **Purpose:** Gate every deploy through a dev environment and acceptance tests before production.

## Dependency Matrix

| REQ | Title | Builds on | Overlaps with | Supersedes |
|-----|-------|-----------|---------------|------------|
| REQ-002 | HTML Email Parsing and Structured Receipt Storage | REQ-001 | — | — |
| REQ-003 | REST API for Receipt and Product Data | REQ-002 | — | — |
| REQ-004 | Statistics and Spending Insights | REQ-002, REQ-003 | REQ-011 (budget value) | — |
| REQ-005 | React Dashboard | REQ-003, REQ-004, REQ-006 | REQ-009, REQ-011, REQ-013, REQ-014 | — |
| REQ-006 | User Login & Authentication | — | REQ-009, REQ-011 (auth dependency) | — |
| REQ-007 | Login Rate Limiting | REQ-006 | — | — |
| REQ-008 | Fix Price Extraction for Forwarded Invoice Emails | REQ-002 | REQ-012 | — |
| REQ-009 | Delete a Receipt | REQ-003, REQ-006 | REQ-005 | — |
| REQ-010 | Filter Ingested Emails by Subject | REQ-001 | — | REQ-002 (upstream filter) |
| REQ-011 | Configure Monthly Budget | REQ-004, REQ-006 | REQ-005 | — |
| REQ-012 | Robust Item-Row Detection for the Current Picnic Invoice Format | REQ-002 | REQ-008 | — |
| REQ-013 | Group Receipt Line Items by Picnic Order Number | REQ-002, REQ-003, REQ-005 | — | — |
| REQ-014 | Parse the Delivery Date from the Invoice HTML | REQ-002, REQ-003, REQ-004 | — | — |
| REQ-015 | Staged Deployment with a Dev Acceptance Gate | REQ-001…REQ-014 (tests entire system) | — | — |

(REQ-001 has no inbound "builds on" — it is the root of the dependency graph.)

## Architecture Interplay (Touchpoint Index)

| Touchpoint | Type | Touched by |
|-----------|------|------------|
| `backend/imap/client.py` | module | REQ-001, REQ-010 |
| `backend/imap/parser.py` | module | REQ-002, REQ-008, REQ-012, REQ-013, REQ-014 |
| `backend/services/receipt_service.py` | module | REQ-002, REQ-003, REQ-009, REQ-013, REQ-014 |
| `backend/services/stats_service.py` | module | REQ-004, REQ-014 |
| `backend/services/budget_service.py` | module | REQ-011 |
| `backend/api/routes.py` | module | REQ-003, REQ-004, REQ-009, REQ-011, REQ-013 |
| `backend/api/auth_routes.py` | module | REQ-006, REQ-007 |
| `backend/api/dependencies.py` | module | REQ-003, REQ-006 |
| `backend/auth/security.py` | module | REQ-006 |
| `backend/auth/rate_limit.py` | module | REQ-007 |
| `backend/models.py` | module | REQ-002, REQ-006, REQ-007, REQ-011, REQ-013, REQ-014 |
| `backend/main.py` | module | REQ-001, REQ-006, REQ-010 |
| `receipts` | table | REQ-001, REQ-002, REQ-003, REQ-004, REQ-009, REQ-014 |
| `products` | table | REQ-002, REQ-003, REQ-004 |
| `receipt_items` | table | REQ-002, REQ-003, REQ-004, REQ-009, REQ-013 |
| `price_history` | table | REQ-002, REQ-004, REQ-009, REQ-014 |
| `users` | table | REQ-006 |
| `sessions` | table | REQ-006 |
| `login_attempts` | table | REQ-007 |
| `budget_settings` | table | REQ-011 |
| Message-ID deduplication | calculation | REQ-001 |
| Price string → cents conversion | calculation | REQ-002 |
| Row-style normalization (tbody/whitespace/case) | calculation | REQ-008, REQ-012 |
| Order-number extraction & nearest-match grouping | calculation | REQ-013 |
| Delivery-date / `effective_date` resolution | calculation | REQ-014 |
| Spending aggregation (week/month buckets) | calculation | REQ-004, REQ-014 |
| Top-items ranking | calculation | REQ-004 |
| Price trend min/max/avg | calculation | REQ-004 |
| Budget vs. spent comparison | calculation | REQ-004, REQ-011 |
| Session expiry / PBKDF2 password check | calculation | REQ-006 |
| Failed-login lockout window | calculation | REQ-007 |
| `/picnic/health` endpoint | route | REQ-001 (implicit), REQ-006 (exempted), REQ-015 (verified) |
| `GET /picnic/api/receipts`, `/receipts/{id}` | route | REQ-003, REQ-009 (extends), REQ-013 (response field) |
| `GET /picnic/api/products`, `/products/{id}/price-history` | route | REQ-003 |
| `DELETE /picnic/api/receipts/{id}` | route | REQ-009 |
| `GET /picnic/api/stats/*` | route | REQ-004, REQ-011 (budget endpoint) |
| `PUT /picnic/api/settings/budget` | route | REQ-011 |
| `POST /picnic/api/auth/login`, `/logout`, `GET /auth/me` | route | REQ-006, REQ-007 |
| `src/pages/Home.tsx`, `Stats.tsx`, `Receipts.tsx` | UI surface | REQ-005, REQ-009, REQ-011, REQ-013 |
| `src/components/Receipts/ReceiptDetail.tsx` | UI surface | REQ-005, REQ-009, REQ-013 |
| `src/components/Budget/BudgetWidget.tsx` | UI surface | REQ-005, REQ-011 |
| `src/components/ProtectedRoute.tsx`, `src/pages/Login.tsx` | UI surface | REQ-006, REQ-007 |
| `.github/workflows/ci-cd.yml`, `scripts/deploy.sh` | CI/CD | REQ-015 |
