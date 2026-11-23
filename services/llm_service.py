
import json
import re
import urllib.request
import urllib.error
import logging


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logger = logging.getLogger(__name__)


# --------------------------------------------------
# OLLAMA CONFIGURATION
# --------------------------------------------------

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:0.5b"

REQUEST_TIMEOUT = 120

MAX_EVIDENCE_DOCUMENTS = 3
MAX_EVIDENCE_LENGTH = 6500


# --------------------------------------------------
# TEXT PROCESSING
# --------------------------------------------------

STOP_WORDS = {
    "the", "and", "for", "are", "was", "were",
    "has", "have", "had", "this", "that", "with",
    "from", "into", "about", "their", "there",
    "they", "them", "then", "than", "been",
    "being", "our", "your", "you", "its", "not",
    "but", "can", "could", "should", "would",
    "will", "please", "area", "issue", "problem",
    "reported", "report", "community", "people",
    "households", "household", "days", "day"
}


def tokenize(text):
    """Convert text into meaningful lowercase keywords."""

    words = re.findall(
        r"[a-zA-Z]{3,}",
        str(text or "").lower()
    )

    return {
        word for word in words
        if word not in STOP_WORDS
    }


def clean_text(text):
    """Remove excessive whitespace from text."""

    return re.sub(
        r"\s+",
        " ",
        str(text or "")
    ).strip()


# --------------------------------------------------
# EVIDENCE PREPARATION
# --------------------------------------------------

def prepare_evidence(evidence, description=""):
    """
    Prepare relevant retrieved documents.

    Rank documents using complaint keyword overlap
    and retrieval similarity.
    """

    if not isinstance(evidence, list):
        return ""

    complaint_words = tokenize(description)

    prepared = []

    for index, item in enumerate(evidence):

        if not isinstance(item, dict):
            continue

        text = clean_text(
            item.get("text")
            or item.get("content")
            or item.get("page_content")
            or ""
        )

        if not text:
            continue

        source = clean_text(
            item.get("source")
            or item.get("document")
            or item.get("filename")
            or "Unknown document"
        )

        document_words = tokenize(
            source + " " + text
        )

        overlap = len(
            complaint_words.intersection(document_words)
        )

        relevance = (
            overlap / len(complaint_words)
            if complaint_words else 0
        )

        try:
            similarity = float(
                item.get("similarity", 0) or 0
            )
        except (ValueError, TypeError):
            similarity = 0.0

        prepared.append({
            "source": source,
            "text": text,
            "overlap": overlap,
            "relevance": relevance,
            "similarity": similarity,
            "original_index": index
        })

    if not prepared:
        return ""

    prepared.sort(
        key=lambda item: (
            item["overlap"],
            item["similarity"]
        ),
        reverse=True
    )

    relevant = [
        item for item in prepared
        if item["overlap"] > 0
    ]

    if not relevant:
        relevant = prepared[:1]

    relevant = relevant[:MAX_EVIDENCE_DOCUMENTS]

    sections = []
    total_length = 0

    for index, item in enumerate(relevant, start=1):

        section = (
            f"Reference {index}: {item['source']}\n"
            f"{item['text']}"
        )

        remaining = MAX_EVIDENCE_LENGTH - total_length

        if remaining <= 0:
            break

        section = section[:remaining]

        sections.append(section)
        total_length += len(section)

    return "\n\n".join(sections)


# --------------------------------------------------
# RULE-BASED FALLBACK
# --------------------------------------------------

CATEGORY_KEYWORDS = {
    "Water Supply": [
        "water", "drinking", "supply",
        "shortage", "tap", "pipeline"
    ],

    "Waste Management": [
        "garbage", "waste", "rubbish",
        "dumping", "collection", "litter"
    ],

    "Road Maintenance": [
        "road", "pothole", "damaged",
        "pavement"
    ],

    "Drainage": [
        "drain", "sewage", "drainage",
        "overflow", "waterlogging"
    ],

    "Streetlights": [
        "streetlight", "streetlights",
        "street light", "lamp", "lighting"
    ],

    "Electricity": [
        "electricity", "power", "outage",
        "transformer", "electric", "voltage"
    ],

    "Public Safety": [
        "safety", "unsafe", "crime",
        "accident", "security", "threat"
    ]
}


