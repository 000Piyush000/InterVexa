"""
Persistent storage for the Help & Support FAQ list shown in the UI.

FAQs are stored as a flat JSON list under ``config.FAQS_FILE``. The file is
seeded with a handful of defaults on first read so Help & Support is never
empty, and new entries submitted through the UI are appended to it.
"""

import json
import os
import threading

import config

_lock = threading.Lock()

_DEFAULT_FAQS = [
    {
        "question": "Is my data ever sent anywhere?",
        "answer": "No. Every document you upload, every embedding, and every generated answer stays "
        "entirely on your own machine via FAISS and a local Ollama model — nothing leaves your computer.",
    },
    {
        "question": "Why did it say it can't answer my question?",
        "answer": "Intervexa only answers from documents you've uploaded for that company. If the "
        "uploaded interview experiences don't mention it, it tells you directly instead of guessing.",
    },
    {
        "question": "What do I need installed before chat works?",
        "answer": "Install Ollama, run `ollama serve` in a terminal, then `ollama pull llama3`. You can "
        "still upload and process documents before that — only the chat answers need Ollama running.",
    },
    {
        "question": "Can I add my own company?",
        "answer": "Yes — use the \"Add Company\" option to create a new company, then upload PDF or "
        "TXT interview experiences for it from the Upload page.",
    },
    {
        "question": "What file types are supported?",
        "answer": "PDF and TXT files, up to the configured size limit per file (see the Upload page).",
    },
]


class FaqError(Exception):
    """Raised when a FAQ cannot be added because required fields are missing."""


def _read():
    if not os.path.isfile(config.FAQS_FILE):
        return None
    try:
        with open(config.FAQS_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def _write(faqs):
    os.makedirs(os.path.dirname(config.FAQS_FILE), exist_ok=True)
    with open(config.FAQS_FILE, "w", encoding="utf-8") as handle:
        json.dump(faqs, handle, indent=2)


def get_faqs():
    """Return the current FAQ list, seeding it with defaults on first use."""
    with _lock:
        faqs = _read()
        if faqs is None:
            faqs = [dict(item, id=index + 1) for index, item in enumerate(_DEFAULT_FAQS)]
            _write(faqs)
        return faqs


def add_faq(question, answer):
    """Append a new FAQ entry and persist it, returning the stored entry."""
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer:
        raise FaqError("Both a question and an answer are required.")
    if len(question) > 200:
        raise FaqError("Question is too long (max 200 characters).")
    if len(answer) > 1000:
        raise FaqError("Answer is too long (max 1000 characters).")

    with _lock:
        faqs = _read()
        if faqs is None:
            faqs = [dict(item, id=index + 1) for index, item in enumerate(_DEFAULT_FAQS)]
        next_id = max((item.get("id", 0) for item in faqs), default=0) + 1
        entry = {"id": next_id, "question": question, "answer": answer}
        faqs.append(entry)
        _write(faqs)
        return entry
