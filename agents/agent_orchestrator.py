
from pathlib import Path
import re

from agents.classification_agent import classify_issue
from agents.evidence_agent import verify_answer
from agents.impact_agent import assess_impact

from rag.rag_service import retrieve_evidence

from services.priority_service import calculate_priority
from services.llm_service import generate_llm_response


# ==================================================
# CATEGORY AND SOURCE MAPPING
# ==================================================

CATEGORY_SOURCE_MAP = {
    "watersupply": ["watersupply"],
    "watershortage": ["watersupply"],

    "wastemanagement": ["wastemanagement"],
    "waste": ["wastemanagement"],

    "roadmaintenance": ["roadmaintenance"],
    "damagedroads": ["roadmaintenance"],
    "roads": ["roadmaintenance"],

    "drainage": ["drainageproblems"],

    "electricity": ["electricitycomplaints"],
    "electricityoutage": ["electricitycomplaints"],
    "poweroutage": ["electricitycomplaints"],

    "streetlights": ["streetlightissues"],
    "streetlight": ["streetlightissues"],

    "publicsafety": ["publicsafety"],
}

GENERAL_SOURCES = ["complaintreporting"]

CATEGORY_ALIASES = {
    "watershortage": "Water Supply",
    "watersupply": "Water Supply",

    "wastemanagement": "Waste Management",
    "waste": "Waste Management",

    "damagedroads": "Road Maintenance",
    "roadmaintenance": "Road Maintenance",
    "roads": "Road Maintenance",

    "drainage": "Drainage",

    "electricity": "Electricity",
    "electricityoutage": "Electricity",
    "poweroutage": "Electricity",

    "streetlights": "Streetlights",
    "streetlight": "Streetlights",
    "streetlightsissue": "Streetlights",

    "publicsafety": "Public Safety",

    "other": "Other",
}


# ==================================================
# SAFE HELPER FUNCTIONS
# ==================================================

def safe_text(value, default=""):
    if value is None:
        return default

    text = str(value).strip()

    if text.lower() in {"", "none", "nan", "unknown"}:
        return default

    return text