def detect_complaint_category(description):
    """
    Identify the complaint category.

    Explicit category labels are preferred.
    Whole-word matching prevents streetlights
    from being incorrectly classified as roads.
    """

    text = str(description or "").lower()

    # 1. Check explicit category labels first.

    category_pattern = (
        r"(?:reported\s+category|resident-selected\s+category|"
        r"ai-predicted\s+category|category)"
        r"\s*:\s*"
        r"(water supply|waste management|road maintenance|"
        r"drainage|streetlights|electricity|public safety)"
    )

    category_match = re.search(
        category_pattern,
        text
    )

    if category_match:

        selected = category_match.group(1).strip().lower()

        for category in CATEGORY_KEYWORDS:

            if category.lower() == selected:
                return category

    # 2. Whole-word keyword matching.

    category_patterns = {

        "Water Supply": [
            r"\bdrinking water\b",
            r"\bwater\b",
            r"\bsupply\b",
            r"\bshortage\b",
            r"\btap\b",
            r"\bpipeline\b"
        ],

        "Waste Management": [
            r"\bgarbage\b",
            r"\bwaste\b",
            r"\brubbish\b",
            r"\bdumping\b",
            r"\bcollection\b",
            r"\blitter\b"
        ],

        "Road Maintenance": [
            r"\broads?\b",
            r"\bpotholes?\b",
            r"\bdamaged\b",
            r"\bpavement\b",
            r"\broad repair\b"
        ],

        "Drainage": [
            r"\bdrains?\b",
            r"\bsewage\b",
            r"\bdrainage\b",
            r"\boverflow\b",
            r"\bwaterlogging\b"
        ],

        "Streetlights": [
            r"\bstreetlights?\b",
            r"\bstreet\s+lights?\b",
            r"\blamps?\b",
            r"\blighting\b"
        ],

        "Electricity": [
            r"\belectricity\b",
            r"\bpower\b",
            r"\boutage\b",
            r"\btransformer\b",
            r"\belectrical\b",
            r"\bvoltage\b"
        ],

        "Public Safety": [
            r"\bsafety\b",
            r"\bunsafe\b",
            r"\bcrime\b",
            r"\baccident\b",
            r"\bsecurity\b",
            r"\bthreat\b"
        ]
    }

    scores = {}

    for category, patterns in category_patterns.items():

        scores[category] = sum(
            1 for pattern in patterns
            if re.search(pattern, text)
        )

    matched = [
        (category, score)
        for category, score in scores.items()
        if score > 0
    ]

    if not matched:
        return "Community Issue"

    matched.sort(
        key=lambda item: item[1],
        reverse=True
    )

    # Avoid uncertain category assignment.

    if (
        len(matched) > 1
        and matched[0][1] == matched[1][1]
    ):
        return "Community Issue"

    return matched[0][0]


def generate_fallback_response(description, evidence_context):
    """
    Generate category-specific guidance without an LLM.

    This is rule-based text generation, not an AI-generated
    or independently verified assessment.
    """

    category = detect_complaint_category(description)

    evidence_lines = []

    for line in evidence_context.splitlines():

        if line.startswith("Reference "):

            evidence_lines.append(
                line.strip()
            )

    if evidence_lines:

        evidence_text = "\n".join(
            f"- {line}" for line in evidence_lines
        )

    else:

        evidence_text = (
            "No usable supporting reference was identified."
        )

    # Category-specific recommendations.

    recommendations = {

        "Water Supply": [
            "Record the affected locality and duration of the water interruption.",
            "Check whether nearby households are experiencing the same issue.",
            "Request an inspection of the relevant water supply infrastructure."
        ],

        "Waste Management": [
            "Record the location and extent of the waste accumulation.",
            "Check how long the waste has remained uncollected.",
            "Request inspection and appropriate waste collection."
        ],

        "Road Maintenance": [
            "Record the exact location and visible condition of the road damage.",
            "Check whether the damaged section creates a traffic or pedestrian hazard.",
            "Request a road inspection and maintenance assessment."
        ],

        "Drainage": [
            "Record the location and extent of the drainage blockage or overflow.",
            "Check whether nearby properties or roads are affected.",
            "Request inspection of the affected drainage infrastructure."
        ],

        "Streetlights": [
            "Record the exact locations of the non-functioning streetlights.",
            "Check whether nearby streetlights are also affected.",
            "Request inspection of the lighting equipment and repair of faulty units."
        ],

        "Electricity": [
            "Record the affected location and duration of the power interruption.",
            "Check whether the issue affects one building or multiple households.",
            "Request inspection of the affected electrical infrastructure."
        ],

        "Public Safety": [
            "Record the reported location, time and nature of the safety concern.",
            "Avoid approaching or confronting anyone involved in a potentially dangerous incident.",
            "Refer immediate threats or emergencies to the appropriate emergency services."
        ],

        "Community Issue": [
            "Record the exact location and nature of the reported issue.",
            "Collect additional details from affected residents.",
            "Arrange administrator review before deciding on further action."
        ]
    }

    next_steps = recommendations.get(
        category,
        recommendations["Community Issue"]
    )

    complaint_details = clean_text(description)

    return f"""
## 1. Issue Summary

A {category.lower()} complaint has been reported.

Reported complaint details: {complaint_details}

## 2. Relevant Supporting Evidence

{evidence_text}

The references are retrieved documents and have not been independently verified.

## 3. Recommended Next Steps

{chr(10).join(
    f"{index}. {step}"
    for index, step in enumerate(next_steps, start=1)
)}

## 4. Information Requiring Human Verification

1. Confirm the exact complaint location.
2. Verify the reported conditions through an appropriate inspection.
3. Confirm the number of affected households and the current situation.

This response was generated using rule-based fallback logic because the Ollama model was unavailable. Administrator review is required.
""".strip()


