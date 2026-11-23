
from sentence_transformers import SentenceTransformer
import numpy as np
import re

from rag.document_loader import load_documents


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

SIMILARITY_THRESHOLD = 0.30
MAX_CHUNKS_PER_SOURCE = 2
LEXICAL_SCORE_WEIGHT = 0.30

_STOP_WORDS = {
    "a", "about", "an", "and", "are", "can", "do", "for", "how",
    "in", "is", "should", "the", "to", "what", "when", "where",
    "who", "why", "with", "would", "residents", "resident", "report",
    "reporting", "problem", "issue", "issues",
}

_model = None
_cached_documents = None
_cached_embeddings = None


def get_model():
    """Load the embedding model only once."""

    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def get_document_embeddings():
    """Load documents and cache their embeddings."""

    global _cached_documents, _cached_embeddings

    documents = load_documents()

    if not documents:
        return [], None

    if documents != _cached_documents:
        model = get_model()

        document_texts = [
            document["text"]
            for document in documents
        ]

        _cached_embeddings = model.encode(
            document_texts,
            normalize_embeddings=True
        )

        _cached_documents = documents.copy()

    return documents, _cached_embeddings


def _search_terms(text):
    """Return informative, lightly normalized terms for lexical matching."""

    terms = set()
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        if term in _STOP_WORDS or len(term) < 3:
            continue
        if term.endswith("ies") and len(term) > 4:
            term = term[:-3] + "y"
        elif term.endswith("s") and not term.endswith(("ss", "us", "is")):
            term = term[:-1]
        terms.add(term)
    return terms


def search_documents(query, top_k=3):
    """Retrieve the most relevant document passages."""

    if not query or not query.strip():
        return []

    documents, document_embeddings = get_document_embeddings()

    if not documents or document_embeddings is None:
        return []

    model = get_model()

    query_embedding = model.encode(
        [query.strip()],
        normalize_embeddings=True
    )[0]

    similarities = np.dot(
        document_embeddings,
        query_embedding
    )

    query_terms = _search_terms(query)
    combined_scores = []
    for index, document in enumerate(documents):
        document_terms = _search_terms(document["text"])
        lexical_score = (
            len(query_terms & document_terms) / len(query_terms)
            if query_terms else 0.0
        )
        combined_scores.append(
            float(similarities[index]) + LEXICAL_SCORE_WEIGHT * lexical_score
        )

    # Keep semantic similarity as the threshold and reported score. Direct
    # topic matches influence order when broad semantic matches score highly.
    ranked_indices = np.argsort(combined_scores)[::-1]

    results = []
    source_counts = {}

    for index in ranked_indices:

        similarity = float(similarities[index])

        if similarity < SIMILARITY_THRESHOLD:
            continue

        document = documents[int(index)]
        source = document["source"]

        if source_counts.get(source, 0) >= MAX_CHUNKS_PER_SOURCE:
            continue

        results.append({
            "source": source,
            "page": document["page"],
            "text": document["text"],
            "similarity": similarity,
        })

        source_counts[source] = (
            source_counts.get(source, 0) + 1
        )

        if len(results) >= top_k:
            break

    return results
