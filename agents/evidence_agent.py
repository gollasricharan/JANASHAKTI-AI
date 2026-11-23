
import re


# ==================================================
# CONFIGURATION
# ==================================================

STOP_WORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for",
    "in", "on", "is", "are", "was", "were", "be",
    "by", "with", "their", "they", "this", "that",
    "should", "may", "can", "could", "would", "will",
    "residents", "complaint", "complaints", "based",
    "available", "reference", "document", "documents",
    "information", "following", "provided", "according",
    "generally", "from", "into", "about", "which",
    "when", "where", "what", "who", "how", "has",
    "have", "had", "been", "being", "its", "it",
    "as", "at", "these", "those", "such", "also",
    "than", "then", "there", "here", "but",
    "reported", "report", "issue", "issues",
    "community", "households", "household",
    "please", "using", "used", "appropriate",
    "each", "every"
}

NEGATION_WORDS = {
    "not", "no", "never", "without", "neither"
}

FACTUAL_SECTIONS = {
    "issue summary",
    "relevant supporting evidence",
    "supporting evidence"
}

IGNORED_PREFIXES = (
    "based on the available reference document",
    "based on the available reference documents",
    "note:",
    "human review is required",
    "this response was generated",
    "the references are retrieved documents"
)

CLAIM_MATCH_THRESHOLD = 0.65
STRONG_MATCH_THRESHOLD = 0.80
PARTIAL_MATCH_THRESHOLD = 0.50
MINIMUM_CLAIM_WORDS = 3


# ==================================================
# TEXT NORMALIZATION
# ==================================================

def normalize_text(text):
    """Normalize text before comparison."""

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def normalize_word(word):
    """Normalize common singular and plural variations."""

    word = str(word).lower().strip()

    if len(word) <= 3:
        return word

    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"

    if word.endswith("sses"):
        return word[:-2]

    if word.endswith("s") and not word.endswith(
        ("ss", "us", "is")
    ):
        return word[:-1]

    return word


def extract_important_words(text):
    """Extract meaningful words while preserving negation."""

    normalized = normalize_text(text)

    words = []

    for word in normalized.split():

        if word in STOP_WORDS and word not in NEGATION_WORDS:
            continue

        if len(word) <= 1:
            continue

        words.append(normalize_word(word))

    return words


# ==================================================
# HEADING DETECTION
# ==================================================

def normalize_heading(heading):
    """Normalize numbered and Markdown headings."""

    heading = str(heading).strip()

    heading = re.sub(r"^#+\s*", "", heading)

    heading = heading.replace("**", "")
    heading = heading.replace("__", "")
    heading = heading.replace("*", "")

    heading = re.sub(
        r"^\d+[\s.)-]+",
        "",
        heading
    )

    return heading.strip().lower().rstrip(":")


def identify_heading(line):
    """Identify relevant answer sections."""

    heading = normalize_heading(line)

    known_headings = {
        "issue summary",
        "relevant supporting evidence",
        "supporting evidence",
        "recommended next steps",
        "information requiring human verification"
    }

    if heading in known_headings:
        return heading

    return None


# ==================================================
# CLAIM EXTRACTION
# ==================================================

def clean_claim(line):
    """Remove bullets, numbering and document labels."""

    line = str(line).strip()

    line = re.sub(
        r"^\s*[-*•\d.)]+\s*",
        "",
        line
    ).strip()

    # Remove Markdown formatting.
    line = line.replace("**", "")
    line = line.replace("__", "")

    # Remove document filename prefixes.
    line = re.sub(
        r"^[\w.-]+\.txt\s*:\s*",
        "",
        line,
        flags=re.IGNORECASE
    )

    return line.strip()