# --------------------------------------------------
# LLM RESPONSE GENERATION
# --------------------------------------------------

def generate_llm_response(description, evidence):
    """
    Generate complaint-specific guidance using Ollama.

    Automatically use rule-based fallback when Ollama
    is unavailable or returns an invalid response.
    """

    if (
        not isinstance(description, str)
        or not description.strip()
    ):

        return {
            "success": False,
            "answer": "",
            "model": None,
            "fallback_used": False,
            "error": "Complaint description is required."
        }

    description = description.strip()

    evidence_context = prepare_evidence(
        evidence,
        description
    )

    if not evidence_context:

        return {
            "success": False,
            "answer": (
                "No relevant supporting documents were found. "
                "Administrator review is required."
            ),
            "model": None,
            "fallback_used": False,
            "error": "No usable RAG evidence available."
        }

    # --------------------------------------------------
    # IMPROVED SYSTEM PROMPT
    # --------------------------------------------------

    system_prompt = """
You are JANASHAKTI AI, an intelligent multi-agent
community complaint analysis assistant.

Your responsibility is to analyze community complaints
and provide practical, evidence-aware recommendations.

STRICT RULES:

1. Understand the complaint before generating a response.
2. Do not copy the complete complaint into the summary.
3. Summarize the issue in your own words using 1-2 sentences.
4. Use retrieved documents only when relevant to the complaint.
5. Clearly distinguish resident-reported information
   from information supported by reference documents.
6. Never claim that a real-world incident is verified
   merely because a reference document exists.
7. Provide specific, actionable recommendations.
8. Avoid generic advice and repeating the complaint.
9. Do not invent government policies, officials,
   contact numbers, deadlines or procedures.
10. Do not introduce unrelated problems or solutions.
11. Identify information that administrators must verify.
12. Keep the response concise, professional and structured.
13. Human administrator review is mandatory.

For recommendations:
- Explain what action should be taken.
- Identify who should take the action when appropriate.
- Suggest practical verification or inspection steps.
- Do not claim that any action has already happened.
"""

    # --------------------------------------------------
    # IMPROVED USER PROMPT
    # --------------------------------------------------

    user_prompt = f"""
COMMUNITY COMPLAINT:

{description}

RELEVANT RETRIEVED REFERENCE DOCUMENTS:

{evidence_context}

Analyze this complaint and generate a useful response.

Use EXACTLY these four sections:

## 1. Issue Summary
Summarize the actual problem in 1-2 sentences.
Do not copy the full complaint.

## 2. Relevant Supporting Evidence
Mention the relevant reference filenames.
Explain briefly what the documents support.
Do not present general guidelines as proof of this incident.

## 3. Recommended Next Steps
Provide a maximum of 3 specific and practical actions.
Avoid repeating the resident's requested solution.
Focus on inspection, immediate response and prevention
where relevant to the complaint.

## 4. Information Requiring Human Verification
List up to 3 important details that require confirmation
through administrator review or physical inspection.

Do not add extra headings.
Do not repeat the complaint.
Do not invent facts.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 500,
            "top_p": 0.8
        }
    }

    # --------------------------------------------------
    # TRY OLLAMA FIRST
    # --------------------------------------------------

    try:

        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

        answer = (
            result.get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            raise ValueError(
                "Ollama returned an empty response."
            )

        logger.info(
            "JANASHAKTI AI response generated using Ollama: %s",
            MODEL_NAME
        )

        return {
            "success": True,
            "answer": answer,
            "model": MODEL_NAME,
            "fallback_used": False,
            "error": None
        }

    # --------------------------------------------------
    # AUTOMATIC FALLBACK
    # --------------------------------------------------

    except Exception as error:

        logger.warning(
            "Ollama unavailable or failed: %s",
            error
        )

        try:

            fallback_answer = generate_fallback_response(
                description,
                evidence_context
            )

            logger.info(
                "JANASHAKTI AI generated a rule-based fallback response."
            )

            return {
                "success": True,
                "answer": fallback_answer,
                "model": "Rule-Based Fallback",
                "fallback_used": True,
                "error": str(error)
            }

        except Exception as fallback_error:

            logger.exception(
                "Fallback generation failed."
            )

            return {
                "success": False,
                "answer": (
                    "AI response generation is currently unavailable. "
                    "Please arrange administrator review."
                ),
                "model": None,
                "fallback_used": True,
                "error": str(fallback_error)
            }
