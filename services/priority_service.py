
def normalize_level(value):
    """Normalize urgency and impact values safely."""

    if value is None:
        return ""

    value = str(value).strip().lower()

    aliases = {
        "high": "High",
        "high urgency": "High",
        "medium": "Medium",
        "moderate": "Medium",
        "medium urgency": "Medium",
        "low": "Low",
        "low urgency": "Low",
    }

    return aliases.get(value, value.title())


def calculate_priority(urgency, impact, affected_households=None):
    """
    Calculate a rule-based complaint priority score.

    Maximum score: 100.

    Urgency:       40 points maximum
    Community impact: 35 points maximum
    Households:    25 points maximum

    Human administrator review is always required.
    """

    # ------------------------------------------
    # SCORING CONFIGURATION
    # ------------------------------------------

    urgency_points = {
        "High": 40,
        "Medium": 25,
        "Low": 10,
    }

    impact_points = {
        "High": 35,
        "Medium": 20,
        "Low": 10,
    }

    # ------------------------------------------
    # NORMALIZE INPUTS
    # ------------------------------------------

    normalized_urgency = normalize_level(urgency)
    normalized_impact = normalize_level(impact)

    # ------------------------------------------
    # URGENCY SCORE
    # ------------------------------------------

    urgency_score = urgency_points.get(
        normalized_urgency,
        0
    )

    # ------------------------------------------
    # IMPACT SCORE
    # ------------------------------------------

    impact_score = impact_points.get(
        normalized_impact,
        0
    )

    # ------------------------------------------
    # VALIDATE HOUSEHOLDS
    # ------------------------------------------

    try:
        if affected_households is None:
            households = 0
        else:
            households = int(float(affected_households))

        households = max(households, 0)

    except (ValueError, TypeError, OverflowError):
        households = 0

    # ------------------------------------------
    # HOUSEHOLD SCORE
    # ------------------------------------------

    if households >= 100:
        household_score = 25

    elif households >= 20:
        household_score = 15

    elif households > 0:
        household_score = 5

    else:
        household_score = 0

    # ------------------------------------------
    # TOTAL SCORE
    # ------------------------------------------

    score = (
        urgency_score
        + impact_score
        + household_score
    )

    score = min(max(score, 0), 100)

    # ------------------------------------------
    # PRIORITY LEVEL
    # ------------------------------------------

    if urgency_score == 0 or impact_score == 0:
        priority = "Not Assessed"

    elif score >= 80:
        priority = "Critical"

    elif score >= 60:
        priority = "High"

    elif score >= 35:
        priority = "Medium"

    else:
        priority = "Low"

    # ------------------------------------------
    # RETURN RESULT
    # ------------------------------------------

    return {
        "priority_score": score,
        "priority_level": priority,

        "urgency_points": urgency_score,
        "impact_points": impact_score,
        "household_points": household_score,

        "affected_households": households,

        # Diagnostic information
        "urgency_used": normalized_urgency,
        "impact_used": normalized_impact,

        "human_review_required": True,
    }
