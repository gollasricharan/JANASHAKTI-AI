
from rag.vector_store import search_documents


# ==================================================
# EVIDENCE RETRIEVAL SERVICE
# ==================================================

def retrieve_evidence(complaint, top_k=3):
    """
    Retrieve relevant supporting documents for a complaint.

    Returns:
        query
        evidence
        message
        retrieval_success
    """

    # --------------------------------------------------
    # INPUT VALIDATION
    # --------------------------------------------------

    if not isinstance(complaint, str) or not complaint.strip():

        return {
            "query": "",
            "evidence": [],
            "message": "Please provide a complaint description.",
            "retrieval_success": False,
        }

    complaint = complaint.strip()

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 3

    top_k = max(1, min(top_k, 10))

    # --------------------------------------------------
    # DOCUMENT RETRIEVAL
    # --------------------------------------------------

    try:

        results = search_documents(
            query=complaint,
            top_k=top_k,
        )

        if not results:

            return {
                "query": complaint,
                "evidence": [],
                "message": "No supporting documents found.",
                "retrieval_success": False,
            }

        evidence = []

        # --------------------------------------------------
        # PROCESS RETRIEVED DOCUMENTS
        # --------------------------------------------------

        for result in results:

            if not isinstance(result, dict):
                continue

            text = str(
                result.get("text") or ""
            ).strip()

            if not text:
                continue

            source = str(
                result.get("source") or "Unknown document"
            ).strip()

            page = result.get("page")

            try:
                similarity = round(
                    float(result.get("similarity", 0)),
                    4
                )
            except (TypeError, ValueError):
                similarity = 0.0

            evidence.append({
                "source": source,
                "page": page,
                "text": text,
                "similarity": similarity,
            })

        # --------------------------------------------------
        # FINAL RESULT
        # --------------------------------------------------

        if not evidence:

            return {
                "query": complaint,
                "evidence": [],
                "message": (
                    "Documents were retrieved, but no usable "
                    "evidence content was found."
                ),
                "retrieval_success": False,
            }

        return {
            "query": complaint,
            "evidence": evidence,
            "message": (
                f"Successfully retrieved {len(evidence)} "
                "supporting evidence document(s)."
            ),
            "retrieval_success": True,
        }

    except Exception as error:

        return {
            "query": complaint,
            "evidence": [],
            "message": f"Evidence retrieval failed: {error}",
            "retrieval_success": False,
        }
