import re
from collections import Counter


CATEGORY_KEYWORDS = {
    "Water shortage": [
        "water", "drinking water", "water supply",
        "no water", "shortage", "pipeline"
    ],
    "Waste management": [
        "garbage", "waste", "trash", "rubbish",
        "dump", "sanitation"
    ],
    "Damaged roads": [
        "road", "pothole", "damaged road",
        "broken road", "traffic"
    ],
    "Drainage": [
        "drainage", "drain", "sewage",
        "overflow", "stagnant water"
    ],
    "Streetlights": [
        "streetlight", "street light",
        "street lamp", "dark road", "no lights"
    ],
}


def analyze_complaint(description):
    """Analyze a complaint and generate preliminary insights."""

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Please provide a complaint description.")

    text = description.strip()
    text_lower = text.lower()

    matched_categories = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            matched_categories.append(category)

    if matched_categories:
        predicted_category = matched_categories[0]
    else:
        predicted_category = "Other"

    urgent_keywords = [
        "emergency",
        "dangerous",
        "accident",
        "injury",
        "injured",
        "collapsed",
        "contaminated",
        "fire",
        "electrocution",
        "life threatening",
    ]

    urgency_matches = [
        keyword
        for keyword in urgent_keywords
        if re.search(
            rf"\b{re.escape(keyword)}\b",
            text_lower
        )
    ]

    if urgency_matches:
        urgency = "Potentially urgent"
        urgency_reason = (
            "The description contains terms that may indicate "
            "a safety risk. Human review is required."
        )
    else:
        urgency = "Standard review"
        urgency_reason = (
            "No predefined urgent keywords were detected. "
            "This does not establish that the issue is safe."
        )

    words = re.findall(r"\b[a-zA-Z]+\b", text_lower)

    word_count = len(words)

    repeated_terms = [
        word
        for word, count in Counter(words).most_common(5)
        if count > 1 and len(word) > 4
    ]

    if word_count < 15:
        completeness = "Limited information"
        recommendation = (
            "Request additional details about the location, "
            "time, impact, and any supporting evidence."
        )
    else:
        completeness = "Description available"
        recommendation = (
            "Review the location and description, verify "
            "the reported conditions, and determine the "
            "appropriate next steps."
        )

    return {
        "predicted_category": predicted_category,
        "urgency": urgency,
        "urgency_reason": urgency_reason,
        "completeness": completeness,
        "word_count": word_count,
        "repeated_terms": repeated_terms,
        "recommendation": recommendation,
        "human_review_required": True,
        "matched_categories": matched_categories,
    }