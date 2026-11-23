
import hmac
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from database.connection import get_connection
from services.report_service import get_all_reports
from services.priority_service import calculate_priority
from services.map_service import display_complaint_map


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Admin Dashboard | JANASHAKTI AI",
    page_icon="🛡️",
    layout="wide",
)


# ==================================================
# ADMINISTRATOR LOGIN
# ==================================================

def admin_login():

    st.title("🛡️ JANASHAKTI AI")
    st.subheader("Administrator Login")

    st.write(
        "Sign in with your administrator credentials "
        "to access the dashboard."
    )

    with st.form("admin_login_form"):

        username = st.text_input(
            "Administrator Username"
        )

        password = st.text_input(
            "Administrator Password",
            type="password",
        )

        submitted = st.form_submit_button(
            "Sign In",
            use_container_width=True,
        )

        if submitted:

            try:
                correct_username = str(
                    st.secrets["admin"]["username"]
                )

                correct_password = str(
                    st.secrets["admin"]["password"]
                )

                username_valid = hmac.compare_digest(
                    username.strip(),
                    correct_username,
                )

                password_valid = hmac.compare_digest(
                    password,
                    correct_password,
                )

                if username_valid and password_valid:

                    st.session_state[
                        "admin_authenticated"
                    ] = True

                    st.rerun()

                else:
                    st.error(
                        "Invalid username or password."
                    )

            except Exception:
                st.error(
                    "Administrator credentials are not configured. "
                    "Please check .streamlit/secrets.toml."
                )


# Authentication check

if not st.session_state.get(
    "admin_authenticated", False
):
    admin_login()
    st.stop()


# ==================================================
# AUTHENTICATED DASHBOARD HEADER
# ==================================================

header_col1, header_col2 = st.columns([5, 1])

with header_col1:

    st.title(
        "🛡️ JANASHAKTI AI — Admin Dashboard"
    )

with header_col2:

    if st.button(
        "Logout",
        use_container_width=True,
    ):

        st.session_state["admin_authenticated"] = False
        st.rerun()

st.write(
    "Monitor community complaints, review AI assessments "
    "and manage administrator verification."
)


# ==================================================
# LOAD REPORTS
# ==================================================

try:

    reports = get_all_reports()

except Exception as error:

    st.error(
        f"Unable to load reports: {error}"
    )

    st.stop()


if not reports:

    st.info(
        "No community reports are available yet."
    )

    st.stop()


df = pd.DataFrame(reports)


# ==================================================
# SAFE DISPLAY VALUES
# ==================================================

