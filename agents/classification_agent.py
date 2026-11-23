
import re


# ==================================================
# CATEGORY KEYWORDS
# ==================================================

CATEGORY_KEYWORDS = {
    "Water Supply": [
        "water shortage", "no water", "water supply",
        "water interruption", "drinking water",
        "water leakage", "low water pressure",
        "irregular water supply", "water scarcity",
        "dry tap",
    ],

    "Waste Management": [
        "garbage", "waste", "dustbin", "rubbish",
        "dumping", "uncollected garbage",
        "sanitation", "waste collection",
        "pests", "overflowing garbage",
    ],

    "Road Maintenance": [
        "pothole", "damaged road", "broken road",
        "footpath", "road damage", "road repair",
        "cracked road", "damaged footpath",
    ],

    "Drainage": [
        "blocked drain", "drainage", "sewage",
        "overflowing drain", "waterlogging",
        "drain blockage", "sewage overflow",
        "blocked sewage",
    ],

    "Electricity": [
        "power outage", "electricity", "power cut",
        "electrical supply", "transformer",
        "hanging electrical wire", "dangerous electrical wire",
        "electrical wire", "hanging wire",
        "exposed wire", "live wire",
        "electrical hazard", "electric shock",
        "electricity leakage", "short circuit",
    ],

    "Streetlights": [
        "streetlight", "streetlights", "street light",
        "street lights", "flickering light",
        "broken streetlight", "broken street light",
        "poorly illuminated", "dark street",
        "streetlights not working",
        "street light not working",
        "lights not working", "no street lights",
        "no streetlight",
    ],

    "Public Safety": [
        "unsafe", "public danger", "accident risk",
        "safety hazard", "dangerous infrastructure",
        "building collapse", "fire hazard",
        "public safety",
    ],
}


# ==================================================
# CATEGORY ALIASES
# ==================================================

CATEGORY_ALIASES = {
    "water supply": "Water Supply",
    "water shortage": "Water Supply",
    "water": "Water Supply",

    "waste management": "Waste Management",
    "waste": "Waste Management",
    "garbage": "Waste Management",

    "road maintenance": "Road Maintenance",
    "damaged roads": "Road Maintenance",
    "roads": "Road Maintenance",

    "drainage": "Drainage",
    "drainage problems": "Drainage",

    "electricity": "Electricity",
    "power outage": "Electricity",

    "streetlights": "Streetlights",
    "street lights": "Streetlights",
    "streetlight": "Streetlights",

    "public safety": "Public Safety",

    "other": "Other",
}


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_text(text):
    if text is None:
        return ""

    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def normalize_category(category):
    value = str(category or "").strip().lower()
    return CATEGORY_ALIASES.get(value)


# ==================================================
# RESIDENT-SELECTED CATEGORY
# ==================================================

def extract_reported_category(description):
    """
    Extract the category selected by the resident.
    Example: Reported category: Water shortage.
    """

    if not isinstance(description, str):
        return None

    match = re.search(
        r"^\s*Reported category\s*:\s*(.+?)\s*$",
        description,
        re.IGNORECASE | re.MULTILINE,
    )

    if not match:
        return None

    return normalize_category(match.group(1))


# ==================================================
# NUMBER WORD CONVERSION
# ==================================================

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}


def parse_number(value):
    value = str(value).strip().lower()

    if value.isdigit():
        return int(value)

    return NUMBER_WORDS.get(value)


# ==================================================
# DURATION EXTRACTION
# ==================================================

def extract_duration_days(text):
    text = normalize_text(text)

    pattern = (
        r"\b(\d+|"
        + "|".join(NUMBER_WORDS.keys())
        + r")\s*(days?|d|weeks?|wks?|months?|mos?)\b"
    )

    match = re.search(pattern, text)

    if not match:
        return 0

    number = parse_number(match.group(1))

    if number is None:
        return 0

    unit = match.group(2)

    if unit.startswith("w"):
        return number * 7

    if unit.startswith("m"):
        return number * 30

    return number


# ==================================================
# HOUSEHOLD EXTRACTION
# ==================================================

def extract_households(text):
    text = normalize_text(text)

    pattern = (
        r"\b(\d+|"
        + "|".join(NUMBER_WORDS.keys())
        + r")\s+(?:households?|families)\b"
    )

    match = re.search(pattern, text)

    if not match:
        return None

    return parse_number(match.group(1))


def get_household_count(description, affected_households=None):
    if affected_households is not None:
        try:
            value = int(affected_households)

            if value >= 0:
                return value

        except (ValueError, TypeError, OverflowError):
            pass

    return extract_households(description)


# ==================================================
# CATEGORY CLASSIFICATION
# ==================================================

def classify_category(text):
    """
    Score complaint categories using keyword matches.
    Return Needs Review only when no selected category
    is available and the strongest matches are tied.
    """

    text = normalize_text(text)
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0

        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"

            if re.search(pattern, text):
                score += 2 if len(keyword.split()) > 1 else 1

        scores[category] = score

    best_score = max(scores.values(), default=0)

    if best_score == 0:
        return {
            "category": "Other",
            "score": 0,
            "matched_categories": [],
        }

    matched_categories = [
        category
        for category, score in scores.items()
        if score == best_score
    ]

    if len(matched_categories) > 1:
        return {
            "category": "Needs Review",
            "score": best_score,
            "matched_categories": matched_categories,
        }

    return {
        "category": matched_categories[0],
        "score": best_score,
        "matched_categories": matched_categories,
    }


