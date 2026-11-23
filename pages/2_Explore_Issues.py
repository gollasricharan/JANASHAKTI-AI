
import json
import streamlit as st
import pandas as pd

from services.report_service import (
    get_all_reports,
    update_admin_review,
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="Explore Issues | JANASHAKTI AI",
    page_icon="🔎",
    layout="wide",
)


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def safe_text(value, default="Not available"):
    """Convert database values into clean display text."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if text.lower() in {"", "nan", "none", "nat"}:
        return default

    return text


def parse_json(value):
    """Safely parse JSON stored in the database."""

    if isinstance(value, (dict, list)):
        return value

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


# ==================================================
# PAGE HEADER
# ==================================================

st.title("🔎 Explore Community Issues")

st.write(
    "Explore submitted community reports, AI assessments "
    "and administrator review decisions."
)


# ==================================================
# ADMIN AUTHENTICATION STATE
# ==================================================

is_admin_logged_in = st.session_state.get(
    "admin_authenticated",
    False,
)


# ==================================================
# LOAD REPORTS
# ==================================================

try:

    reports = get_all_reports()

except Exception as error:

    st.error(
        f"Unable to load community reports: {error}"
    )

    st.stop()


if not reports:

    st.info(
        "No community reports have been submitted yet."
    )

    st.stop()


df = pd.DataFrame(reports)


# ==================================================
# ENSURE EXPECTED COLUMNS EXIST
# ==================================================

expected_columns = [
    "report_id",
    "category",
    "status",
    "locality",
    "description",
    "ai_category",
    "ai_urgency",
    "ai_impact_level",
    "verification_status",
    "state",
    "district",
    "created_at",
    "affected_households",
    "ai_response",
    "ai_sources",
    "ai_verification_result",
    "reviewed_at",
    "reviewed_by",
    "admin_review_note",
    "human_review_required",
]

for column in expected_columns:

    if column not in df.columns:
        df[column] = None


# ==================================================
# FILTERS
# ==================================================

col1, col2, col3 = st.columns(3)

with col1:

    categories = sorted(
        df["category"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    category_filter = st.selectbox(
        "Filter by category",
        ["All"] + categories,
    )


with col2:

    statuses = sorted(
        df["status"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    status_filter = st.selectbox(
        "Filter by report status",
        ["All"] + statuses,
    )


with col3:

    search = st.text_input(
        "Search reports",
        placeholder="Search locality or report ID",
    )


filtered = df.copy()


# Category filter

if category_filter != "All":

    filtered = filtered[
        filtered["category"] == category_filter
    ]


# Status filter

if status_filter != "All":

    filtered = filtered[
        filtered["status"] == status_filter
    ]


# Search filter

if search.strip():

    query = search.strip()

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

    description_mask = (
        filtered["description"]
        .fillna("")
        .astype(str)
        .str.contains(
            query,
            case=False,
            regex=False,
        )
    )

    filtered = filtered[
        locality_mask | report_mask | description_mask
    ]


st.divider()


# ==================================================
# DASHBOARD STATISTICS
# ==================================================

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Total Reports",
        len(df),
    )


with col2:

    st.metric(
        "Filtered Reports",
        len(filtered),
    )


with col3:

    high_impact = (
        filtered["ai_impact_level"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("high")
        .sum()
    )

    st.metric(
        "High Impact",
        int(high_impact),
    )


with col4:

    pending = (
        filtered["verification_status"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("pending")
        .sum()
    )

    st.metric(
        "Pending Verification",
        int(pending),
    )


st.divider()


# ==================================================
# COMMUNITY REPORTS TABLE
# ==================================================

st.subheader("Community Reports")

st.caption(
    f"{len(filtered)} report(s) found."
)

display_columns = [
    "report_id",
    "category",
    "locality",
    "status",
    "ai_category",
    "ai_urgency",
    "ai_impact_level",
    "verification_status",
]

available_columns = [
    column
    for column in display_columns
    if column in filtered.columns
]

display_df = filtered[available_columns].copy()

display_df = display_df.fillna("Not available")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
)

st.divider()


# ==================================================
# DETAILED REPORT ANALYSIS
# ==================================================

st.subheader("Detailed Report Analysis")

available_ids = (
    filtered["report_id"]
    .dropna()
    .astype(str)
    .tolist()
)


if not available_ids:

    st.info(
        "No reports match the selected filters."
    )

else:

    selected_id = st.selectbox(
        "Select a report to view its details",
        available_ids,
    )

    selected = filtered[
        filtered["report_id"].astype(str) == selected_id
    ].iloc[0]


    # --------------------------------------------------
    # REPORT DETAILS
    # --------------------------------------------------

    st.markdown(
        f"### Report: {selected_id}"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Original Category:**",
            safe_text(selected.get("category")),
        )

        st.write(
            "**State:**",
            safe_text(selected.get("state")),
        )

        st.write(
            "**District:**",
            safe_text(selected.get("district")),
        )

        st.write(
            "**Locality:**",
            safe_text(selected.get("locality")),
        )


    with col2:

        st.write(
            "**Report Status:**",
            safe_text(selected.get("status"), "Submitted"),
        )

        st.write(
            "**Real-world Verification:**",
            safe_text(
                selected.get("verification_status"),
                "Pending",
            ),
        )

        st.write(
            "**Submitted At:**",
            safe_text(selected.get("created_at")),
        )


    st.write("**Complaint Description:**")

    st.info(
        safe_text(
            selected.get("description"),
            "No description available.",
        )
    )


    st.divider()


    # --------------------------------------------------
    # AI ASSESSMENT
    # --------------------------------------------------

    st.markdown(
        "### JANASHAKTI AI Assessment"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "AI Category",
            safe_text(
                selected.get("ai_category"),
                "Not available",
            ),
        )


    with col2:

        st.metric(
            "Urgency",
            safe_text(
                selected.get("ai_urgency"),
                "Unknown",
            ),
        )


    with col3:

        st.metric(
            "Community Impact",
            safe_text(
                selected.get("ai_impact_level"),
                "Unknown",
            ),
        )


    households = selected.get("affected_households")

    if households is None:

        households = "Not provided"

    else:

        try:
            if pd.isna(households):
                households = "Not provided"
        except (TypeError, ValueError):
            pass

    st.write(
        "**Affected Households:**",
        households,
    )


    # --------------------------------------------------
    # AI-GENERATED GUIDANCE
    # --------------------------------------------------

    st.markdown(
        "### AI-Generated Guidance"
    )

    ai_response = safe_text(
        selected.get("ai_response"),
        "",
    )

    if ai_response:

        st.write(ai_response)

    else:

        st.info(
            "AI analysis is not available."
        )


    # --------------------------------------------------
    # SUPPORTING DOCUMENTS
    # --------------------------------------------------

    st.markdown(
        "### Supporting Reference Documents"
    )

    sources = parse_json(
        selected.get("ai_sources")
    )

    if isinstance(sources, list) and sources:

        for source in sources:

            if not isinstance(source, dict):
                continue

            document = safe_text(
                source.get("document"),
                "Unknown document",
            )

            similarity = source.get(
                "similarity",
                0,
            )

            try:

                similarity = float(similarity)

            except (TypeError, ValueError):

                similarity = 0.0

            st.write(
                f"- {document} "
                f"(Relevance: {similarity:.2f})"
            )

    else:

        st.info(
            "No supporting documents were saved."
        )


    # --------------------------------------------------
    # AI EVIDENCE VERIFICATION
    # --------------------------------------------------

    st.markdown(
        "### AI Evidence Verification"
    )

    verification = parse_json(
        selected.get("ai_verification_result")
    )

    if isinstance(verification, dict):

        st.write(
            "**Evidence matching result:**",
            safe_text(
                verification.get("status"),
                "Unknown",
            ),
        )

        try:

            score = float(
                verification.get(
                    "verification_score",
                    0,
                )
            )

        except (TypeError, ValueError):

            score = 0.0

        score = max(
            0.0,
            min(1.0, score),
        )

        st.progress(score)

        st.write(
            f"**Text Matching Score:** {score:.0%}"
        )

        if verification.get("unsupported_claims"):

            st.warning(
                "Some AI-generated claims need further checking."
            )

    else:

        st.info(
            "AI evidence verification is not available."
        )


    st.caption(
        "AI evidence matching checks text against reference "
        "documents. It does not independently verify the "
        "real-world complaint."
    )


    st.divider()


    # ==================================================
    # ADMINISTRATOR REVIEW
    # ==================================================

    if not is_admin_logged_in:

        st.info(
            "Administrator login is required to update "
            "report progress or verification status."
        )

        st.caption(
            "You can still explore community reports "
            "and view AI assessments."
        )

    else:

        st.header(
            "Administrator Review"
        )

        st.write(
            "Review the complaint and update its official "
            "progress and real-world verification status."
        )

        current_status = safe_text(
            selected.get("status"),
            "Submitted",
        )

        current_verification = safe_text(
            selected.get("verification_status"),
            "Pending",
        )

        status_options = [
            "Submitted",
            "Under Investigation",
            "Resolved",
        ]

        verification_options = [
            "Pending",
            "Verified",
            "Rejected",
        ]

        with st.form(
            f"admin_review_form_{selected_id}"
        ):

            new_status = st.selectbox(
                "Report Progress",
                status_options,
                index=(
                    status_options.index(current_status)
                    if current_status in status_options
                    else 0
                ),
            )

            new_verification = st.selectbox(
                "Real-world Verification",
                verification_options,
                index=(
                    verification_options.index(
                        current_verification
                    )
                    if current_verification in verification_options
                    else 0
                ),
            )

            admin_name = st.text_input(
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
                placeholder=(
                    "Enter inspection findings or review observations."
                ),
                max_chars=2000,
            )

            save_review = st.form_submit_button(
                "Save Admin Review",
                use_container_width=True,
            )


        if save_review:

            if not admin_name.strip():

                st.error(
                    "Please enter the administrator name."
                )

            elif not review_note.strip():

                st.error(
                    "Please enter an administrator review note."
                )

            else:

                try:

                    update_admin_review(
                        report_id=selected_id,
                        status=new_status,
                        verification_status=new_verification,
                        review_note=review_note.strip(),
                        reviewed_by=admin_name.strip(),
                    )

                    st.success(
                        f"Review saved successfully for {selected_id}."
                    )

                    st.rerun()

                except Exception as error:

                    st.error(
                        f"Unable to save the review: {error}"
                    )


    # ==================================================
    # ADMINISTRATOR REVIEW HISTORY
    # ==================================================

    if is_admin_logged_in:

        st.divider()

        st.subheader(
            "Administrator Review History"
        )

        st.write(
            "**Last Reviewed At:**",
            safe_text(
                selected.get("reviewed_at"),
                "Not reviewed yet",
            ),
        )

        st.write(
            "**Reviewed By:**",
            safe_text(
                selected.get("reviewed_by"),
                "Not available",
            ),
        )

        previous_note = safe_text(
            selected.get("admin_review_note"),
            "",
        )

        if previous_note:

            st.info(
                f"**Previous Admin Note:** {previous_note}"
            )

        human_review = selected.get(
            "human_review_required",
            1,
        )

        try:

            human_review_required = (
                bool(int(human_review))
                if pd.notna(human_review)
                else True
            )

        except (TypeError, ValueError):

            human_review_required = True

        if human_review_required:

            st.warning(
                "Human review is required before official action."
            )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "JANASHAKTI AI | Community Intelligence "
    "and Community Issue Exploration System"
)
