"""
Splits cleaned document text into overlapping chunks suitable for embedding,
and wraps each chunk as a LangChain Document carrying citation metadata.
"""

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import CHUNK_OVERLAP, CHUNK_SIZE

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
)


def split_text(text):
    """Split raw text into a list of chunk strings."""
    if not text or not text.strip():
        return []
    return _splitter.split_text(text)


def chunk_document(text, source_filename, company):
    """Split text into LangChain Documents with citation metadata attached.

    Each Document's metadata contains:
        source:  original filename (shown in citations)
        company: company folder the file belongs to
        chunk_id: 1-based index of the chunk within this document
    """
    chunks = split_text(text)
    documents = []
    for index, chunk_text in enumerate(chunks, start=1):
        documents.append(
            Document(
                page_content=chunk_text,
                metadata={
                    "source": source_filename,
                    "company": company,
                    "chunk_id": index,
                    "total_chunks": len(chunks),
                },
            )
        )
    return documents
