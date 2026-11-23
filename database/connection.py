
import sqlite3
from pathlib import Path
from contextlib import contextmanager


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "janshakti.db"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

@contextmanager
def get_connection():
    """
    Create, manage and safely close a database connection.
    Automatically commits successful operations and
    rolls back failed operations.
    """

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

def initialize_database():
    """
    Create the reports table if necessary and safely
    add any missing columns without deleting existing data.
    """

    with get_connection() as connection:

        # Create reports table if it does not exist.

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT UNIQUE,
                category TEXT NOT NULL,
                state TEXT,
                district TEXT,
                locality TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ai_summary TEXT,
                ai_severity TEXT,
                verification_status TEXT NOT NULL DEFAULT 'Pending'
            )
            """
        )

        # --------------------------------------------------
        # ADDITIONAL DATABASE COLUMNS
        # --------------------------------------------------

        new_columns = {

            # AI classification fields.
            "ai_category": "TEXT",
            "ai_urgency": "TEXT",
            "ai_impact_level": "TEXT",

            # Community impact fields.
            "affected_households": "INTEGER",

            # AI response and evidence fields.
            "ai_response": "TEXT",
            "ai_sources": "TEXT",
            "ai_verification_score": "REAL",
            "ai_verification_result": "TEXT",

            # Human review.
            "human_review_required": "INTEGER DEFAULT 1",

            # Priority assessment.
            "priority_score": "INTEGER",
            "priority_level": "TEXT",

            # Administrator review.
            "admin_review_note": "TEXT",
            "reviewed_at": "TEXT",
            "reviewed_by": "TEXT",
        }

        # Get existing column names.

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(reports)"
            ).fetchall()
        }

        # Add only columns that are missing.

        for column_name, column_type in new_columns.items():

            if column_name not in existing_columns:

                connection.execute(
                    f"""
                    ALTER TABLE reports
                    ADD COLUMN {column_name} {column_type}
                    """
                )

        # Do not reset verification_status here.
        # Real-world verification decisions made by
        # administrators must remain unchanged.
