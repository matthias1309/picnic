"""
Schema drift detection against the live database (TEST-025).

Traces: ARCH-025
Verifies: REQ-025 (AC-025-01, AC-025-02, AC-025-03, AC-025-05, AC-025-06,
AC-025-07)

Every engine here is a real SQLite database (in-memory or tmp_path file) —
no mocks. Incomplete/extra-column schemas are built with hand-written SQL,
never through Base.metadata, so these tests fail for the right reason if the
comparison code ever stops reading the live DB schema.
"""

from pathlib import Path

from sqlalchemy import create_engine, text

from backend.database import init_db
from backend.models import Base
from backend.schema_check import check_schema_drift, main


def _engine(path: Path):
    return create_engine(f"sqlite:///{path}")


# TC-025-01
# Given an in-memory database created from Base.metadata (matches the models)
# When check_schema_drift is called against it
# Then the report has no drift
# And missing_tables and missing_columns are both empty
def test_check_schema_drift_reports_nothing_when_schema_matches():
    # Arrange
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    # Act
    report = check_schema_drift(engine)

    # Assert
    assert report.has_drift is False
    assert report.missing_tables == []
    assert report.missing_columns == []


# TC-025-02
# Given no database file exists at a tmp_path location
# When init_db() is run against that path
# Then check_schema_drift reports no drift
def test_freshly_initialized_database_reports_no_drift(tmp_path, monkeypatch):
    # Arrange
    db_path = tmp_path / "fresh.db"
    assert not db_path.exists()
    monkeypatch.setattr("backend.database.engine", _engine(db_path))

    # Act
    init_db()
    report = check_schema_drift(_engine(db_path))

    # Assert
    assert report.has_drift is False


# TC-025-03
# Given a database whose products table has every column except
#   category_key
# When check_schema_drift is called against it
# Then the report has drift
# And one missing column names table "products" and column "category_key"
# And its alter_statement is
#   "ALTER TABLE products ADD COLUMN category_key VARCHAR(32)"
def test_missing_column_is_reported_with_exact_alter_table_statement(tmp_path):
    # Arrange
    engine = _engine(tmp_path / "missing_column.db")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE products ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(512) NOT NULL, "
                "category_is_manual BOOLEAN NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )

    # Act
    report = check_schema_drift(engine)

    # Assert
    assert report.has_drift is True
    assert len(report.missing_columns) == 1
    missing = report.missing_columns[0]
    assert missing.table_name == "products"
    assert missing.column_name == "category_key"
    assert missing.alter_statement == "ALTER TABLE products ADD COLUMN category_key VARCHAR(32)"


# TC-025-05
# Given a database missing two columns (in two different tables) and
#   missing one whole table relative to Base.metadata
# When check_schema_drift is called once
# Then the report's missing_columns has exactly those two entries
# And missing_tables has exactly that one entry
# And no second call was needed to discover any of them
def test_every_difference_is_reported_from_a_single_run(tmp_path):
    # Arrange
    engine = _engine(tmp_path / "multi_drift.db")
    other_tables = [
        t
        for t in Base.metadata.sorted_tables
        if t.name not in ("products", "receipts", "price_history")
    ]
    Base.metadata.create_all(bind=engine, tables=other_tables)
    with engine.begin() as conn:
        # products: missing category_key
        conn.execute(
            text(
                "CREATE TABLE products ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(512) NOT NULL, "
                "category_is_manual BOOLEAN NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        # receipts: missing processed
        conn.execute(
            text(
                "CREATE TABLE receipts ("
                "id INTEGER PRIMARY KEY, "
                "message_id VARCHAR(255) NOT NULL, "
                "received_date DATETIME NOT NULL, "
                "delivery_date DATE, "
                "from_address VARCHAR(255) NOT NULL, "
                "raw_email_text TEXT NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )
        # price_history table intentionally not created at all

    # Act
    report = check_schema_drift(engine)

    # Assert
    assert {t.table_name for t in report.missing_tables} == {"price_history"}
    assert {(c.table_name, c.column_name) for c in report.missing_columns} == {
        ("products", "category_key"),
        ("receipts", "processed"),
    }


# TC-025-06
# Given a database that has every model column plus one extra column
#   ("legacy_note") that no model declares
# When check_schema_drift is called against it
# Then the report has no drift
def test_extra_database_column_not_on_any_model_is_not_reported(tmp_path):
    # Arrange
    engine = _engine(tmp_path / "extra_column.db")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE products ADD COLUMN legacy_note TEXT"))

    # Act
    report = check_schema_drift(engine)

    # Assert
    assert report.has_drift is False


# TC-025-07
# Given a database file missing the products.category_key column
# When main(["--database-url", <that file's URL>]) is called
# Then it returns 1
# And the printed report contains "products", "category_key", and
#   "ALTER TABLE"
def test_cli_reports_drift_and_returns_nonzero(tmp_path, capsys):
    # Arrange
    db_path = tmp_path / "cli_drift.db"
    engine = _engine(db_path)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE products ("
                "id INTEGER PRIMARY KEY, "
                "name VARCHAR(512) NOT NULL, "
                "category_is_manual BOOLEAN NOT NULL, "
                "created_at DATETIME NOT NULL"
                ")"
            )
        )

    # Act
    exit_code = main(["--database-url", f"sqlite:///{db_path}"])
    output = capsys.readouterr().out

    # Assert
    assert exit_code == 1
    assert "products" in output
    assert "category_key" in output
    assert "ALTER TABLE" in output


# TC-025-08
# Given a database file initialized from the current models
# When main(["--database-url", <that file's URL>]) is called
# Then it returns 0
def test_cli_reports_no_drift_and_returns_zero(tmp_path):
    # Arrange
    db_path = tmp_path / "cli_clean.db"
    engine = _engine(db_path)
    Base.metadata.create_all(bind=engine)

    # Act
    exit_code = main(["--database-url", f"sqlite:///{db_path}"])

    # Assert
    assert exit_code == 0
