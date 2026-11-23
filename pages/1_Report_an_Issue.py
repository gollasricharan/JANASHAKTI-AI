
import streamlit as st

from services.report_service import (
    create_report,
    save_report_analysis,
)

from agents.agent_orchestrator import process_complaint


# --------------------------------------------------
# CATEGORY NORMALIZATION
# --------------------------------------------------

def normalize_category(category):
    value = str(category or "").strip().lower()

    category_map = {
        "water shortage": "water supply",
        "water supply": "water supply",
        "watershortage": "water supply",
        "watersupply": "water supply",
        "waste management": "waste management",
        "wastemanagement": "waste management",
        "waste": "waste management",
        "damaged roads": "road maintenance",
        "road maintenance": "road maintenance",
        "damagedroads": "road maintenance",
        "roads": "road maintenance",
        "drainage": "drainage",
        "drainage problems": "drainage",
        "electricity": "electricity",
        "electricity complaints": "electricity",
        "electricity outage": "electricity",
        "power outage": "electricity",
        "streetlights": "streetlights",
        "streetlight": "streetlights",
        "street lights": "streetlights",
        "streetlight issues": "streetlights",
        "public safety": "public safety",
        "publicsafety": "public safety",
        "other": "other",
    }

    return category_map.get(value, value)


# --------------------------------------------------
# SUPPORTING SOURCE EXTRACTION
# --------------------------------------------------

def get_supporting_sources(result):
    """Collect source metadata returned by the orchestrator."""

    if not isinstance(result, dict):
        return []

    evidence = result.get("evidence")
    sources = result.get("sources")
    retrieval = result.get("retrieval", {})

    if not evidence:
        evidence = sources

    if not evidence and isinstance(retrieval, dict):
        evidence = retrieval.get("evidence")

        if not evidence:
            evidence = retrieval.get("sources")

    if isinstance(evidence, dict):
        evidence = (
            evidence.get("evidence")
            or evidence.get("sources")
            or evidence.get("documents")
            or []
        )

    if not isinstance(evidence, (list, tuple)):
        evidence = [evidence] if evidence else []

    displayed_sources = []
    seen_sources = set()

    for item in evidence:

        if isinstance(item, dict):
            metadata = item.get("metadata", {})

            if not isinstance(metadata, dict):
                metadata = {}

            source_name = (
                item.get("source")
                or item.get("source_name")
                or item.get("file_name")
                or item.get("filename")
                or item.get("document")
                or metadata.get("source")
                or "Unknown source"
            )

            similarity = item.get(
                "similarity",
                item.get("score")
            )

        else:
            source_name = str(item)
            similarity = None

        source_name = str(source_name).strip()

        if not source_name:
            continue

        source_key = source_name.lower()

        if source_key in seen_sources:
            continue

        seen_sources.add(source_key)

        displayed_sources.append({
            "name": source_name,
            "similarity": similarity
        })

    return displayed_sources


# --------------------------------------------------
# CLAIM DISPLAY HELPERS
# --------------------------------------------------

def get_claim_list(verification, key):
    """Return claim details safely as a list."""

    claims = verification.get(key, [])

    if claims is None:
        return []

    if isinstance(claims, str):
        return [claims] if claims.strip() else []

    if isinstance(claims, (list, tuple)):
        return list(claims)

    return []


def get_claim_count(verification, count_key, claims):
    """Use the agent count when available, otherwise list length."""

    count = verification.get(count_key)

    if count is None:
        return len(claims)

    try:
        return max(0, int(count))
    except (TypeError, ValueError):
        return len(claims)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Report an Issue | JANASHAKTI AI",
    page_icon="📝",
    layout="wide",
)

st.title("Report a Community Issue")

st.write(
    "Help improve your community by reporting local problems."
)

st.info(
    "Please provide accurate information. "
    "Every submission will be saved for review."
)


# --------------------------------------------------
# REPORT FORM
# --------------------------------------------------

