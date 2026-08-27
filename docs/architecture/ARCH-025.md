# ARCH-025 — Schema Drift Check Before Deploy Restart

**Status:** draft
**Created:** 2026-08-27
**Traces:** REQ-025
**Verified by:** TEST-025

## Summary

A new module, `backend/schema_check.py`, compares the SQLAlchemy model
metadata (`backend.models.Base.metadata`) against the live database schema
and reports drift: tables or columns the models declare that the database
does not have. `scripts/deploy.sh` runs this check as part of step 4
("Setup database"), after the existing fresh-database `init_db()` branch,
and aborts the deploy — before the frontend build and before
`supervisorctl restart` — if drift is found. The same check is importable
and runnable as a standalone CLI so an operator can ask "is a migration
pending?" without running a deploy.

## Design

### `backend/schema_check.py`

```python
@dataclass(frozen=True)
class MissingTable:
    table_name: str
    create_statement: str  # full CREATE TABLE ... DDL, dialect-compiled

@dataclass(frozen=True)
class MissingColumn:
    table_name: str
    column_name: str
    alter_statement: str  # ALTER TABLE ... ADD COLUMN ... <type>, dialect-compiled

@dataclass(frozen=True)
class DriftReport:
    missing_tables: list[MissingTable]
    missing_columns: list[MissingColumn]

    @property
    def has_drift(self) -> bool: ...

def check_schema_drift(engine: Engine) -> DriftReport: ...

def format_report(report: DriftReport) -> str:
    """Human-readable report: one line naming each missing table/column,
    followed by the exact DDL statement to add it."""

def main() -> int:
    """CLI entry point. --database-url overrides backend.config.settings
    (AC-025-07: runnable standalone against an arbitrary database)."""
```

`check_schema_drift`:

1. Uses `sqlalchemy.inspect(engine)` to get the live schema (on SQLite this
   is backed by `PRAGMA table_info`/`sqlite_master`, but the code stays
   dialect-agnostic at the API level).
2. For each table in `Base.metadata.sorted_tables`:
   - If the table name is not in the inspector's `get_table_names()`, record
     a `MissingTable` with DDL from
     `str(CreateTable(table).compile(engine))` (AC-025-03, AC-025-05).
   - Otherwise, diff the model's declared column names against
     `{col["name"] for col in inspector.get_columns(table.name)}`. Every
     column present in the model but absent from the DB becomes a
     `MissingColumn`, with `alter_statement` built as
     `ALTER TABLE {table} ADD COLUMN {compiled_column_ddl}` using the
     dialect's type compiler for the column's SQLAlchemy type
     (AC-025-03).
3. Columns present in the DB but not declared on the model are never
   inspected and never reported (AC-025-06) — the loop only ever iterates
   `Base.metadata`'s own tables/columns, so there is no code path that could
   flag them.
4. All findings across all tables are collected into one `DriftReport`
   before returning — a single run surfaces every gap, not just the first
   (AC-025-05).

`main()` reads `--database-url` (falling back to
`backend.config.settings.database_url`), builds an engine, runs the check,
prints `format_report(...)` to stdout, and returns `0` when
`report.has_drift` is `False`, `1` otherwise — matching AC-025-07's "same
report, exit status reflects drift".

### `scripts/deploy.sh` — step 4

```
[4/6] Setting up database...
if [ ! -f "$PICNIC_DB" ]; then
    python -c "from backend.database import init_db; init_db()"
    echo "✓ Database initialized"
else
    if ! python -m backend.schema_check; then
        echo "✗ Schema drift detected — see output above for the required ALTER TABLE statements"
        exit 1
    fi
    echo "✓ Schema matches models, no drift"
fi
```

- The fresh-DB branch (AC-025-02) is unchanged: `init_db()` still creates
  every table from current metadata, so a brand-new database can never be
  reported as drifting.
- The check runs against the venv's Python, same as the existing `init_db`
  call, so it reads `backend.config.settings` the same way the running app
  will (same `.env`, same `DATABASE_URL`).
- Because it runs inside step 4 — before step 5 (frontend build) and step 6
  (`supervisorctl restart picnic`) — a non-zero exit here, combined with
  `deploy.sh`'s existing `set -e`, stops the script before either runs
  (AC-025-01 continues past the check when clean; AC-025-04 never reaches
  the restart when dirty). No new error-handling mechanism is needed;
  `set -e` already does this for every other step in the script.

### CI (`.github/workflows/ci-cd.yml`)

No change. `deploy-dev` pipes `deploy.sh` over SSH as `bash -s`; a non-zero
exit from the remote script already fails that step, which fails the
`deploy-dev` job. `acceptance` and `deploy-prod` both declare
`needs: deploy-dev` (`deploy-prod` transitively via `needs: acceptance`),
and GitHub Actions skips a job whose `needs` entry failed — so AC-025-08
falls out of the existing job graph once `deploy.sh` itself fails correctly.

### Standalone use (AC-025-07)

```bash
source venv/bin/activate
python -m backend.schema_check
# or, against a specific file:
python -m backend.schema_check --database-url sqlite:///path/to/other.db
```

## Key Decisions

- **Introspect `Base.metadata` at check time rather than maintain a
  migration list.** Every column added to a model is automatically covered;
  this is the direct fix for the gap `create_all` and REQ-024 exposed,
  per the REQ's own rationale.
- **`sqlalchemy.inspect()` over raw `PRAGMA table_info` SQL.** Same
  underlying SQLite mechanism, but keeps the module reading schema the same
  way the ORM layer does elsewhere in the codebase (CLAUDE.md: "all
  database access goes through SQLAlchemy"), and gives dialect-aware DDL
  compilation for the reported statements for free via `CreateTable` /
  the dialect's `DDLCompiler`.
- **Detect-and-report, never apply.** No code path in this module executes
  DDL. This preserves CLAUDE.md's "database migrations are reviewed by a
  human before production" rule; the deliverable is a loud, actionable
  failure, not automated schema changes (REQ-025 Notes).
- **A plain Python module + CLI, not Alembic.** Matches the REQ's rejected
  alternative: Alembic is the "real" tool but is disproportionate apparatus
  for a single-user SQLite app whose only unmet need today is "detect a
  missing column."
- **Failure point is inside step 4, before steps 5–6.** This is what makes
  AC-025-04 hold: the currently running Gunicorn workers are never touched
  when the check fails, so the deploy fails into a consistent state (old
  code, old schema) rather than a broken one (new code, old schema).

## Out of Scope

- Applying, generating, or ordering migrations (detection only).
- Changed column *types*, renames, dropped columns, or index/constraint
  drift — only tables and columns the models declare but the database lacks
  are checked, matching what actually breaks the running app today.
- Databases other than SQLite — the CLI accepts a `--database-url`, but
  `PRAGMA`-backed reflection and the DDL this project's SQLAlchemy version
  targets are only exercised against SQLite in this codebase.
- Any change to `.github/workflows/ci-cd.yml` — the existing `needs:` graph
  already fails the pipeline correctly once `deploy.sh` exits non-zero.
- The separate gap that the acceptance suite (REQ-015) never exercises a
  database-backed route — tracked as its own future REQ.

## Open Questions

None — the REQ's "Implementation approach" and "Rejected alternatives"
sections already settle the open design choices for this scope.
