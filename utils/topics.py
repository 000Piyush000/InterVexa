"""
Frequently-asked-topic analysis (bonus feature).

Counts occurrences of known interview-mode keywords across a company's
indexed chunks, without any additional LLM calls, to surface which topics
show up most often in the uploaded interview experiences.
"""

from collections import Counter

from config import INTERVIEW_MODES
from utils.vector_store import iter_documents, list_companies_with_data

_ALL_KEYWORDS = sorted(
    {keyword for mode in INTERVIEW_MODES.values() for keyword in mode.get("keywords", [])}
)

_KEYWORD_TO_MODE = {}
for _mode_key, _mode_cfg in INTERVIEW_MODES.items():
    for _keyword in _mode_cfg.get("keywords", []):
        _KEYWORD_TO_MODE.setdefault(_keyword, _mode_key)


def get_frequent_topics(company=None, top_n=12):
    """Return the most frequently mentioned topics for one company or all companies.

    Returns a list of dicts: {"topic": str, "count": int, "mode": str}
    sorted by count descending.
    """
    if company:
        documents = iter_documents(company)
    else:
        documents = []
        for name in list_companies_with_data():
            documents.extend(iter_documents(name))

    if not documents:
        return []

    counter = Counter()
    for document in documents:
        lowered = document.page_content.lower()
        for keyword in _ALL_KEYWORDS:
            if keyword in lowered:
                counter[keyword] += lowered.count(keyword)

    topics = []
    for keyword, count in counter.most_common(top_n):
        if count <= 0:
            continue
        topics.append({"topic": keyword, "count": count, "mode": _KEYWORD_TO_MODE.get(keyword, "general")})
    return topics
