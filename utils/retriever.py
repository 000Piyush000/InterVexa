"""
Semantic retrieval over a company's FAISS index, with optional interview-mode
re-ranking (DSA / System Design / SQL / HR) and a confidence score derived
from similarity distances.
"""

from config import INTERVIEW_MODES, MIN_RELEVANCE_SCORE, TOP_K
from utils.vector_store import VectorStoreError, get_vector_store

# How much larger a candidate pool to pull before mode-based re-ranking.
_CANDIDATE_POOL_MULTIPLIER = 4
_MAX_CANDIDATE_POOL = 40


def _l2_distance_to_similarity(squared_distance):
    """Convert a FAISS L2 score to a 0-1 cosine-style similarity.

    IMPORTANT: faiss.IndexFlatL2.search() (used internally by LangChain's
    FAISS.similarity_search_with_score) returns the SQUARED L2 distance,
    not the Euclidean distance itself. For unit-normalized vectors:
        ||a - b||^2 = 2 - 2*cos(a, b)
    so cos(a, b) = 1 - squared_distance / 2. Clipped to [0, 1] for display.
    """
    similarity = 1.0 - (squared_distance / 2.0)
    return max(0.0, min(1.0, similarity))


def _keyword_boost(text, keywords):
    if not keywords:
        return 0
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def retrieve(company, query, mode="general", top_k=TOP_K):
    """Retrieve the most relevant chunks for a question, optionally boosted by mode.

    Raises:
        VectorStoreError: if the company has no processed documents yet.

    Returns:
        list of dicts: {content, source, chunk_id, total_chunks, company,
                         similarity, rank}
    """
    store = get_vector_store(company)
    if store is None:
        raise VectorStoreError(
            f"No processed documents found for '{company}'. Upload interview "
            "experiences and process them first."
        )

    mode_config = INTERVIEW_MODES.get(mode, INTERVIEW_MODES["general"])
    keywords = mode_config.get("keywords", [])

    pool_size = min(_MAX_CANDIDATE_POOL, max(top_k * _CANDIDATE_POOL_MULTIPLIER, top_k))
    try:
        raw_results = store.similarity_search_with_score(query, k=pool_size)
    except Exception as exc:  # noqa: BLE001
        raise VectorStoreError(f"Retrieval failed for '{company}': {exc}") from exc

    scored = []
    for document, distance in raw_results:
        similarity = _l2_distance_to_similarity(distance)
        boost = _keyword_boost(document.page_content, keywords)
        # Keyword matches give a small, bounded nudge on top of semantic
        # similarity so mode selection influences ranking without overriding
        # genuine semantic relevance.
        combined_score = similarity + min(boost, 5) * 0.03
        scored.append((combined_score, similarity, document))

    scored.sort(key=lambda item: item[0], reverse=True)
    top_results = scored[:top_k]

    results = []
    for rank, (_, similarity, document) in enumerate(top_results, start=1):
        results.append(
            {
                "content": document.page_content,
                "source": document.metadata.get("source", "unknown"),
                "chunk_id": document.metadata.get("chunk_id", "?"),
                "total_chunks": document.metadata.get("total_chunks", "?"),
                "company": document.metadata.get("company", company),
                "similarity": round(similarity, 4),
                "rank": rank,
            }
        )
    return results


def compute_confidence(results):
    """Derive a human-friendly confidence label + score from retrieved chunks."""
    if not results:
        return {"score": 0.0, "label": "No Match", "level": "none"}

    relevant = [r for r in results if r["similarity"] >= MIN_RELEVANCE_SCORE]
    if not relevant:
        return {"score": 0.0, "label": "No Match", "level": "none"}

    avg_similarity = sum(r["similarity"] for r in relevant) / len(relevant)
    score = round(avg_similarity * 100, 1)

    if avg_similarity >= 0.55:
        label, level = "High", "high"
    elif avg_similarity >= 0.35:
        label, level = "Medium", "medium"
    else:
        label, level = "Low", "low"

    return {"score": score, "label": label, "level": level}