def safe_similarity(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def normalize_category(value):
    return "".join(
        character
        for character in str(value or "").lower()
        if character.isalnum()
    )


def get_source_name(source):
    try:
        filename = Path(str(source)).stem
    except Exception:
        filename = str(source)

    return normalize_category(filename)


def canonical_category(value):
    normalized = normalize_category(value)

    return CATEGORY_ALIASES.get(
        normalized,
        safe_text(value, "Needs Review"),
    )


# ==================================================
# AI RESPONSE QUALITY VALIDATION
# ==================================================

def validate_answer_quality(answer):
    """
    Check whether the generated AI response is usable.

    Checks:
    1. Valid text.
    2. Minimum response length.
    3. Required sections.
    4. Repeated statements.
    """

    if not isinstance(answer, str):
        return False, "AI response is not valid text."

    answer = answer.strip()

    if len(answer) < 150:
        return False, "AI response is too short."

    required_sections = [
        "Issue Summary",
        "Relevant Supporting Evidence",
        "Recommended Next Steps",
        "Information Requiring Human Verification"
    ]

    for section in required_sections:

        if section.lower() not in answer.lower():

            return False, (
                f"Missing section: {section}"
            )

    lines = [
        line.strip().lower()
        for line in answer.splitlines()
        if len(line.strip()) > 25
    ]

    if not lines:
        return False, "AI response contains no useful content."

    unique_lines = set(lines)

    duplicate_ratio = (
        1 - (len(unique_lines) / len(lines))
    )

    if duplicate_ratio > 0.25:
        return False, (
            "AI response contains repeated statements."
        )

    return True, None


# ==================================================
# RESIDENT-SELECTED CATEGORY
# ==================================================

def extract_reported_category(description):
    """
    Extract the category selected by the resident.
    """

    if not isinstance(description, str):
        return None

    match = re.search(
        r"(?im)^\s*Reported category\s*:\s*([^\n]+)",
        description,
    )

    if not match:
        return None

    selected = match.group(1).strip().rstrip(".")

    return canonical_category(selected)


# ==================================================
# CATEGORY-BASED EVIDENCE FILTERING
# ==================================================

def filter_relevant_evidence(evidence, category):

    if not isinstance(evidence, list):
        return []

    normalized_category = normalize_category(
        canonical_category(category)
    )

    allowed_sources = CATEGORY_SOURCE_MAP.get(
        normalized_category,
        [],
    )

    filtered_evidence = []
    seen_chunks = set()

    for item in evidence:

        if not isinstance(item, dict):
            continue

        text = safe_text(item.get("text"))

        if not text:
            continue

        source = safe_text(
            item.get("source"),
            "Unknown document",
        )

        source_name = get_source_name(source)

        is_general_source = any(
            name in source_name
            for name in GENERAL_SOURCES
        )

        is_category_source = any(
            name in source_name
            for name in allowed_sources
        )

        if not (is_general_source or is_category_source):
            continue

        chunk_key = (
            source_name,
            text.lower(),
        )

        if chunk_key in seen_chunks:
            continue

        filtered_evidence.append({
            **item,
            "text": text,
            "source": source,
            "similarity": safe_similarity(
                item.get("similarity")
            ),
        })

        seen_chunks.add(chunk_key)

    filtered_evidence.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return filtered_evidence


# ==================================================
# EXTRACTIVE FALLBACK RESPONSE
# ==================================================

def generate_fallback_answer(evidence):

    if not evidence:
        return (
            "No relevant supporting information was found "
            "in the available reference documents. "
            "Human review is required."
        )

    sections = []

    for index, item in enumerate(evidence, start=1):

        if not isinstance(item, dict):
            continue

        text = safe_text(item.get("text"))

        if not text:
            continue

        source = safe_text(
            item.get("source"),
            "Unknown document",
        )

        sections.append(
            f"Reference {index} - {source}:\n{text}"
        )

    if not sections:
        return (
            "No usable supporting information was found. "
            "Human review is required."
        )

    evidence_text = "\n\n".join(sections)

    return (
        "## Issue Summary\n\n"
        "The complaint has been submitted for community "
        "issue analysis. The following information was "
        "retrieved from relevant reference documents.\n\n"

        "## Relevant Supporting Evidence\n\n"
        f"{evidence_text}\n\n"

        "## Recommended Next Steps\n\n"
        "1. Review the retrieved reference documents.\n"
        "2. Confirm the reported location and circumstances.\n"
        "3. Arrange an appropriate inspection before deciding "
        "on further action.\n\n"

        "## Information Requiring Human Verification\n\n"
        "1. Confirm the actual condition at the reported location.\n"
        "2. Verify the number of affected households.\n"
        "3. Confirm whether the retrieved information applies "
        "to this specific complaint.\n\n"

        "This response was generated using an evidence-based "
        "fallback because the LLM response was unavailable "
        "or failed quality validation. Human review is required."
    )


# ==================================================
# SOURCE PREPARATION
# ==================================================

def prepare_sources(evidence):

    sources = []
    seen_sources = set()

    for item in evidence:

        if not isinstance(item, dict):
            continue

        source = safe_text(
            item.get("source"),
            "Unknown document",
        )

        source_key = get_source_name(source)

        if source_key in seen_sources:
            continue

        sources.append({
            "document": source,
            "page": item.get("page"),
            "similarity": safe_similarity(
                item.get("similarity")
            ),
        })

        seen_sources.add(source_key)

    return sources


# ==================================================
# COMPLAINT PROCESSING ORCHESTRATOR
# ==================================================

def process_complaint(description, affected_households=None):
    """
    JANASHAKTI AI multi-agent workflow.

    Agent 1: Complaint classification
    Agent 2: RAG evidence retrieval
    LLM: Ollama Qwen response generation
    Quality Check: AI response validation
    Fallback: Evidence-based response
    Agent 3: Evidence verification
    Agent 4: Community impact assessment
    Agent 5: Priority assessment

    Administrator review remains mandatory.
    """

    if not isinstance(description, str) or not description.strip():

        return {
            "success": False,
            "message": "Please provide a complaint description.",
            "human_review_required": True,
        }

    description = description.strip()

    try:

        # ==================================================
        # AGENT 1: CLASSIFICATION
        # ==================================================

        classification = classify_issue(
            description,
            affected_households=affected_households,
        )

        if not isinstance(classification, dict):
            raise ValueError(
                "Classification agent returned an invalid response."
            )

        predicted_category = safe_text(
            classification.get("predicted_category")
        )

        if not predicted_category:
            predicted_category = safe_text(
                classification.get("category"),
                "Needs Review",
            )

        predicted_category = canonical_category(
            predicted_category
        )

        reported_category = extract_reported_category(
            description
        )

        # Select routing category.

        if (
            reported_category
            and reported_category != "Other"
        ):
            routing_category = reported_category

        elif (
            predicted_category
            and predicted_category not in {
                "Other",
                "Needs Review",
                "Unknown",
            }
        ):
            routing_category = predicted_category

        else:
            routing_category = "Needs Review"

        category_mismatch = (
            bool(reported_category)
            and reported_category != "Other"
            and predicted_category not in {
                "Other",
                "Needs Review",
                "Unknown",
                reported_category,
            }
        )

        classification["reported_category"] = (
            reported_category or "Not Provided"
        )

        classification["predicted_category"] = (
            predicted_category
        )

        classification["routing_category"] = (
            routing_category
        )

        classification["category"] = (
            routing_category
        )

        classification["category_mismatch"] = (
            category_mismatch
        )

        if category_mismatch:

            classification["reason"] = (
                safe_text(classification.get("reason"))
                + " Resident-selected category and AI-predicted "
                "category differ. Administrator review is required."
            )

        # ==================================================
        # AGENT 2: RAG EVIDENCE RETRIEVAL
        # ==================================================

        retrieval = retrieve_evidence(
            description,
            top_k=5,
        )

        if not isinstance(retrieval, dict):
            retrieval = {}

        raw_evidence = retrieval.get("evidence", [])

        if not isinstance(raw_evidence, list):
            raw_evidence = []

        evidence = filter_relevant_evidence(
            raw_evidence,
            routing_category,
        )

        sources = prepare_sources(evidence)

        retrieval["evidence"] = evidence
        retrieval["sources"] = sources
        retrieval["routing_category"] = routing_category

        retrieval["relevant_evidence_count"] = len(
            evidence
        )

        retrieval["excluded_unrelated_documents"] = (
            len(raw_evidence) - len(evidence)
        )

        # ==================================================
        # LLM: QWEN RESPONSE GENERATION
        # ==================================================

        if evidence:

            llm_result = generate_llm_response(
                description,
                evidence,
            )

        else:

            llm_result = {
                "success": False,
                "answer": "",
                "error": (
                    "No category-matched supporting documents "
                    "were found."
                ),
            }

        if not isinstance(llm_result, dict):

            llm_result = {
                "success": False,
                "answer": "",
                "error": "Invalid LLM response.",
            }

        llm_success = bool(
            llm_result.get("success")
        )

        answer = ""
        quality_error = None

        # ==================================================
        # AI RESPONSE QUALITY VALIDATION
        # ==================================================

        if llm_success:

            answer = safe_text(
                llm_result.get("answer")
            )

            if not answer:

                llm_success = False

                quality_error = (
                    "Ollama returned an empty response."
                )

            else:

                quality_ok, quality_error = (
                    validate_answer_quality(answer)
                )

                if not quality_ok:
                    llm_success = False

        # ==================================================
        # AUTOMATIC FALLBACK
        # ==================================================

        fallback_used = False

        if not llm_success:

            fallback_used = True

            answer = generate_fallback_answer(
                evidence
            )

        llm_model = (
            llm_result.get("model")
            if llm_success
            else "Rule-Based Fallback"
        )

        llm_error = (
            None
            if llm_success
            else (
                quality_error
                or llm_result.get("error")
                or "LLM response was unavailable."
            )
        )

        # ==================================================
        # AGENT 3: EVIDENCE VERIFICATION
        # ==================================================

        verification = verify_answer(
            answer,
            evidence,
        )

        if not isinstance(verification, dict):
            raise ValueError(
                "Evidence verification agent returned "
                "an invalid response."
            )

        evidence_status = safe_text(
            verification.get("status"),
            "Not Verified",
        )

        acceptable_evidence_statuses = {
            "Strong Evidence Match",
            "Partial Evidence Match",
        }

        evidence_supported = (
            evidence_status in acceptable_evidence_statuses
        )

        # ==================================================
        # AGENT 4: COMMUNITY IMPACT ASSESSMENT
        # ==================================================

        impact = assess_impact(
            description,
            affected_households=affected_households,
        )

        if not isinstance(impact, dict):
            raise ValueError(
                "Impact assessment agent returned "
                "an invalid response."
            )

        # ==================================================
        # AGENT 5: PRIORITY ASSESSMENT
        # ==================================================

        priority_households = affected_households

        if priority_households is None:

            priority_households = impact.get(
                "affected_households",
                0,
            )

        classification_urgency = safe_text(
            classification.get("urgency")
        ).title()

        impact_urgency = safe_text(
            impact.get("urgency")
        ).title()

        valid_urgencies = {
            "High",
            "Medium",
            "Low",
        }

        if classification_urgency in valid_urgencies:

            priority_urgency = classification_urgency

        elif impact_urgency in valid_urgencies:

            priority_urgency = impact_urgency

        else:

            priority_urgency = "Unknown"

        priority = calculate_priority(
            urgency=priority_urgency,
            impact=impact.get("impact_level"),
            affected_households=priority_households,
        )

        if not isinstance(priority, dict):
            raise ValueError(
                "Priority service returned an invalid response."
            )

        priority["urgency_used"] = priority_urgency

        # ==================================================
        # HUMAN REVIEW DECISION
        # ==================================================

        review_reasons = []

        if routing_category in {
            "Unknown",
            "Other",
            "Needs Review",
        }:

            review_reasons.append(
                "Complaint classification needs administrator review."
            )

        if category_mismatch:

            review_reasons.append(
                "Resident-selected category differs from "
                "the AI-predicted category."
            )

        if (
            classification_urgency not in valid_urgencies
            and impact_urgency not in valid_urgencies
        ):

            review_reasons.append(
                "Complaint urgency could not be determined."
            )

        elif classification_urgency not in valid_urgencies:

            review_reasons.append(
                "Classification Agent urgency was unavailable. "
                "Impact Agent urgency was used for priority calculation."
            )

        if not evidence:

            review_reasons.append(
                "No category-matched supporting evidence was found."
            )

        elif not evidence_supported:

            review_reasons.append(
                "Supporting evidence is insufficient."
            )

        if fallback_used:

            review_reasons.append(
                "LLM generation was unavailable or failed quality "
                "validation. An evidence-based fallback response was used."
            )

        if verification.get("human_review_required", True):

            review_reasons.append(
                "Evidence verification recommends human review."
            )

        if impact.get("human_review_required", True):

            review_reasons.append(
                "Community impact assessment recommends human review."
            )

        if priority.get("human_review_required", True):

            review_reasons.append(
                "Priority assessment recommends human review."
            )

        review_reasons.append(
            "Final administrator review is mandatory for all complaints."
        )

        # Never automatically approve real-world complaints.

        human_review_required = True

        # ==================================================
        # FINAL RESPONSE
        # ==================================================

        return {

            "success": True,

            "complaint": description,

            "classification": classification,

            "retrieval": retrieval,

            "ai_response": answer,

            "sources": sources,

            "verification": verification,

            "impact_assessment": impact,

            "priority_assessment": priority,

            "evidence_supported": evidence_supported,

            "human_review_required": human_review_required,

            "review_reasons": review_reasons,

            "real_world_verification_status": "Pending",

            "llm_used": llm_success,

            "llm_model": llm_model,

            "llm_error": llm_error,

            "llm_generation_success": llm_success,

            "fallback_used": fallback_used,

        }

    except Exception as error:

        return {

            "success": False,

            "message": (
                "Unable to complete the multi-agent complaint analysis."
            ),

            "error": str(error),

            "human_review_required": True,

            "real_world_verification_status": "Pending",

        }