# ==================================================
# URGENCY ASSESSMENT
# ==================================================

def assess_urgency(text, category, affected_households=None):
    """
    Estimate urgency from safety risks, duration
    and affected households.

    This is automated decision support, not an
    official emergency assessment.
    """

    text = normalize_text(text)

    high_risk_terms = [
        "life threatening",
        "life-threatening",
        "emergency",
        "electrocution",
        "electric shock",
        "fire",
        "building collapse",
        "major flooding",
        "severe flooding",
        "contaminated drinking water",
        "unsafe drinking water",
        "hanging electrical wire",
        "exposed wire",
        "live wire",
        "electrical hazard",
        "hanging wire",
        "short circuit",
        "fire hazard",
    ]

    medium_risk_terms = [
        "overflowing",
        "blocked",
        "pests",
        "unsafe",
        "severe",
        "accident risk",
        "waterlogging",
        "sewage overflow",
        "foul smell",
        "unhealthy environment",
    ]

    duration_days = extract_duration_days(text)

    households = get_household_count(
        text,
        affected_households,
    )

    # High-risk indicators.
    if any(term in text for term in high_risk_terms):
        return (
            "High",
            "Potential safety or emergency risk detected.",
        )

    # Water supply interruption.
    if category == "Water Supply" and duration_days >= 3:
        return (
            "High",
            f"Water interruption reported for approximately "
            f"{duration_days} days.",
        )

    if category == "Water Supply" and duration_days >= 2:
        return (
            "Medium",
            "Extended water interruption reported.",
        )

    # Large community impact.
    if households is not None and households >= 100:
        return (
            "High",
            f"{households} affected households were reported.",
        )

    if households is not None and households >= 25:
        return (
            "Medium",
            f"{households} affected households were reported.",
        )

    # Duration-based assessment.
    if duration_days >= 7:
        return (
            "High",
            "Problem reportedly continued for at least seven days.",
        )

    if duration_days >= 2:
        return (
            "Medium",
            "Problem reportedly continued for multiple days.",
        )

    # General community disruption.
    if any(term in text for term in medium_risk_terms):
        return (
            "Medium",
            "Potential community disruption detected.",
        )

    return (
        "Low",
        "No strong urgency indicators were detected.",
    )


# ==================================================
# MAIN CLASSIFICATION FUNCTION
# ==================================================

def classify_issue(description, affected_households=None):
    """
    Classify a community complaint and estimate urgency.

    Returns the existing fields:
        category
        urgency
        reason
        human_review_required

    Also returns:
        reported_category
        predicted_category
        matched_categories
    """

    if not isinstance(description, str) or not description.strip():
        return {
            "category": "Unknown",
            "urgency": "Unknown",
            "reason": "No complaint description provided.",
            "reported_category": None,
            "predicted_category": "Unknown",
            "matched_categories": [],
            "human_review_required": True,
        }

    text = normalize_text(description)

    if not text:
        return {
            "category": "Unknown",
            "urgency": "Unknown",
            "reason": "Complaint description is invalid.",
            "reported_category": None,
            "predicted_category": "Unknown",
            "matched_categories": [],
            "human_review_required": True,
        }

    # Read the resident-selected category.
    reported_category = extract_reported_category(description)

    # Independently classify the complaint text.
    category_result = classify_category(text)

    predicted_category = category_result["category"]

    matched_categories = category_result["matched_categories"]

    # Use selected category for routing when available.
    if reported_category and reported_category != "Other":
        final_category = reported_category
        category_reason = (
            f"Resident selected {reported_category}. "
            f"Keyword-based prediction: {predicted_category}."
        )

    else:
        final_category = predicted_category
        category_reason = (
            f"Keyword-based prediction: {predicted_category}."
        )

    # Ambiguous category without resident selection.
    if final_category == "Needs Review":
        urgency = "Unknown"

        return {
            "category": "Needs Review",
            "urgency": urgency,
            "reason": (
                f"Multiple categories matched: "
                f"{', '.join(matched_categories)}. "
                "Administrator review is required."
            ),
            "reported_category": reported_category,
            "predicted_category": predicted_category,
            "matched_categories": matched_categories,
            "human_review_required": True,
        }

    # No identifiable category.
    if final_category == "Other":
        return {
            "category": "Other",
            "urgency": "Unknown",
            "reason": (
                "No clear category match was found. "
                "Manual review is required."
            ),
            "reported_category": reported_category,
            "predicted_category": predicted_category,
            "matched_categories": matched_categories,
            "human_review_required": True,
        }

    # Assess urgency using the selected/final category.
    urgency, urgency_reason = assess_urgency(
        text,
        final_category,
        affected_households,
    )

    # Flag disagreement for administrator review.
    category_disagreement = (
        reported_category is not None
        and reported_category != "Other"
        and predicted_category not in {
            reported_category,
            "Needs Review",
            "Other",
        }
    )

    reason = (
        f"{category_reason} "
        f"{urgency_reason} "
        "Automated assessment requires human review."
    )

    if category_disagreement:
        reason += (
            " The selected category and keyword prediction differ."
        )

    return {
        "category": final_category,
        "urgency": urgency,
        "reason": reason,
        "reported_category": reported_category,
        "predicted_category": predicted_category,
        "matched_categories": matched_categories,
        "human_review_required": True,
    }
