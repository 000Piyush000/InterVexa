"""
Sentence-Transformer embedding backend, exposed through the LangChain
`Embeddings` interface so it can be plugged directly into a LangChain FAISS
vector store.

The SentenceTransformer model is loaded lazily and cached as a module-level
singleton, since loading `all-MiniLM-L6-v2` from disk/HuggingFace cache takes
a noticeable amount of time and should only happen once per process.
"""

import threading

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_DEVICE, EMBEDDING_MODEL_NAME

_model_lock = threading.Lock()
_model = None


class EmbeddingModelError(Exception):
    """Raised when the sentence-transformer model cannot be loaded."""


def get_model():
    """Return the shared SentenceTransformer instance, loading it on first use."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    _model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE)
                except Exception as exc:  # noqa: BLE001
                    raise EmbeddingModelError(
                        f"Failed to load embedding model '{EMBEDDING_MODEL_NAME}': {exc}"
                    ) from exc
    return _model


class SentenceTransformerEmbeddings(Embeddings):
    """LangChain-compatible embeddings wrapper around Sentence Transformers."""

    def __init__(self, model_name=EMBEDDING_MODEL_NAME):
        self.model_name = model_name

    def embed_documents(self, texts):
        model = get_model()
        vectors = model.encode(
            list(texts),
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, text):
        model = get_model()
        vector = model.encode(
            [text],
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector[0].tolist()


def get_embeddings():
    """Factory returning a ready-to-use LangChain Embeddings instance."""
    return SentenceTransformerEmbeddings()