def split_claims(answer):
    """
    Extract complete factual statements.

    Recommendations and human verification instructions
    are excluded from evidence scoring.
    """

    if not answer:
        return []

    claims = []
    current_section = None

    for line in str(answer).splitlines():

        line = line.strip()

        if not line:
            continue

        heading = identify_heading(line)

        if heading:
            current_section = heading
            continue

        if current_section not in FACTUAL_SECTIONS:
            continue

        line = clean_claim(line)

        if not line:
            continue

        if line.lower().startswith(IGNORED_PREFIXES):
            continue

        if re.match(
            r"^(reference|source)\s*\d*\s*:",
            line,
            flags=re.IGNORECASE
        ):
            continue

        # Split into complete sentences.
        sentences = re.split(
            r"(?<=[.!?])\s+(?=[A-Z0-9])",
            line
        )

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            if sentence.lower().startswith(IGNORED_PREFIXES):
                continue

            words = extract_important_words(sentence)

            if len(words) < MINIMUM_CLAIM_WORDS:
                continue

            claims.append({
                "claim": sentence,
                "section": current_section
            })

    return claims


# ==================================================
# EVIDENCE PREPARATION
# ==================================================

def prepare_evidence(evidence):
    """
    Prepare retrieved documents.

    Supports text, content and page_content.
    """

    evidence_items = []

    if not isinstance(evidence, list):
        return evidence_items

    for index, item in enumerate(evidence):

        if not isinstance(item, dict):
            continue

        text = str(
            item.get("text")
            or item.get("content")
            or item.get("page_content")
            or ""
        ).strip()

        if not text:
            continue

        normalized = normalize_text(text)

        words = set(
            extract_important_words(text)
        )

        if not normalized or not words:
            continue

        source = str(
            item.get("source")
            or item.get("document")
            or item.get("filename")
            or "Unknown document"
        ).strip()

        evidence_items.append({
            "source": source,
            "text": text,
            "normalized": normalized,
            "words": words,
            "index": index
        })

    return evidence_items


# ==================================================
# CLAIM COMPARISON
# ==================================================

def compare_claim_with_evidence(claim, evidence_words):
    """Calculate keyword overlap."""

    claim_words = set(
        extract_important_words(claim)
    )

    evidence_words = set(evidence_words)

    if not claim_words:
        return 0.0, []

    matched_words = sorted(
        claim_words.intersection(evidence_words)
    )

    ratio = len(matched_words) / len(claim_words)

    return ratio, matched_words


# ==================================================
# BEST EVIDENCE MATCH
# ==================================================

def find_best_evidence_match(claim, evidence_items):
    """
    Find the strongest keyword overlap with retrieved evidence.

    This does not establish real-world truth.
    """

    claim_words = set(
        extract_important_words(claim)
    )

    if not claim_words:

        return {
            "match_ratio": 0.0,
            "matched_words": [],
            "sources": [],
            "method": "No meaningful claim terms"
        }

    best_match = {
        "match_ratio": 0.0,
        "matched_words": [],
        "sources": [],
        "method": "Keyword overlap"
    }

    combined_words = set()

    for item in evidence_items:
        combined_words.update(item["words"])

    # Individual document matching.

    for item in evidence_items:

        ratio, matched_words = compare_claim_with_evidence(
            claim,
            item["words"]
        )

        if ratio > best_match["match_ratio"]:

            best_match = {
                "match_ratio": ratio,
                "matched_words": matched_words,
                "sources": [item["source"]],
                "method": "Individual document keyword overlap"
            }

    # Combined document matching.

    combined_ratio, combined_matches = (
        compare_claim_with_evidence(
            claim,
            combined_words
        )
    )

    if combined_ratio > best_match["match_ratio"]:

        supporting_sources = []

        for item in evidence_items:

            if set(combined_matches).intersection(item["words"]):

                supporting_sources.append(item["source"])

        best_match = {
            "match_ratio": combined_ratio,
            "matched_words": combined_matches,
            "sources": list(dict.fromkeys(supporting_sources)),
            "method": "Combined evidence keyword overlap"
        }

    return best_match


# ==================================================
# THREE-WAY CLAIM CLASSIFICATION
# ==================================================

