"""
Persistent, per-company FAISS vector store management.

Each company gets its own folder under `embeddings/<company>/` containing:
    - a LangChain FAISS index (`index.faiss` + `index.pkl`)
    - a `manifest.json` tracking which source files have already been
      embedded (by filename, size and modification time), so re-running the
      processing pipeline never re-embeds unchanged files.

An in-memory cache avoids reloading the FAISS index from disk on every chat
request; the cache is refreshed automatically whenever new documents are
added.
"""

import json
import os
import threading

from langchain_community.vectorstores import FAISS

from config import DATA_DIR, EMBEDDINGS_DIR
from utils.chunker import chunk_document
from utils.embeddings import get_embeddings
from utils.pdf_loader import DocumentLoadError, extract_and_clean

MANIFEST_FILENAME = "manifest.json"
INDEX_NAME = "index"

_store_cache = {}
_cache_lock = threading.Lock()


class VectorStoreError(Exception):
    """Raised for unrecoverable vector-store failures (e.g. missing index)."""


def _company_dir(company):
    path = os.path.join(EMBEDDINGS_DIR, company)
    os.makedirs(path, exist_ok=True)
    return path


def _data_dir(company):
    return os.path.join(DATA_DIR, company)


def _manifest_path(company):
    return os.path.join(_company_dir(company), MANIFEST_FILENAME)


def load_manifest(company):
    path = _manifest_path(company)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}


def save_manifest(company, manifest):
    path = _manifest_path(company)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)


def index_exists(company):
    company_dir = _company_dir(company)
    return os.path.isfile(os.path.join(company_dir, f"{INDEX_NAME}.faiss"))


def _load_from_disk(company):
    if not index_exists(company):
        return None
    embeddings = get_embeddings()
    return FAISS.load_local(
        _company_dir(company),
        embeddings,
        index_name=INDEX_NAME,
        allow_dangerous_deserialization=True,
    )


def get_vector_store(company, use_cache=True):
    """Return the cached FAISS store for a company, loading it from disk if needed.

    Returns None if the company has no index yet (i.e. nothing processed).
    """
    with _cache_lock:
        if use_cache and company in _store_cache:
            return _store_cache[company]
        store = _load_from_disk(company)
        if store is not None:
            _store_cache[company] = store
        return store


def _set_cache(company, store):
    with _cache_lock:
        _store_cache[company] = store


def list_source_files(company):
    """List uploaded PDF/TXT files currently sitting in data/<company>."""
    directory = _data_dir(company)
    if not os.path.isdir(directory):
        return []
    files = []
    for name in sorted(os.listdir(directory)):
        if name.startswith("."):
            continue
        if name.lower().endswith((".pdf", ".txt")):
            files.append(name)
    return files


def _file_fingerprint(path):
    stat = os.stat(path)
    return {"size": stat.st_size, "mtime": stat.st_mtime}


def build_or_update_index(company, force_rebuild=False):
    """Scan data/<company>, embed any new or changed files, persist the index.

    Returns a stats dict:
        {
            "processed_files": [...],
            "skipped_files": [...],
            "failed_files": [{"file": name, "error": msg}, ...],
            "chunks_added": int,
            "total_documents": int,
        }
    """
    directory = _data_dir(company)
    os.makedirs(directory, exist_ok=True)
    source_files = list_source_files(company)

    manifest = {} if force_rebuild else load_manifest(company)
    store = None if force_rebuild else get_vector_store(company, use_cache=False)

    processed_files = []
    skipped_files = []
    failed_files = []
    new_documents = []

    for filename in source_files:
        file_path = os.path.join(directory, filename)
        fingerprint = _file_fingerprint(file_path)
        cached = manifest.get(filename)
        if cached and cached.get("size") == fingerprint["size"] and cached.get("mtime") == fingerprint["mtime"]:
            skipped_files.append(filename)
            continue

        try:
            cleaned_text = extract_and_clean(file_path)
            documents = chunk_document(cleaned_text, filename, company)
            if not documents:
                raise DocumentLoadError(f"'{filename}' produced no chunks.")
        except DocumentLoadError as exc:
            failed_files.append({"file": filename, "error": str(exc)})
            continue

        new_documents.extend(documents)
        manifest[filename] = {**fingerprint, "num_chunks": len(documents)}
        processed_files.append(filename)

    chunks_added = len(new_documents)

    if new_documents:
        embeddings = get_embeddings()
        if store is None:
            store = FAISS.from_documents(new_documents, embeddings)
        else:
            store.add_documents(new_documents)
        store.save_local(_company_dir(company), index_name=INDEX_NAME)
        _set_cache(company, store)
        save_manifest(company, manifest)
    elif force_rebuild:
        # Force rebuild requested but there is nothing to embed (empty folder).
        save_manifest(company, manifest)

    total_documents = 0
    current_store = get_vector_store(company, use_cache=True)
    if current_store is not None:
        total_documents = current_store.index.ntotal

    return {
        "processed_files": processed_files,
        "skipped_files": skipped_files,
        "failed_files": failed_files,
        "chunks_added": chunks_added,
        "total_documents": total_documents,
    }


def get_index_stats(company):
    """Lightweight status info used by the UI (no embedding model load required)."""
    manifest = load_manifest(company)
    num_files = len(manifest)
    num_chunks = sum(entry.get("num_chunks", 0) for entry in manifest.values())
    return {
        "company": company,
        "has_index": index_exists(company),
        "num_files": num_files,
        "num_chunks": num_chunks,
        "files": sorted(manifest.keys()),
    }


def iter_documents(company):
    """Return every chunk (LangChain Document) currently indexed for a company."""
    store = get_vector_store(company)
    if store is None:
        return []
    return list(store.docstore._dict.values())


def list_companies_with_data():
    """List every company folder under data/ that currently has an index."""
    if not os.path.isdir(EMBEDDINGS_DIR):
        return []
    companies = []
    for name in sorted(os.listdir(EMBEDDINGS_DIR)):
        if index_exists(name):
            companies.append(name)
    return companies