def safe_text(value, default=""):
    """Convert database values to clean display text without showing NaN."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in {"nan", "none", "nat"}:
        return default

    return text


# ==================================================
# PRIORITY ASSESSMENT
# ==================================================

def get_report_priority(row):
    """
    Use saved priority values when available.
    Calculate priority for older reports when necessary.
    """

    saved_score = row.get("priority_score")
    saved_level = row.get("priority_level")

    # Use values already saved in SQLite.
    if (
        pd.notna(saved_score)
        and pd.notna(saved_level)
        and str(saved_level).strip()
    ):
        return pd.Series({
            "priority_score": int(saved_score),
            "priority_level": str(saved_level),
        })

    urgency = row.get("ai_urgency")
    impact = row.get("ai_impact_level")
    households = row.get("affected_households")

    # Do not classify reports without AI analysis as Low.
    if (
        pd.isna(urgency)
        or pd.isna(impact)
        or str(urgency).strip() in ("", "Unknown")
        or str(impact).strip() in ("", "Unknown")
    ):
        return pd.Series({
            "priority_score": None,
            "priority_level": "Not Assessed",
        })

    if pd.isna(households):
        households = None

    result = calculate_priority(
        urgency=urgency,
        impact=impact,
        affected_households=households,
    )

    return pd.Series({
        "priority_score": result["priority_score"],
        "priority_level": result["priority_level"],
    })


priority_data = df.apply(
    get_report_priority,
    axis=1,
)

df["priority_score"] = (
    priority_data["priority_score"]
)

df["priority_level"] = (
    priority_data["priority_level"]
)

df["priority_score"] = pd.to_numeric(
    df["priority_score"],
    errors="coerce",
)


# ==================================================
# PRIORITY SORTING
# ==================================================

priority_order = {
    "Critical": 4,
    "High": 3,
    "Medium": 2,
    "Low": 1,
    "Not Assessed": 0,
}

df["priority_order"] = (
    df["priority_level"]
    .map(priority_order)
    .fillna(0)
)

df = df.sort_values(
    by=["priority_order", "priority_score"],
    ascending=[False, False],
    na_position="last",
)


# ==================================================
# DASHBOARD METRICS
# ==================================================

total_reports = len(df)

# Pending and reviewed reports.

if "reviewed_at" in df.columns:

    review_timestamps = (
        df["reviewed_at"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    pending_reviews = (
        review_timestamps.eq("").sum()
    )

    reviewed_reports = (
        review_timestamps.ne("").sum()
    )

else:

    pending_reviews = total_reports
    reviewed_reports = 0


# High urgency reports.

high_urgency = (
    df["ai_urgency"]
    .fillna("")
    .eq("High")
    .sum()
    if "ai_urgency" in df.columns
    else 0
)


# Resolved reports.

resolved = (
    df["status"]
    .fillna("")
    .eq("Resolved")
    .sum()
    if "status" in df.columns
    else 0
)


# Priority counts.

critical_count = (
    df["priority_level"]
    .eq("Critical")
    .sum()
)

high_priority_count = (
    df["priority_level"]
    .eq("High")
    .sum()
)

medium_priority_count = (
    df["priority_level"]
    .eq("Medium")
    .sum()
)

low_priority_count = (
    df["priority_level"]
    .eq("Low")
    .sum()
)

not_assessed_count = (
    df["priority_level"]
    .eq("Not Assessed")
    .sum()
)


# ==================================================
# SYSTEM OVERVIEW
# ==================================================

st.subheader("System Overview")

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric(
    "Total Reports",
    total_reports,
)

col2.metric(
    "Pending Human Reviews",
    int(pending_reviews),
)

col3.metric(
    "Reviewed Reports",
    int(reviewed_reports),
)

col4.metric(
    "High Urgency",
    int(high_urgency),
)

col5.metric(
    "Resolved Reports",
    int(resolved),
)

st.divider()


# ==================================================
# PRIORITY OVERVIEW
# ==================================================

st.subheader("Complaint Priority Overview")

p1, p2, p3, p4 = st.columns(4)

p1.metric(
    "Critical Priority",
    int(critical_count),
)

p2.metric(
    "High Priority",
    int(high_priority_count),
)

p3.metric(
    "Medium Priority",
    int(medium_priority_count),
)

p4.metric(
    "Low Priority",
    int(low_priority_count),
)

if not_assessed_count > 0:

    st.info(
        f"{not_assessed_count} report(s) have not yet "
        "received an AI priority assessment."
    )

st.caption(
    "Priority is calculated using reported urgency, "
    "community impact and affected household counts. "
    "It is rule-based decision support, not an official "
    "emergency assessment. Human review is required."
)

st.divider()


# ==================================================
# CRITICAL COMPLAINT ALERT
# ==================================================

st.subheader("Critical Complaint Alerts")

critical_reports = df[
    df["priority_level"] == "Critical"
]

if not critical_reports.empty:

    st.error(
        f"⚠️ {len(critical_reports)} critical-priority "
        "complaint(s) require prompt human review."
    )

    alert_columns = [
        column
        for column in [
            "report_id",
            "category",
            "locality",
            "priority_score",
            "ai_urgency",
            "status",
            "verification_status",
        ]
        if column in critical_reports.columns
    ]

    st.dataframe(
        critical_reports[alert_columns],
        use_container_width=True,
        hide_index=True,
    )

else:

    st.success(
        "No critical-priority complaints currently recorded."
    )

st.divider()


# ==================================================
# COMMUNITY ISSUE ANALYTICS
# ==================================================

st.subheader("Community Issue Analytics")

left, right = st.columns(2)

with left:

    st.markdown(
        "**Reports by Category**"
    )

    if "category" in df.columns:

        category_data = (
            df["category"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(category_data)


with right:

    st.markdown(
        "**Reports by Status**"
    )

    if "status" in df.columns:

        status_data = (
            df["status"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(status_data)


st.divider()


# ==================================================
# COMMUNITY ISSUE MAP
# ==================================================

st.subheader("Community Issue Map")

st.write(
    "View the geographical distribution of all "
    "registered community complaints."
)

try:

    display_complaint_map(
        df.to_dict(orient="records")
    )

except Exception as error:

    st.warning(
        f"Unable to display the complaint map: {error}"
    )

st.divider()


# ==================================================
# COMPLAINT MANAGEMENT AND FILTERS
# ==================================================

st.subheader("Complaint Management")

search = st.text_input(
    "Search by Report ID or Locality",
    placeholder="Enter report ID or locality...",
)


# Priority filter.

priority_filter = st.selectbox(
    "Filter by Priority Level",
    [
        "All Priorities",
        "Critical",
        "High",
        "Medium",
        "Low",
        "Not Assessed",
    ],
)


# Status filter.

status_options = ["All Statuses"]

if "status" in df.columns:

    status_options.extend(
        sorted(
            df["status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
    )

status_filter = st.selectbox(
    "Filter by Complaint Status",
    status_options,
)


# Start filtering.

filtered = df.copy()


# Search filter.

if search.strip():

    query = search.strip()

    report_mask = (
        filtered["report_id"]
        .fillna("")
        .astype(str)
        .str.contains(
            query,
            case=False,
            regex=False,
        )
    )

    locality_mask = (
        filtered["locality"]
        .fillna("")
        .astype(str)
        .str.contains(
            query,
            case=False,
            regex=False,
        )
    )

    filtered = filtered[
        report_mask | locality_mask
    ]


# Priority filter.

if priority_filter != "All Priorities":

    filtered = filtered[
        filtered["priority_level"] == priority_filter
    ]


# Status filter.

if status_filter != "All Statuses":

    filtered = filtered[
        filtered["status"] == status_filter
    ]


# Highest priority first.

filtered = filtered.sort_values(
    by=["priority_order", "priority_score"],
    ascending=[False, False],
    na_position="last",
)


# ==================================================
# COMPLAINT TABLE
# ==================================================

display_columns = [
    "report_id",
    "category",
    "locality",
    "ai_urgency",
    "ai_impact_level",
    "affected_households",
    "priority_level",
    "priority_score",
    "status",
    "verification_status",
]


available_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]


st.dataframe(
    filtered[available_columns],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"{len(filtered)} report(s) displayed. "
    "Sorted by priority level and score."
)

st.divider()


# ==================================================
# ADMINISTRATOR REVIEW
# ==================================================

st.subheader("Administrator Review")

report_ids = (
    filtered["report_id"]
    .dropna()
    .tolist()
)


if not report_ids:

    st.info(
        "No reports match your selected filters."
    )

else:

    selected_id = st.selectbox(
        "Select a report for administrator review",
        report_ids,
    )

    selected = filtered[
        filtered["report_id"] == selected_id
    ].iloc[0]


    # --------------------------------------------------
    # SELECTED REPORT DETAILS
    # --------------------------------------------------

    st.markdown(
        f"### Report: {selected_id}"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Category:**",
            safe_text(selected.get("category"), "Unknown"),
        )

        st.write(
            "**State:**",
            safe_text(selected.get("state"), "Unknown"),
        )

        st.write(
            "**District:**",
            safe_text(selected.get("district"), "Unknown"),
        )

        st.write(
            "**Locality:**",
            safe_text(selected.get("locality"), "Unknown"),
        )

        st.write(
            "**Description:**",
            safe_text(selected.get("description"), ""),
        )

    with col2:

        st.write(
            "**AI Urgency:**",
            safe_text(selected.get("ai_urgency"), "Not available"),
        )

        st.write(
            "**AI Impact:**",
            safe_text(selected.get("ai_impact_level"), "Not available"),
        )

        st.write(
            "**Affected Households:**",
            safe_text(selected.get("affected_households"), "Unknown"),
        )

        st.write(
            "**Current Status:**",
            safe_text(selected.get("status"), "Submitted"),
        )

        st.write(
            "**Current Verification:**",
            safe_text(selected.get("verification_status"), "Pending"),
        )


    # --------------------------------------------------
    # PRIORITY DETAILS
    # --------------------------------------------------

    st.divider()

    st.markdown(
        "### Complaint Priority Assessment"
    )

    priority_col1, priority_col2 = st.columns(2)

    with priority_col1:

        score = selected.get("priority_score")

        if pd.notna(score):

            st.metric(
                "Priority Score",
                f"{int(score)}/100",
            )

        else:

            st.metric(
                "Priority Score",
                "Not Available",
            )

    with priority_col2:

        st.metric(
            "Priority Level",
            selected["priority_level"],
        )

    if selected["priority_level"] == "Critical":

        st.error(
            "Critical priority: Prompt human review is recommended."
        )

    elif selected["priority_level"] == "High":

        st.warning(
            "High priority: Timely administrator attention is recommended."
        )

    elif selected["priority_level"] == "Medium":

        st.info(
            "Medium priority: Review through the normal process."
        )

    elif selected["priority_level"] == "Low":

        st.success(
            "Low priority score: Continue routine complaint review."
        )

    else:

        st.info(
            "AI priority assessment is not available for this report."
        )

    st.caption(
        "This score is generated from predefined rules. "
        "It does not independently establish the severity "
        "or real-world safety of a complaint."
    )


    # --------------------------------------------------
    # ADMINISTRATOR REVIEW FORM
    # --------------------------------------------------

    st.divider()

    with st.form("admin_review_form"):

        st.markdown(
            "#### Update Complaint"
        )

        status_options = [
            "Submitted",
            "Under Investigation",
            "Resolved",
        ]

        current_status = safe_text(
            selected.get("status"),
            "Submitted",
        )

        status_index = (
            status_options.index(current_status)
            if current_status in status_options
            else 0
        )

        new_status = st.selectbox(
            "Complaint Status",
            status_options,
            index=status_index,
        )


        verification_options = [
            "Pending",
            "Verified",
            "Rejected",
        ]

        current_verification = safe_text(
            selected.get("verification_status"),
            "Pending",
        )

        verification_index = (
            verification_options.index(current_verification)
            if current_verification in verification_options
            else 0
        )

        new_verification = st.selectbox(
            "Real-world Verification",
            verification_options,
            index=verification_index,
        )


        reviewed_by = st.text_input(
            "Reviewed By",
            value=safe_text(
                selected.get("reviewed_by"),
                "Administrator",
            ),
        )


        review_note = st.text_area(
            "Administrator Review Note",
            value=safe_text(
                selected.get("admin_review_note"),
                "",
            ),
            placeholder="Enter inspection findings or review comments...",
            max_chars=2000,
        )


        submitted = st.form_submit_button(
            "Save Admin Review",
            use_container_width=True,
        )


        if submitted:

            if not reviewed_by.strip():

                st.error(
                    "Please enter the administrator name."
                )

            elif not review_note.strip():

                st.error(
                    "Please enter an administrator review note."
                )

            else:

                try:

                    now = datetime.now(
                        timezone.utc
                    ).isoformat(timespec="seconds")


                    with get_connection() as connection:

                        existing_columns = {
                            row["name"]
                            for row in connection.execute(
                                "PRAGMA table_info(reports)"
                            ).fetchall()
                        }


                        updates = {
                            "status": new_status,
                            "verification_status": new_verification,
                            "reviewed_by": reviewed_by.strip(),
                            "admin_review_note": review_note.strip(),
                            "reviewed_at": now,
                            "updated_at": now,
                        }


                        available_updates = {
                            key: value
                            for key, value in updates.items()
                            if key in existing_columns
                        }


                        if not available_updates:

                            raise ValueError(
                                "No supported review columns were found."
                            )


                        set_clause = ", ".join(
                            f"{column} = ?"
                            for column in available_updates
                        )


                        values = list(
                            available_updates.values()
                        )

                        values.append(selected_id)


                        cursor = connection.execute(
                            f"""
                            UPDATE reports
                            SET {set_clause}
                            WHERE report_id = ?
                            """,
                            values,
                        )


                        if cursor.rowcount == 0:

                            raise ValueError(
                                "Report was not found."
                            )


                    st.success(
                        "Administrator review saved successfully!"
                    )

                    st.rerun()


                except Exception as error:

                    st.error(
                        f"Could not save administrator review: {error}"
                    )


# ==================================================
# RECENT ADMINISTRATOR ACTIVITY
# ==================================================

st.divider()

st.subheader(
    "Recent Administrator Activity"
)


if "reviewed_at" in df.columns:

    reviewed = df[
        df["reviewed_at"].notna()
        & df["reviewed_at"]
        .astype(str)
        .str.strip()
        .ne("")
    ].copy()


    if not reviewed.empty:

        activity_columns = [
            column
            for column in [
                "report_id",
                "reviewed_by",
                "reviewed_at",
                "status",
                "verification_status",
                "admin_review_note",
                "priority_level",
                "priority_score",
            ]
            if column in reviewed.columns
        ]


        reviewed = reviewed.sort_values(
            "reviewed_at",
            ascending=False,
        )


        # FIX: Avoid PyArrow mixed-type conversion errors.
        # Convert display values to strings safely.

        activity_display = (
            reviewed[activity_columns]
            .head(10)
            .copy()
        )

        for column in activity_display.columns:

            activity_display[column] = (
                activity_display[column].map(
                    lambda value: safe_text(value, "")
                )
            )


        st.dataframe(
            activity_display,
            width="stretch",
            hide_index=True,
        )


    else:

        st.info(
            "No administrator reviews have been recorded yet."
        )

else:

    st.info(
        "Administrator activity is not available in the database."
    )


# ==================================================
# DASHBOARD FOOTER
# ==================================================

st.divider()

st.caption(
    "JANASHAKTI AI | Community Intelligence and "
    "Administrator Monitoring System"
)
