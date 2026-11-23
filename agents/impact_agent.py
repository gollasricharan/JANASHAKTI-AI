
import re


# ==================================================
# NUMBER WORDS
# ==================================================

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_text(text):
    """Normalize complaint descriptions."""

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ==================================================
# NUMBER CONVERSION
# ==================================================

def parse_household_number(value):
    """Convert numeric or supported written counts."""

    value = str(value).strip().lower()

    if value.isdigit():
        return int(value)

    return NUMBER_WORDS.get(value)


# ==================================================
# HOUSEHOLD EXTRACTION
# ==================================================

def extract_households(description):
    """Extract explicitly reported household or family counts."""

    text = normalize_text(description)

    number_pattern = (
        r"(\d+|"
        + "|".join(NUMBER_WORDS.keys())
        + r")"
    )

    patterns = [
        number_pattern + r"\s+households?\b",
        number_pattern + r"\s+families\b",
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            value = parse_household_number(
                match.group(1)
            )

            if value is not None:
                return value

    return None


# ==================================================
# KEYWORD MATCHING
# ==================================================

def find_matching_terms(text, keywords):
    """Find complete matching phrases in complaint text."""

    matches = []

    for term in keywords:

        pattern = (
            r"\b"
            + re.escape(term)
            + r"\b"
        )

        if re.search(pattern, text):
            matches.append(term)

    return matches


# ==================================================
# COMMUNITY IMPACT ASSESSMENT
# ==================================================

def assess_impact(description, affected_households=None):
    """
    Assess potential community impact using reported
    safety risks, service disruptions and household counts.

    This is a preliminary automated assessment.
    Human review is always required.
    """

    # --------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------

    if not isinstance(description, str) or not description.strip():

        return {
            "impact_level": "Unknown",
            "urgency": "Unknown",
            "affected_households": affected_households,
            "impact_factors": [],
            "recommendation": "Provide a complaint description.",
            "human_review_required": True,
        }

    text = normalize_text(description)

    # --------------------------------------------------
    # HOUSEHOLD COUNT
    # --------------------------------------------------

    households = affected_households

    if households is None:
        households = extract_households(text)

    if households is not None:

        try:
            households = int(households)

            if households < 0:
                raise ValueError(
                    "Household count cannot be negative."
                )

        except (ValueError, TypeError, OverflowError):

            return {
                "impact_level": "Unknown",
                "urgency": "Unknown",
                "affected_households": affected_households,
                "impact_factors": [],
                "recommendation": (
                    "Provide a valid non-negative household count."
                ),
                "human_review_required": True,
            }

    # --------------------------------------------------
    # HIGH IMPACT INDICATORS
    # --------------------------------------------------

    high_impact_terms = [
        "contaminated water",
        "sewage overflow",
        "open manhole",
        "electric shock",
        "electrocution",
        "exposed electric wire",
        "exposed wire",
        "hanging electrical wire",
        "dangerous electrical wire",
        "hanging wire",
        "live wire",
        "electrical hazard",
        "fire",
        "building collapse",
        "collapse",
        "life threatening",
        "life-threatening",
        "serious accident",
        "major flooding",
        "severe flooding",
        "dangerous",
        "short circuit",
    ]

    # --------------------------------------------------
    # MEDIUM IMPACT INDICATORS
    # --------------------------------------------------

    medium_impact_terms = [
        "garbage accumulation",
        "overflowing dustbin",
        "blocked drain",
        "pothole",
        "damaged road",
        "broken streetlight",
        "water shortage",
        "power outage",
        "flickering light",
        "overflowing",
        "waterlogging",
        "pests",
        "irregular water supply",
        "waste accumulation",
    ]

    # --------------------------------------------------
    # IDENTIFY IMPACT FACTORS
    # --------------------------------------------------

    high_matches = find_matching_terms(
        text,
        high_impact_terms
    )

    medium_matches = find_matching_terms(
        text,
        medium_impact_terms
    )

    impact_factors = []

    # --------------------------------------------------
    # INITIAL IMPACT ASSESSMENT
    # --------------------------------------------------

    if high_matches:

        impact_level = "High"
        urgency = "High"

        impact_factors.extend(high_matches)

    elif medium_matches:

        impact_level = "Medium"
        urgency = "Medium"

        impact_factors.extend(medium_matches)

    else:

        impact_level = "Low"
        urgency = "Low"

        impact_factors.append(
            "No predefined high or medium impact indicator detected."
        )

    # --------------------------------------------------
    # HOUSEHOLD IMPACT ASSESSMENT
    # --------------------------------------------------

    if households is not None:

        if households >= 100:

            impact_level = "High"
            urgency = "High"

            impact_factors.append(
                f"{households} affected households were reported."
            )

        elif households >= 20 and impact_level == "Low":

            impact_level = "Medium"
            urgency = "Medium"

            impact_factors.append(
                f"{households} affected households were reported."
            )

        elif households > 0:

            impact_factors.append(
                f"{households} affected households were reported."
            )

    # --------------------------------------------------
    # RECOMMENDATIONS
    # --------------------------------------------------

    recommendations = {
        "High": (
            "Prioritize prompt human review and notify the "
            "appropriate responsible authority through "
            "official channels."
        ),

        "Medium": (
            "Arrange timely review and investigate the "
            "reported community impact."
        ),

        "Low": (
            "Record the complaint and review it through "
            "the normal complaint-handling process."
        ),
    }

    # --------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------

    return {
        "impact_level": impact_level,

        "urgency": urgency,

        "affected_households": households,

        "impact_factors": impact_factors,

        "recommendation": recommendations[urgency],

        "human_review_required": True,
    }