def classify_claim(claim_data, match):
    """
    Classify factual statements.

    Issue Summary:
        Always resident-reported because the original
        complaint is not independently verified here.

    Supporting Evidence:
        Reference-supported only when sufficient
        keyword overlap exists.

    Other unsupported factual claims:
        Unverified.
    """

    section = claim_data.get("section", "")

    # Complaint details must never become independently
    # verified merely because their words overlap guidelines.

    if section == "issue summary":
        return "resident_reported"

    if match["match_ratio"] >= CLAIM_MATCH_THRESHOLD:
        return "reference_supported"

    return "unverified"


# ==================================================
# EMPTY RESULT
# ==================================================

def empty_verification_result(message):

    return {
        "status": "No Evidence Match",
        "verification_score": 0.0,
        "total_claims": 0,
        "verified_claims": [],
        "resident_reported_claims": [],
        "unverified_claims": [],
        "unsupported_claims": [message],
        "reference_supported_count": 0,
        "resident_reported_count": 0,
        "unverified_count": 0,
        "human_review_required": True,
        "verification_method": (
            "Section-aware three-way evidence classification"
        )
    }


# ==================================================
# MAIN EVIDENCE VERIFICATION
# ==================================================

def verify_answer(answer, evidence):
    """
    Verify factual statements against retrieved documents.

    This is lexical evidence analysis, not semantic
    fact-checking or real-world verification.

    Administrator review remains mandatory.
    """

    if not answer or not str(answer).strip():

        return empty_verification_result(
            "No answer was provided."
        )

    evidence_items = prepare_evidence(evidence)

    if not evidence_items:

        return empty_verification_result(
            "No supporting reference documents were retrieved."
        )

    claims = split_claims(answer)

    verified_claims = []
    resident_reported_claims = []
    unverified_claims = []

    # --------------------------------------------------
    # CLASSIFY EACH CLAIM
    # --------------------------------------------------

    for claim_data in claims:

        claim = claim_data["claim"]

        match = find_best_evidence_match(
            claim,
            evidence_items
        )

        classification = classify_claim(
            claim_data,
            match
        )

        claim_result = {
            "claim": claim,
            "match_ratio": round(match["match_ratio"], 2),
            "matched_terms": match["matched_words"],
            "source": match["sources"],
            "verification_method": match["method"],
            "classification": classification
        }

        if classification == "reference_supported":

            verified_claims.append(claim_result)

        elif classification == "resident_reported":

            claim_result["reason"] = (
                "This information comes from the submitted "
                "complaint and has not been independently confirmed."
            )

            resident_reported_claims.append(claim_result)

        else:

            claim_result["reason"] = (
                "This statement needs additional evidence "
                "or human investigation."
            )

            unverified_claims.append(claim_result)

    # --------------------------------------------------
    # VERIFICATION SCORE
    # --------------------------------------------------

    total_claims = len(claims)

    reference_supported_count = len(verified_claims)

    resident_reported_count = len(resident_reported_claims)

    unverified_count = len(unverified_claims)

    if total_claims == 0:

        score = 0.0
        status = "No Evidence Match"

    else:

        score = (
            reference_supported_count / total_claims
        )

        if score >= STRONG_MATCH_THRESHOLD:
            status = "Strong Evidence Match"

        elif score >= PARTIAL_MATCH_THRESHOLD:
            status = "Partial Evidence Match"

        else:
            status = "Weak Evidence Match"

    # Preserve compatibility with agent_orchestrator.py.

    unsupported_claims = (
        resident_reported_claims + unverified_claims
    )

    # --------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------

    return {
        "status": status,

        "verification_score": round(score, 2),

        "total_claims": total_claims,

        "verified_claims": verified_claims,

        "resident_reported_claims": resident_reported_claims,

        "unverified_claims": unverified_claims,

        "unsupported_claims": unsupported_claims,

        "reference_supported_count": reference_supported_count,

        "resident_reported_count": resident_reported_count,

        "unverified_count": unverified_count,

        "human_review_required": True,

        "verification_method": (
            "Section-aware classification using individual "
            "and combined reference keyword overlap. "
            "Not independent real-world verification."
        )
    }
