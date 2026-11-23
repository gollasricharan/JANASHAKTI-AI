
import json
from datetime import datetime, timezone
from uuid import uuid4

from database.connection import (
    get_connection,
    initialize_database,
)


def create_report(
    category,
    state,
    district,
    locality,
    description,
):
    """Validate and save a new community report."""

    category = (category or "").strip()
    state = (state or "").strip()
    district = (district or "").strip()
    locality = (locality or "").strip()
    description = (description or "").strip()

    if not category:
        raise ValueError("Please select a problem category.")

    if not state or not district or not locality:
        raise ValueError(
            "Please enter the state, district and locality."
        )

    if len(description) < 10:
        raise ValueError(
            "Please provide a description of at least 10 characters."
        )

    if len(description) > 5000:
        raise ValueError(
            "The description cannot exceed 5000 characters."
        )

    initialize_database()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report_id = f"JAN-{uuid4().hex[:10].upper()}"

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO reports (
                report_id, category, state, district, locality,
                description, status, created_at, updated_at,
                verification_status, human_review_required
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                category,
                state,
                district,
                locality,
                description,
                "Submitted",
                now,
                now,
                "Pending",
                1,
            ),
        )

    return report_id


def save_report_analysis(report_id, result):
    """Save AI analysis without changing real-world verification."""

    if not report_id or not result:
        raise ValueError("Report ID and analysis result are required.")

    if not result.get("success"):
        raise ValueError("Cannot save an unsuccessful AI analysis.")

    classification = result.get("classification") or {}
    verification = result.get("verification") or {}
    impact = result.get("impact_assessment") or {}
    priority = result.get("priority_assessment") or {}
    sources = result.get("sources") or []

    verification_score = verification.get("verification_score")

    if verification_score is not None:
        verification_score = max(
            0.0, min(1.0, float(verification_score))
        )

    priority_score = priority.get("priority_score")
    priority_level = priority.get("priority_level")

    if priority_score is not None:
        priority_score = int(priority_score)

        if not 0 <= priority_score <= 100:
            raise ValueError(
                "Priority score must be between 0 and 100."
            )

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE reports
            SET
                ai_category = ?,
                ai_urgency = ?,
                ai_impact_level = ?,
                affected_households = ?,
                ai_response = ?,
                ai_sources = ?,
                ai_verification_score = ?,
                ai_verification_result = ?,
                ai_summary = ?,
                ai_severity = ?,
                priority_score = ?,
                priority_level = ?,
                human_review_required = 1,
                updated_at = ?
            WHERE report_id = ?
            """,
            (
                classification.get("category"),
                classification.get("urgency"),
                impact.get("impact_level"),
                impact.get("affected_households"),
                result.get("ai_response", ""),
                json.dumps(sources, ensure_ascii=False),
                verification_score,
                json.dumps(verification, ensure_ascii=False),
                result.get("ai_response", "")[:500],
                impact.get("impact_level"),
                priority_score,
                priority_level,
                now,
                report_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No report found with reference ID {report_id}."
            )


def update_admin_review(
    report_id,
    status,
    verification_status,
    review_note,
    reviewed_by="Administrator",
):
    """Update report progress and real-world verification."""

    allowed_statuses = {
        "Submitted",
        "Under Investigation",
        "Resolved",
    }

    allowed_verification = {
        "Pending",
        "Verified",
        "Rejected",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid report status.")

    if verification_status not in allowed_verification:
        raise ValueError("Invalid real-world verification status.")

    if not report_id:
        raise ValueError("Report ID is required.")

    review_note = (review_note or "").strip()
    reviewed_by = (reviewed_by or "Administrator").strip()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE reports
            SET
                status = ?,
                verification_status = ?,
                admin_review_note = ?,
                reviewed_at = ?,
                reviewed_by = ?,
                human_review_required = 1,
                updated_at = ?
            WHERE report_id = ?
            """,
            (
                status,
                verification_status,
                review_note,
                now,
                reviewed_by,
                now,
                report_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No report found with reference ID {report_id}."
            )


def get_all_reports():
    """Return reports, newest first."""

    initialize_database()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM reports
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_report_by_id(report_id):
    """Retrieve one report using its reference ID."""

    initialize_database()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM reports
            WHERE report_id = ?
            """,
            (report_id,),
        ).fetchone()

    return dict(row) if row else None


def get_report_statistics():
    """Calculate dashboard statistics from stored reports."""

    initialize_database()

    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) FROM reports"
        ).fetchone()[0]

        awaiting_review = connection.execute(
            """
            SELECT COUNT(*) FROM reports
            WHERE status = 'Submitted'
            """
        ).fetchone()[0]

        under_investigation = connection.execute(
            """
            SELECT COUNT(*) FROM reports
            WHERE status = 'Under Investigation'
            """
        ).fetchone()[0]

        resolved = connection.execute(
            """
            SELECT COUNT(*) FROM reports
            WHERE status = 'Resolved'
            """
        ).fetchone()[0]

    return {
        "total": total,
        "awaiting_review": awaiting_review,
        "under_investigation": under_investigation,
        "resolved": resolved,
    }