with st.form("report_form", clear_on_submit=True):

    category = st.selectbox(
        "Select Problem Category",
        [
            "Water shortage",
            "Waste management",
            "Damaged roads",
            "Drainage",
            "Electricity",
            "Streetlights",
            "Public Safety",
            "Other",
        ],
    )

    state = st.text_input(
        "State",
        placeholder="Example: Karnataka",
    )

    district = st.text_input(
        "District",
        placeholder="Enter your district",
    )

    locality = st.text_input(
        "Locality",
        placeholder="Enter the affected area",
    )

    affected_households = st.number_input(
        "Number of Affected Households",
        min_value=0,
        max_value=100000,
        value=0,
        step=1,
        help="Enter 0 if the number is unknown.",
    )

    description = st.text_area(
        "Describe the problem",
        placeholder="Explain what happened and where it happened.",
        max_chars=5000,
        height=150,
    )

    submitted = st.form_submit_button(
        "Submit Report",
        use_container_width=True,
    )


# --------------------------------------------------
# PROCESS SUBMISSION
# --------------------------------------------------

if submitted:

    if not description.strip():

        st.error("Please describe the community problem.")

    elif (
        not state.strip()
        or not district.strip()
        or not locality.strip()
    ):

        st.error(
            "Please complete the state, district and locality fields."
        )

    else:

        report_id = None

        try:

            # STEP 1: SAVE ORIGINAL COMPLAINT

            report_id = create_report(
                category=category,
                state=state.strip(),
                district=district.strip(),
                locality=locality.strip(),
                description=description.strip(),
            )

            st.success("Report submitted successfully!")

            st.subheader("Your Report Reference ID")
            st.code(report_id)

            st.write("Status: Submitted")
            st.write("Verification: Pending")

            household_count = (
                int(affected_households)
                if affected_households > 0
                else None
            )

            # STEP 2: PREPARE ANALYSIS INPUT

            analysis_description = (
                f"Reported category: {category}.\n"
                f"Location: {locality}, {district}, {state}.\n"
                f"Affected households: "
                f"{household_count if household_count is not None else 'Unknown'}.\n"
                f"Complaint details: {description.strip()}"
            )

            # STEP 3: RUN MULTI-AGENT WORKFLOW

            with st.spinner(
                "JANASHAKTI AI agents are analysing your complaint..."
            ):

                result = process_complaint(
                    analysis_description,
                    affected_households=household_count,
                )

            st.divider()
            st.header("JANASHAKTI AI Analysis")

            if not isinstance(result, dict):
                raise ValueError("Invalid AI analysis result.")

            # STEP 4: SAVE AI ANALYSIS

            save_report_analysis(
                report_id,
                result,
            )

            st.success(
                "AI analysis has also been saved successfully."
            )

            classification = result.get(
                "classification", {}
            )

            verification = result.get(
                "verification", {}
            )

            if not isinstance(verification, dict):
                verification = {}

            if not isinstance(classification, dict):
                classification = {}

            impact = result.get(
                "impact",
                result.get("impact_assessment", {})
            )

            priority = result.get(
                "priority",
                result.get("priority_assessment", {})
            )

            if not isinstance(impact, dict):
                impact = {}

            if not isinstance(priority, dict):
                priority = {}

            # ------------------------------------------
            # AGENT 1: CLASSIFICATION
            # ------------------------------------------

            st.subheader("1. Complaint Classification")

            reported_category = result.get(
                "reported_category",
                classification.get("reported_category", category)
            )

            predicted_category = result.get(
                "predicted_category",
                classification.get(
                    "predicted_category",
                    classification.get("category", "Unknown")
                )
            )

            routing_category = result.get(
                "routing_category",
                classification.get("routing_category", "Unknown")
            )

            st.write(
                "**Resident-selected category:**",
                category,
            )

            st.write(
                "**AI-predicted category:**",
                predicted_category,
            )

            st.write(
                "**Category used for evidence retrieval:**",
                routing_category,
            )

            classification_urgency = classification.get(
                "urgency",
                result.get("urgency", "Unknown")
            )

            st.write(
                "**Classification urgency:**",
                classification_urgency,
            )

            reason = classification.get("reason", "")

            if reason:
                st.caption(reason)

            category_mismatch = result.get(
                "category_mismatch",
                classification.get("category_mismatch", False)
            )

            if "category_mismatch" not in result:
                if "category_mismatch" not in classification:
                    category_mismatch = (
                        normalize_category(category)
                        != normalize_category(predicted_category)
                        and normalize_category(predicted_category)
                        not in ("unknown", "needs review", "")
                    )

            if category_mismatch:

                st.warning(
                    "The AI prediction differs from the category "
                    "selected by the resident. Administrator review "
                    "is required."
                )

            # ------------------------------------------
            # AGENT 2: AI-GENERATED GUIDANCE
            # ------------------------------------------

            st.subheader("2. AI-Generated Guidance")

            ai_response = result.get("ai_response", "")

            if ai_response:
                st.markdown(ai_response)

            else:
                st.warning(
                    "AI guidance could not be generated."
                )

            # ------------------------------------------
            # AGENT 3: SUPPORTING EVIDENCE
            # ------------------------------------------

            st.subheader("3. Supporting Reference Documents")

            supporting_sources = get_supporting_sources(result)

            if supporting_sources:

                for index, source in enumerate(
                    supporting_sources,
                    start=1
                ):

                    source_name = source["name"]
                    similarity = source["similarity"]

                    if similarity is not None:

                        try:
                            similarity = float(similarity)

                            st.write(
                                f"{index}. {source_name} "
                                f"(Relevance: {similarity:.2f})"
                            )

                        except (TypeError, ValueError):

                            st.write(
                                f"{index}. {source_name}"
                            )

                    else:

                        st.write(
                            f"{index}. {source_name}"
                        )

            else:

                st.warning(
                    "No supporting source metadata was returned "
                    "by the retrieval system."
                )

            # ------------------------------------------
            # AGENT 4: EVIDENCE VERIFICATION
            # ------------------------------------------

            st.subheader("4. Evidence Verification")

            verification_status = verification.get(
                "verification_status",
                verification.get("status", "Needs Review")
            )

            st.write(
                "**Verification status:**",
                verification_status,
            )

            score = verification.get(
                "verification_score",
                0
            )

            try:
                score = float(score)

                if score > 1:
                    score = score / 100

                score = max(0.0, min(1.0, score))

            except (TypeError, ValueError):
                score = 0.0

            st.progress(score)

            st.write(
                f"**Text matching score:** {score:.0%}"
            )

            st.caption(
                "This score measures text overlap with reference "
                "documents. It does not independently verify the "
                "real-world complaint."
            )

            # THREE-WAY CLAIM VERIFICATION

            st.markdown("#### Claim Verification Breakdown")

            reference_claims = get_claim_list(
                verification,
                "verified_claims"
            )

            resident_claims = get_claim_list(
                verification,
                "resident_reported_claims"
            )

            unverified_claims = get_claim_list(
                verification,
                "unverified_claims"
            )

            reference_count = get_claim_count(
                verification,
                "reference_supported_count",
                reference_claims
            )

            resident_count = get_claim_count(
                verification,
                "resident_reported_count",
                resident_claims
            )

            unverified_count = get_claim_count(
                verification,
                "unverified_count",
                unverified_claims
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Reference Supported",
                    reference_count
                )

            with col2:
                st.metric(
                    "Resident Reported",
                    resident_count
                )

            with col3:
                st.metric(
                    "Unverified",
                    unverified_count
                )

            # DISPLAY CLAIM DETAILS IN READABLE FORMAT

            claim_groups = [
                (
                    "Reference-supported claims",
                    reference_claims,
                    "These claims have matching information in "
                    "the retrieved reference documents."
                ),
                (
                    "Resident-reported claims",
                    resident_claims,
                    "These claims are reported in the complaint "
                    "but are not independently confirmed."
                ),
                (
                    "Unverified claims",
                    unverified_claims,
                    "These claims need additional evidence or "
                    "manual checking."
                ),
            ]

            for title, claims, explanation in claim_groups:

                if claims:

                    with st.expander(title):

                        st.caption(explanation)

                        for claim in claims:

                            if isinstance(claim, dict):

                                claim_text = claim.get(
                                    "claim",
                                    "Unknown claim"
                                )

                                st.markdown(
                                    f"- **{claim_text}**"
                                )

                                match_ratio = claim.get(
                                    "match_ratio",
                                    0
                                )

                                try:
                                    match_percentage = (
                                        float(match_ratio) * 100
                                    )
                                except (TypeError, ValueError):
                                    match_percentage = 0

                                st.caption(
                                    f"Reference text overlap: "
                                    f"{match_percentage:.0f}%"
                                )

                                sources = claim.get("source", [])

                                if isinstance(sources, str):
                                    sources = [sources]

                                if sources:
                                    st.caption(
                                        "Matching reference: "
                                        + ", ".join(
                                            str(source)
                                            for source in sources
                                        )
                                    )

                                reason = claim.get("reason")

                                if reason:
                                    st.caption(reason)

                            else:
                                st.write(f"- {claim}")

            # VERIFICATION REVIEW MESSAGE

            human_verification_required = verification.get(
                "human_review_required",
                False
            )

            unsupported_claims = verification.get(
                "unsupported_claims",
                []
            )

            if (
                human_verification_required
                or unsupported_claims
                or unverified_count > 0
            ):

                st.warning(
                    "Some claims require additional evidence "
                    "or manual verification."
                )

            elif (
                reference_count
                + resident_count
                + unverified_count
            ) == 0:

                st.info(
                    "No individual claim details were returned "
                    "by the verification agent. Manual review "
                    "may still be required."
                )

            else:

                st.success(
                    "No unverified claims were returned by the "
                    "evidence verification agent."
                )

            # ------------------------------------------
            # AGENT 5: COMMUNITY IMPACT
            # ------------------------------------------

            st.subheader("5. Community Impact Assessment")

            st.write(
                "**Impact level:**",
                impact.get("impact_level", "Unknown"),
            )

            st.write(
                "**Impact assessment urgency:**",
                impact.get("urgency", "Unknown"),
            )

            st.write(
                "**Affected households:**",
                impact.get(
                    "affected_households",
                    household_count
                    if household_count is not None
                    else "Not provided"
                ),
            )

            st.write(
                "**Recommendation:**",
                impact.get(
                    "recommendation",
                    "Manual assessment required."
                ),
            )

            # ------------------------------------------
            # AGENT 6: PRIORITY ASSESSMENT
            # ------------------------------------------

            st.subheader("6. AI Priority Assessment")

            priority_score = priority.get(
                "priority_score",
                priority.get("score", 0)
            )

            priority_level = priority.get(
                "priority_level",
                priority.get("priority", "Not Assessed")
            )

            try:
                priority_score = int(float(priority_score))

            except (TypeError, ValueError):
                priority_score = 0

            st.metric(
                "Community Issue Priority Score",
                f"{priority_score}/100",
            )

            if priority_level == "Critical":

                st.error(
                    f"Priority Level: {priority_level}"
                )

            elif priority_level == "High":

                st.warning(
                    f"Priority Level: {priority_level}"
                )

            elif priority_level == "Medium":

                st.info(
                    f"Priority Level: {priority_level}"
                )

            elif priority_level == "Low":

                st.success(
                    f"Priority Level: {priority_level}"
                )

            else:

                st.warning(
                    f"Priority Level: {priority_level}"
                )

            st.caption(
                "Priority is calculated using urgency, community "
                "impact and affected households. Administrator "
                "review is required."
            )

            # ------------------------------------------
            # HUMAN REVIEW
            # ------------------------------------------

            st.divider()

            if result.get("human_review_required", True):

                st.warning(
                    "Human review is required before any official action."
                )

            else:

                st.success(
                    "Automated checks completed. "
                    "Official verification is still necessary."
                )

            review_reasons = result.get("review_reasons", [])

            if review_reasons:

                with st.expander("Review details"):

                    for reason in review_reasons:
                        st.write(f"- {reason}")

        except ValueError as error:

            st.error(str(error))

        except Exception as error:

            st.error("Unable to process the report.")
            st.exception(error)

            if report_id:

                st.info(
                    f"Your original report was saved. "
                    f"Reference ID: {report_id}. "
                    "Please check the AI analysis or database update."
                )
