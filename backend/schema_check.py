"""
Schema drift detection: compares backend.models.Base.metadata against the
live database schema and reports missing tables and missing columns.

Traces: ARCH-025
Verifies: REQ-025

Detects only — never applies. Migrations stay a reviewed, human-run step
(CLAUDE.md); this module exists to fail deploys loudly and early, with the
exact SQL an operator needs, when the database can't serve the code that's
about to run against it.

Runnable standalone (AC-025-07):

    python -m backend.schema_check
    python -m backend.schema_check --database-url sqlite:///path/to/other.db
"""

import argparse
import sys
from dataclasses import dataclass, field

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn, CreateTable

from backend.config import settings
from backend.models import Base


@dataclass(frozen=True)
class MissingTable:
    """A table the models declare that the database does not have."""

    table_name: str
    create_statement: str


@dataclass(frozen=True)
class MissingColumn:
    """A column the models declare that the database's table does not have."""

    table_name: str
    column_name: str
    alter_statement: str


@dataclass(frozen=True)
class DriftReport:
    """Every difference found between the models and the live database."""

    missing_tables: list[MissingTable] = field(default_factory=list)
    missing_columns: list[MissingColumn] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.missing_tables or self.missing_columns)


def check_schema_drift(engine: Engine) -> DriftReport:
    """Compare Base.metadata against `engine`'s live schema.

    Only tables/columns the models declare are ever inspected, so a column
    or table present in the database but absent from the models (e.g. after
    a rollback) is never reported (AC-025-06). Every difference is collected
    before returning, so one call surfaces everything (AC-025-05).
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing_tables: list[MissingTable] = []
    missing_columns: list[MissingColumn] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            create_statement = str(CreateTable(table).compile(dialect=engine.dialect)).strip()
            missing_tables.append(
                MissingTable(table_name=table.name, create_statement=create_statement)
            )
            continue

        existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            column_ddl = str(CreateColumn(column).compile(dialect=engine.dialect)).strip()
            alter_statement = f"ALTER TABLE {table.name} ADD COLUMN {column_ddl}"
            missing_columns.append(
                MissingColumn(
                    table_name=table.name,
                    column_name=column.name,
                    alter_statement=alter_statement,
                )
            )

    return DriftReport(missing_tables=missing_tables, missing_columns=missing_columns)


def format_report(report: DriftReport) -> str:
    """Human-readable report: one line naming each gap, followed by the
    exact DDL statement that closes it."""
    if not report.has_drift:
        return "No schema drift detected — database matches the models."

    lines = ["Schema drift detected:"]

    for missing_table in report.missing_tables:
        lines.append(f"\n- Table {missing_table.table_name!r} is missing.")
        lines.append(f"  {missing_table.create_statement}")

    for missing_column in report.missing_columns:
        lines.append(
            f"\n- Column {missing_column.column_name!r} on table "
            f"{missing_column.table_name!r} is missing."
        )
        lines.append(f"  {missing_column.alter_statement};")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code without calling
    sys.exit itself, so it can be called directly from tests."""
    parser = argparse.ArgumentParser(
        description="Detect schema drift between the SQLAlchemy models and a database."
    )
    parser.add_argument(
        "--database-url",
        default=settings.database_url,
        help="SQLAlchemy database URL to check (defaults to the configured DATABASE_URL).",
    )
    args = parser.parse_args(argv)

    engine = create_engine(args.database_url)
    report = check_schema_drift(engine)
    print(format_report(report))

    return 1 if report.has_drift else 0


if __name__ == "__main__":
    sys.exit(main())
