import streamlit as st

from database.connection import initialize_database
from services.report_service import get_report_statistics


st.set_page_config(
    page_title="JANASHAKTI AI | Community Intelligence",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

initialize_database()


# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
    @import url(
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap'
    );

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #f4f7fb;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    .top-banner {
        background: #102f56;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 13px;
        margin-bottom: 22px;
    }

    .brand {
        color: #102f56;
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 0;
    }

    .brand-subtitle {
        color: #64748b;
        font-size: 12px;
        margin-top: 4px;
    }

    .hero {
        background: linear-gradient(120deg, #102f56, #176b87);
        color: white;
        padding: 45px 38px;
        border-radius: 18px;
        margin-top: 22px;
        margin-bottom: 28px;
    }

    .hero h1 {
        font-size: 38px;
        line-height: 1.3;
        font-weight: 800;
        color: white;
    }

    .hero p {
        font-size: 16px;
        line-height: 1.8;
        color: #e2edf7;
        max-width: 850px;
    }

    .section-title {
        color: #102f56;
        font-size: 25px;
        font-weight: 800;
        margin-top: 25px;
        margin-bottom: 15px;
    }

    .metric-card {
        background: white;
        padding: 22px;
        border-radius: 13px;
        border: 1px solid #e2e8f0;
        min-height: 135px;
    }

    .metric-label {
        color: #64748b;
        font-size: 13px;
    }

    .metric-value {
        color: #102f56;
        font-size: 31px;
        font-weight: 800;
        margin-top: 9px;
    }

    .info-card {
        background: white;
        padding: 23px;
        border-radius: 13px;
        border: 1px solid #e2e8f0;
        min-height: 175px;
    }

    .info-card h3 {
        color: #102f56;
        font-size: 18px;
    }

    .info-card p {
        color: #64748b;
        line-height: 1.8;
        font-size: 14px;
    }

    .footer {
        text-align: center;
        color: #64748b;
        padding: 30px 10px;
        font-size: 12px;
    }

    div.stButton > button {
        border-radius: 8px;
        min-height: 42px;
        font-weight: 600;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div class="top-banner">
        COMMUNITY SERVICE PORTAL
        &nbsp; | &nbsp; Responsible AI for Public Good
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([3, 2])

with left:
    st.markdown(
        """
        <div class="brand">JANASHAKTI AI</div>
        <div class="brand-subtitle">
            COMMUNITY INTELLIGENCE & SOCIAL RESPONSE
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.write("")
    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.page_link(
            "app.py",
            label="Home",
            use_container_width=True,
        )

    with col2:
        st.page_link(
            "pages/1_Report_an_Issue.py",
            label="Report Issue",
            use_container_width=True,
        )

    with col3:
        st.page_link(
            "pages/3_AI_Insights.py",
            label="AI Insights",
            use_container_width=True,
        )

st.divider()


# --------------------------------------------------
# HERO SECTION
# --------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <h1>Building Better Communities<br>
        Through Responsible AI</h1>

        <p>
        A community intelligence platform designed to organize public
        issue reports, identify emerging patterns, retrieve supporting
        evidence, and help people make informed decisions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# LIVE STATISTICS
# --------------------------------------------------

st.markdown(
    '<div class="section-title">Community Overview</div>',
    unsafe_allow_html=True,
)

stats = get_report_statistics()

columns = st.columns(4)

metrics = [
    (
        "Reports Received",
        stats["total"],
        "Total stored reports",
    ),
    (
        "Awaiting Review",
        stats["awaiting_review"],
        "Submitted reports",
    ),
    (
        "Under Investigation",
        stats["under_investigation"],
        "Reports being reviewed",
    ),
    (
        "Resolved Issues",
        stats["resolved"],
        "Reports marked resolved",
    ),
]

for col, (label, value, description) in zip(columns, metrics):
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                <div class="metric-label">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# SERVICES
# --------------------------------------------------

st.markdown(
    '<div class="section-title">Our Services</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
        <div class="info-card">
            <h3>📝 Report a Problem</h3>
            <p>
            Submit information about water shortages, waste accumulation,
            damaged roads, drainage, and other community concerns.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.page_link(
        "pages/1_Report_an_Issue.py",
        label="Submit a Report →",
        use_container_width=True,
    )

with c2:
    st.markdown(
        """
        <div class="info-card">
            <h3>🔎 Explore Issues</h3>
            <p>
            Browse community reports, search by location, and filter
            issues by category and review status.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.page_link(
        "pages/2_Explore_Issues.py",
        label="Explore Reports →",
        use_container_width=True,
    )

with c3:
    st.markdown(
        """
        <div class="info-card">
            <h3>🤖 AI Insights</h3>
            <p>
            AI-assisted analysis organizes community reports,
            retrieves supporting evidence, assesses impact,
            and generates recommendations for human review.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.page_link(
        "pages/3_AI_Insights.py",
        label="View AI Insights →",
        use_container_width=True,
    )


# --------------------------------------------------
# HOW IT WORKS
# --------------------------------------------------

st.markdown(
    '<div class="section-title">How It Works</div>',
    unsafe_allow_html=True,
)

steps = st.columns(4)

step_data = [
    (
        "01 · Report",
        "A citizen submits a community concern.",
    ),
    (
        "02 · Analyze",
        "AI organizes and classifies information.",
    ),
    (
        "03 · Verify",
        "Evidence is checked and reviewed.",
    ),
    (
        "04 · Respond",
        "Authorized people decide the next steps.",
    ),
]

for col, (title, description) in zip(steps, step_data):
    with col:
        st.markdown(
            f"""
            <div class="info-card">
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown(
    """
    <div class="footer">
        JANASHAKTI AI · Academic Prototype for Community Benefit
        <br><br>
        This is an independent demonstration project, not an official
        government website. AI-generated information requires verification.
    </div>
    """,
    unsafe_allow_html=True,
)