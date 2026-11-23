
import json
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

from services.report_service import get_all_reports
from services.ai_service import analyze_complaint
from services.priority_service import calculate_priority
from rag.rag_service import retrieve_evidence
from rag.answer_generator import generate_answer


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Insights | JANASHAKTI AI",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
    }
    .section-subtitle {
        color: #9CA3AF;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_text(value, default="Not available"):
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    value = str(value).strip()
    return value if value else default


def create_json_download(data, filename):
    st.download_button(
        "Download JSON",
        data=json.dumps(
            data,
            indent=4,
            ensure_ascii=False,
            default=str,
        ),
        file_name=filename,
        mime="application/json",
        use_container_width=True,
    )


def normalize_location(value):
    """Create a consistent comparison key for a location component."""
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = unicodedata.normalize("NFKD", str(value)).casefold()
    text = "".join(
        char for char in text
        if unicodedata.category(char) not in ("Cf", "Cc", "Mn")
    )
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_location_display(value):
    """Clean display text while preserving original capitalization."""
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    text = unicodedata.normalize("NFKC", str(value))
    text = "".join(
        char for char in text
        if unicodedata.category(char) not in ("Cf", "Cc")
    )
    return re.sub(r"\s+", " ", text).strip()


def group_location_data(data, value_column):
    """
    Group by normalized location components and merge duplicate
    final display labels so the chart never shows duplicate bars.
    """

    output_columns = [
        "Location", "Locality", "District", "State", value_column
    ]

    if data.empty:
        return pd.DataFrame(columns=output_columns)

    work = data.copy()

    for column in ("locality", "district", "state"):
        if column not in work.columns:
            work[column] = ""

        work[f"_{column}_display"] = work[column].apply(
            clean_location_display
        )

        work[f"_{column}_key"] = work[column].apply(
            normalize_location
        )

    work = work[work["_locality_key"] != ""].copy()

    if work.empty:
        return pd.DataFrame(columns=output_columns)

    # First grouping: normalize locality, district and state.
    grouped = (
        work.groupby(
            ["_locality_key", "_district_key", "_state_key"],
            sort=False,
            dropna=False,
            as_index=False,
        )
        .agg(
            **{
                value_column: (value_column, "sum"),
                "Locality": ("_locality_display", "first"),
                "District": ("_district_display", "first"),
                "State": ("_state_display", "first"),
            }
        )
    )

    for column in ("Locality", "District", "State"):
        grouped[column] = grouped[column].replace("", "Unknown")

    grouped["Location"] = grouped.apply(
        lambda row: ", ".join(
            value
            for value in (
                row["Locality"],
                row["District"] if row["District"] != "Unknown" else "",
                row["State"] if row["State"] != "Unknown" else "",
            )
            if value
        ),
        axis=1,
    )

    # Second grouping: merge identical final display labels.
    grouped["_final_location_key"] = grouped["Location"].apply(
        normalize_location
    )

    grouped = (
        grouped.groupby(
            "_final_location_key",
            sort=False,
            as_index=False,
        )
        .agg(
            **{
                value_column: (value_column, "sum"),
                "Location": ("Location", "first"),
                "Locality": ("Locality", "first"),
                "District": ("District", "first"),
                "State": ("State", "first"),
            }
        )
    )

    return (
        grouped[output_columns]
        .sort_values(value_column, ascending=False)
        .reset_index(drop=True)
    )


def get_category_counts(data):

    if data.empty:
        return pd.DataFrame(columns=["Category", "Reports"])

    return (
        data["category"]
        .fillna("Unspecified")
        .value_counts()
        .rename_axis("Category")
        .reset_index(name="Reports")
    )


def get_status_counts(data):

    if data.empty:
        return pd.DataFrame(columns=["Status", "Reports"])

    return (
        data["status"]
        .fillna("Unknown")
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Reports")
    )


def get_location_counts(data):

    if data.empty:
        return pd.DataFrame(
            columns=[
                "Location",
                "Locality",
                "District",
                "State",
                "Reports",
            ]
        )

    location_data = data.copy()
    location_data["Reports"] = 1

    return group_location_data(
        location_data,
        "Reports",
    )


def calculate_report_priority(row):
    """Use saved priority or calculate when inputs are valid."""

    valid_levels = {
        "Critical",
        "High",
        "Medium",
        "Low",
    }

    saved_level = safe_text(
        row.get("priority_level"),
        "",
    ).strip().title()

    saved_score = row.get("priority_score")

    try:
        saved_score = float(saved_score)

        if pd.isna(saved_score) or not 0 <= saved_score <= 100:
            saved_score = None

        elif saved_score.is_integer():
            saved_score = int(saved_score)

    except (TypeError, ValueError):
        saved_score = None

    if saved_level in valid_levels:
        return pd.Series({
            "priority_score": saved_score,
            "priority_level": saved_level,
        })

    if saved_level == "Not Assessed":
        return pd.Series({
            "priority_score": None,
            "priority_level": "Not Assessed",
        })

    urgency = safe_text(
        row.get("ai_urgency"),
        "",
    ).strip().title()

    impact = safe_text(
        row.get("ai_impact_level"),
        "",
    ).strip().title()

    if urgency not in {"High", "Medium", "Low"}:
        return pd.Series({
            "priority_score": None,
            "priority_level": "Not Assessed",
        })

    if impact not in {"High", "Medium", "Low"}:
        return pd.Series({
            "priority_score": None,
            "priority_level": "Not Assessed",
        })

    households = row.get("affected_households")

    try:
        if pd.isna(households):
            households = None
    except (TypeError, ValueError):
        households = None

    try:
        result = calculate_priority(
            urgency=urgency,
            impact=impact,
            affected_households=households,
        )

        level = safe_text(
            result.get("priority_level"),
            "Not Assessed",
        ).title()

        if level not in valid_levels:
            level = "Not Assessed"

        score = (
            result.get("priority_score")
            if level != "Not Assessed"
            else None
        )

        return pd.Series({
            "priority_score": score,
            "priority_level": level,
        })

    except Exception:
        return pd.Series({
            "priority_score": None,
            "priority_level": "Not Assessed",
        })


def build_recommendations(data):

    recommendations = []

    if data.empty:
        return recommendations

    categories = get_category_counts(data)

    if not categories.empty:
        top = categories.iloc[0]

        recommendations.append({
            "title": "Most frequently reported issue",
            "detail": (
                f"{top['Category']} has "
                f"{int(top['Reports'])} reports. "
                "Review whether coordinated attention "
                "from the responsible authority is needed."
            ),
        })

    locations = get_location_counts(data)

    if not locations.empty:
        top = locations.iloc[0]

        recommendations.append({
            "title": "Area with the most reports",
            "detail": (
                f"{top['Location']} has "
                f"{int(top['Reports'])} reports. "
                "Review complaints from this locality together."
            ),
        })

    critical = int(
        data["priority_level"].eq("Critical").sum()
    )

    high = int(
        data["priority_level"].eq("High").sum()
    )

    not_assessed = int(
        data["priority_level"].eq("Not Assessed").sum()
    )

    if critical:
        recommendations.append({
            "title": "Critical priority reports",
            "detail": (
                f"{critical} report(s) have Critical priority. "
                "Arrange prompt human assessment."
            ),
        })

    if high:
        recommendations.append({
            "title": "High priority reports",
            "detail": (
                f"{high} report(s) have High priority. "
                "Review their reported impact and decide "
                "appropriate next steps."
            ),
        })

    if not_assessed:
        recommendations.append({
            "title": "Reports awaiting AI priority assessment",
            "detail": (
                f"{not_assessed} report(s) do not yet have a complete "
                "priority assessment. Review or reprocess these reports "
                "before assigning a priority."
            ),
        })

    return recommendations


# ============================================================
# PAGE HEADER
# ============================================================

st.markdown(
    '<div class="main-title">'
    'Community Intelligence Dashboard'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-subtitle">'
    'Explore community reporting patterns, analyze complaints, '
    'retrieve supporting evidence and generate recommendations.'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# LOAD REPORTS
# ============================================================

try:
    reports = get_all_reports()
    df = pd.DataFrame(reports)

except Exception as error:
    st.error(f"Unable to load reports: {error}")
    st.stop()


if df.empty:

    st.info(
        "No community reports are available yet. "
        "Submit a report to start exploring analytics."
    )

    st.header("Ask JANASHAKTI AI")

    question = st.text_input(
        "Enter your question",
        key="empty_rag_question",
    )

    if st.button("Find Answer", key="empty_rag_button"):

        if not question.strip():
            st.warning("Please enter a question.")

        else:
            try:
                result = generate_answer(
                    question,
                    top_k=3,
                )

                st.subheader("Answer")
                st.write(result.get("answer", ""))

                st.subheader("Supporting Sources")
                st.write(result.get("sources", []))

                create_json_download(
                    result,
                    "janashakti_rag_answer.json",
                )

            except Exception as error:
                st.error(str(error))

    st.stop()


# ============================================================
# ENSURE DATABASE COLUMNS EXIST
# ============================================================

expected_columns = [
    "report_id",
    "category",
    "state",
    "district",
    "locality",
    "description",
    "status",
    "verification_status",
    "created_at",
    "ai_urgency",
    "ai_impact_level",
    "affected_households",
    "ai_response",
    "ai_sources",
    "ai_verification_result",
    "priority_score",
    "priority_level",
]

for column in expected_columns:
    if column not in df.columns:
        df[column] = None


# ============================================================
# PRIORITY CALCULATION
# ============================================================

priority_data = df.apply(
    calculate_report_priority,
    axis=1,
)

df["priority_score"] = priority_data["priority_score"]
df["priority_level"] = priority_data["priority_level"]


# ============================================================
# COMMUNITY OVERVIEW
# ============================================================

st.divider()
st.header("📊 Community Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Reports", len(df))

col2.metric(
    "Pending Verification",
    int(
        df["verification_status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
        .eq("pending")
        .sum()
    ),
)

col3.metric(
    "Under Investigation",
    int(
        df["status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
        .eq("under investigation")
        .sum()
    ),
)

col4.metric(
    "Resolved Reports",
    int(
        df["status"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.strip()
        .eq("resolved")
        .sum()
    ),
)


# ============================================================
# MOST REPORTED ISSUES
# ============================================================

st.divider()
st.header("🔥 Most Reported Community Issues")

category_counts = get_category_counts(df)

if not category_counts.empty:

    fig = px.bar(
        category_counts,
        x="Category",
        y="Reports",
        text="Reports",
        color="Category",
        title="Community Issues by Category",
    )

    fig.update_layout(showlegend=False)

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        category_counts,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No category information is available.")


# ============================================================
# REPORT STATUS
# ============================================================

st.header("📌 Report Status Distribution")

status_counts = get_status_counts(df)

if not status_counts.empty:

    fig = px.pie(
        status_counts,
        names="Status",
        values="Reports",
        hole=0.45,
        title="Community Report Statuses",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# AREA-WISE COMMUNITY ANALYSIS
# ============================================================

st.divider()
st.header("📍 Area-wise Community Analysis")

location_counts = get_location_counts(df)

if not location_counts.empty:

    fig = px.bar(
        location_counts.head(15),
        x="Location",
        y="Reports",
        text="Reports",
        color="Location",
        title="Top Locations by Number of Reports",
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="Location",
        yaxis_title="Number of Reports",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.dataframe(
        location_counts,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No locality information is available.")


# ============================================================
# MONTHLY REPORTING TRENDS
# ============================================================

st.divider()
st.header("📈 Monthly Reporting Trends")

date_data = df.copy()

date_data["parsed_date"] = pd.to_datetime(
    date_data["created_at"],
    errors="coerce",
    utc=True,
)

valid_dates = date_data.dropna(
    subset=["parsed_date"]
).copy()

if not valid_dates.empty:

    valid_dates["MonthStart"] = (
        valid_dates["parsed_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    valid_dates["Month"] = (
        valid_dates["MonthStart"].dt.strftime("%b %Y")
    )

    monthly_counts = (
        valid_dates.groupby(["MonthStart", "Month"])
        .size()
        .reset_index(name="Reports")
        .sort_values("MonthStart")
    )

    fig = px.line(
        monthly_counts,
        x="Month",
        y="Reports",
        markers=True,
        title="Community Reports Over Time",
    )

    fig.update_xaxes(
        type="category",
        title="Month",
    )

    fig.update_yaxes(title="Reports")

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

else:
    st.info(
        "Monthly trends are unavailable because no valid "
        "submission dates were found."
    )


# ============================================================
# PRIORITY DISTRIBUTION
# ============================================================

st.divider()
st.header("🚦 Community Complaint Priority")

priority_order = [
    "Critical",
    "High",
    "Medium",
    "Low",
    "Not Assessed",
]

priority_counts = (
    df["priority_level"]
    .fillna("Not Assessed")
    .value_counts()
    .reindex(priority_order, fill_value=0)
    .rename_axis("Priority")
    .reset_index(name="Reports")
)

priority_columns = st.columns(5)

for column, level in zip(
    priority_columns,
    priority_order,
):

    count = int(
        priority_counts.loc[
            priority_counts["Priority"] == level,
            "Reports",
        ].iloc[0]
    )

    column.metric(level, count)

fig = px.pie(
    priority_counts,
    names="Priority",
    values="Reports",
    hole=0.45,
    title="Rule-based Complaint Priority",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

st.caption(
    "Priority is calculated from reported urgency, impact and "
    "affected households. It is decision support, not an official "
    "emergency assessment."
)


# ============================================================
# COMMUNITY HOUSEHOLD IMPACT
# ============================================================

st.divider()
st.header("🏘️ Community Household Impact")

household_data = df.copy()

household_data["household_count"] = pd.to_numeric(
    household_data["affected_households"],
    errors="coerce",
)

known_households = household_data[
    household_data["household_count"].notna()
    & (household_data["household_count"] >= 0)
].copy()

if not known_households.empty:

    total_households = int(
        known_households["household_count"].sum()
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Reported Household Impacts",
        total_households,
    )

    c2.metric(
        "Reports with Household Counts",
        len(known_households),
    )

    grouped_households = group_location_data(
        known_households.copy(),
        "household_count",
    )

    if not grouped_households.empty:

        fig = px.bar(
            grouped_households.head(10),
            x="Location",
            y="household_count",
            text="household_count",
            title="Reported Household Impacts by Locality",
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        st.dataframe(
            grouped_households[
                [
                    "Location",
                    "Locality",
                    "District",
                    "State",
                    "household_count",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "Reported household counts may overlap between complaints. "
        "They are not verified unique population counts."
    )

else:
    st.info(
        "No valid affected-household counts are available."
    )


# ============================================================
# ADMINISTRATOR RECOMMENDATIONS
# ============================================================

st.divider()
st.header("💡 Community Response Recommendations")

recommendations = build_recommendations(df)

if recommendations:

    for index, recommendation in enumerate(
        recommendations,
        start=1,
    ):

        with st.container(border=True):

            st.markdown(
                f"**{index}. {recommendation['title']}**"
            )

            st.write(recommendation["detail"])

else:
    st.info("Not enough information for recommendations.")

st.warning(
    "Recommendations are rule-based decision support. "
    "Administrators must independently verify complaints."
)


# ============================================================
# COMMUNITY REPORTS OVERVIEW
# ============================================================

st.divider()
st.header("📋 Community Reports Overview")

search_query = st.text_input(
    "Search reports",
    placeholder="Search by report ID, category, district or locality",
    key="report_search",
)

filtered_df = df.copy()

if search_query.strip():

    query = search_query.strip()

    searchable_columns = [
        "report_id",
        "category",
        "state",
        "district",
        "locality",
        "description",
        "status",
        "verification_status",
    ]

    mask = pd.Series(
        False,
        index=filtered_df.index,
    )

    for column in searchable_columns:

        mask |= (
            filtered_df[column]
            .fillna("")
            .astype(str)
            .str.contains(
                query,
                case=False,
                regex=False,
            )
        )

    filtered_df = filtered_df[mask]

display_columns = [
    column for column in [
        "report_id",
        "category",
        "state",
        "district",
        "locality",
        "status",
        "verification_status",
        "priority_level",
        "priority_score",
        "created_at",
    ]
    if column in filtered_df.columns
]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Showing {len(filtered_df)} of {len(df)} reports."
)

create_json_download(
    filtered_df.to_dict(orient="records"),
    "janashakti_reports.json",
)


# ============================================================
# INDIVIDUAL REPORT DETAILS
# ============================================================

st.divider()
st.header("🔎 View Individual Report")

report_options = df.to_dict(orient="records")

report_ids = [
    str(report.get("report_id") or "")
    for report in report_options
]

selected_report_id = st.selectbox(
    "Choose a report",
    options=report_ids,
    key="selected_report",
)

selected_report = next(
    (
        report for report in report_options
        if str(report.get("report_id") or "")
        == selected_report_id
    ),
    None,
)

if selected_report:

    with st.expander(
        "View report details",
        expanded=True,
    ):

        for label, key in [
            ("Report ID", "report_id"),
            ("Category", "category"),
            ("State", "state"),
            ("District", "district"),
            ("Locality", "locality"),
            ("Description", "description"),
            ("Status", "status"),
            ("Verification", "verification_status"),
            ("Submitted At", "created_at"),
        ]:

            st.write(
                f"**{label}:**",
                safe_text(selected_report.get(key)),
            )

        st.metric(
            "Priority Level",
            safe_text(
                selected_report.get("priority_level")
            ),
        )

        selected_score = selected_report.get("priority_score")

        try:

            selected_score = float(selected_score)

            selected_score_text = (
                "Not assessed"
                if pd.isna(selected_score)
                else f"{selected_score:g}/100"
            )

        except (TypeError, ValueError):

            selected_score_text = "Not assessed"

        st.metric(
            "Priority Score",
            selected_score_text,
        )

    create_json_download(
        selected_report,
        f"{selected_report_id}_report.json",
    )


# ============================================================
# AI-POWERED COMPLAINT ANALYSIS
# ============================================================

st.divider()
st.header("🤖 AI-Powered Complaint Analysis")

st.write(
    "Analyze the selected complaint to identify its likely "
    "category, urgency, completeness and suggested next steps."
)

st.warning(
    "This analyzer provides preliminary insights. "
    "It does not independently verify complaints."
)

if selected_report:

    if st.button(
        "Analyze Selected Complaint",
        type="primary",
        key="analyze_complaint_button",
        use_container_width=True,
    ):

        description = safe_text(
            selected_report.get("description"),
            "",
        )

        if not description:

            st.warning(
                "The selected report has no description."
            )

        else:

            with st.spinner("Analyzing complaint..."):

                try:

                    analysis = analyze_complaint(description)

                    st.session_state["janashakti_analysis"] = {
                        "report_id": selected_report_id,
                        "analysis": analysis,
                    }

                except Exception as error:

                    st.error(
                        f"Unable to analyze complaint: {error}"
                    )


analysis_state = st.session_state.get(
    "janashakti_analysis"
)

if (
    analysis_state
    and analysis_state.get("report_id") == selected_report_id
):

    analysis = analysis_state.get("analysis", {})

    st.success("Complaint analysis completed.")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Predicted Category",
        safe_text(
            analysis.get("predicted_category"),
            "Unknown",
        ),
    )

    c2.metric(
        "Review Urgency",
        safe_text(
            analysis.get("urgency"),
            "Unknown",
        ),
    )

    c3.metric(
        "Description Completeness",
        safe_text(
            analysis.get("completeness"),
            "Unknown",
        ),
    )

    st.subheader("Analysis Details")

    st.write(
        "**Urgency explanation:**",
        safe_text(analysis.get("urgency_reason")),
    )

    st.write(
        "**Word count:**",
        analysis.get("word_count", 0),
    )

    repeated_terms = analysis.get("repeated_terms", [])

    st.write(
        "**Repeated terms:**",
        ", ".join(map(str, repeated_terms))
        if repeated_terms else "None detected",
    )

    matched_categories = analysis.get(
        "matched_categories",
        [],
    )

    st.write(
        "**Matched categories:**",
        ", ".join(map(str, matched_categories))
        if matched_categories else "None",
    )

    st.subheader("Recommended Next Steps")

    st.info(
        safe_text(
            analysis.get("recommendation"),
            "Review and verify the complaint.",
        )
    )

    st.warning(
        "Human review is required before official action."
    )

    create_json_download(
        {
            "report_id": selected_report_id,
            "analysis": analysis,
            "human_review_required": True,
        },
        f"{selected_report_id}_analysis.json",
    )


# ============================================================
# SUPPORTING EVIDENCE RETRIEVAL
# ============================================================

st.divider()
st.header("📚 Supporting Evidence Retrieval")

st.write(
    "Search local reference documents for information "
    "relevant to the selected complaint."
)

if selected_report:

    if st.button(
        "Retrieve Supporting Evidence",
        key="retrieve_evidence_button",
        use_container_width=True,
    ):

        description = safe_text(
            selected_report.get("description"),
            "",
        )

        if not description:

            st.warning("Complaint description is missing.")

        else:

            with st.spinner("Searching reference documents..."):

                try:

                    result = retrieve_evidence(
                        description,
                        top_k=3,
                    )

                    st.session_state["janashakti_evidence"] = {
                        "report_id": selected_report_id,
                        "result": result,
                    }

                except Exception as error:

                    st.error(
                        f"Unable to retrieve evidence: {error}"
                    )


evidence_state = st.session_state.get(
    "janashakti_evidence"
)

if (
    evidence_state
    and evidence_state.get("report_id") == selected_report_id
):

    evidence_result = evidence_state.get("result", {})
    evidence = evidence_result.get("evidence", [])

    st.write(
        safe_text(
            evidence_result.get("message"),
            "Evidence retrieval completed.",
        )
    )

    if evidence:

        for index, item in enumerate(
            evidence,
            start=1,
        ):

            with st.expander(
                f"Evidence {index}: "
                f"{item.get('source', 'Unknown document')}",
                expanded=index == 1,
            ):

                st.write(
                    "**Document:**",
                    safe_text(item.get("source")),
                )

                st.write(
                    "**Page:**",
                    item.get("page") or "Not available",
                )

                try:

                    similarity = float(
                        item.get("similarity", 0)
                    )

                except (TypeError, ValueError):

                    similarity = 0.0

                st.write(
                    f"**Similarity score:** {similarity:.4f}"
                )

                st.write(
                    safe_text(
                        item.get("text"),
                        "No text available.",
                    )
                )

        create_json_download(
            {
                "report_id": selected_report_id,
                "complaint": selected_report.get("description"),
                "evidence": evidence,
                "human_review_required": True,
            },
            f"{selected_report_id}_evidence.json",
        )

    else:

        st.info(
            "No supporting documents were retrieved. "
            "Consider adding relevant documents to data/documents."
        )


# ============================================================
# ASK JANASHAKTI AI
# ============================================================

st.divider()
st.header("💬 Ask JANASHAKTI AI")

st.write(
    "Ask questions about community issues and receive "
    "answers based on your local reference documents."
)

question = st.text_input(
    "Enter your question",
    placeholder="What should residents do about a water shortage?",
    key="rag_question",
)

if st.button(
    "Find Answer",
    type="primary",
    key="rag_answer_button",
    use_container_width=True,
):

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        with st.spinner(
            "Searching documents and preparing an answer..."
        ):

            try:

                result = generate_answer(
                    question,
                    top_k=3,
                )

                st.session_state[
                    "janashakti_rag_answer"
                ] = result

            except Exception as error:

                st.error(
                    f"Unable to generate an answer: {error}"
                )


rag_result = st.session_state.get(
    "janashakti_rag_answer"
)

if rag_result:

    st.subheader("Answer")

    st.write(
        rag_result.get(
            "answer",
            "No answer was generated.",
        )
    )

    st.subheader("Supporting Sources")

    sources = rag_result.get("sources", [])

    if sources:

        for index, source in enumerate(
            sources,
            start=1,
        ):

            with st.expander(
                f"Source {index}: "
                f"{source.get('document', 'Unknown document')}"
            ):

                st.write(
                    "**Document:**",
                    source.get("document", "Unknown"),
                )

                st.write(
                    "**Page:**",
                    source.get("page") or "Not available",
                )

                try:

                    similarity = float(
                        source.get("similarity", 0)
                    )

                except (TypeError, ValueError):

                    similarity = 0.0

                st.write(
                    f"**Similarity score:** {similarity:.4f}"
                )

    else:

        st.info("No supporting sources were retrieved.")

    st.warning(
        "Answers are based on retrieved reference documents. "
        "Human review and independent verification are required."
    )

    create_json_download(
        rag_result,
        "janashakti_rag_answer.json",
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "JANASHAKTI AI | Community Intelligence and Social Response"
)

st.caption(
    "Academic prototype. Automated analysis and retrieved "
    "information are preliminary and must not replace independent "
    "verification or authorized decisions."
)
