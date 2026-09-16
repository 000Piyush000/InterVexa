"""
Central configuration for the AI Interview Copilot.

Every path, model name, and tunable constant used across the application is
defined here so that no other module hard-codes a value. Import from this
module instead of re-deriving paths elsewhere.
"""

import os

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
EMBEDDINGS_DIR = os.path.join(BASE_DIR, "embeddings")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
FAQS_FILE = os.path.join(BASE_DIR, "data", "faqs.json")
COMPANY_META_FILE = os.path.join(BASE_DIR, "data", "company_meta.json")

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
SITE_NAME = "Intervexa"
SITE_TAGLINE = "AI Interview Copilot"

# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
# Companies that always show up on the landing page / selectors. Users may
# also type a custom company name during upload, which dynamically creates a
# new folder under DATA_DIR and a new FAISS index under EMBEDDINGS_DIR.
DEFAULT_COMPANIES = ["Amazon", "Google", "Microsoft", "Adobe", "Meta"]

COMPANY_LOGOS = {
    "Amazon": "bi-cart-fill",
    "Google": "bi-google",
    "Microsoft": "bi-microsoft",
    "Adobe": "bi-badge-ad-fill",
    "Meta": "bi-meta",
}

# ---------------------------------------------------------------------------
# File upload settings
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {"pdf", "txt"}
MAX_CONTENT_LENGTH_MB = 20
MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
TOP_K = 5
# A retrieved chunk with a similarity score below this threshold is treated
# as "not relevant enough" when computing the confidence indicator.
MIN_RELEVANCE_SCORE = 0.20

# ---------------------------------------------------------------------------
# Ollama / LLM
# ---------------------------------------------------------------------------
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
LLM_TEMPERATURE = 0.2
LLM_REQUEST_TIMEOUT = 120  # seconds

# ---------------------------------------------------------------------------
# Interview modes
# ---------------------------------------------------------------------------
INTERVIEW_MODES = {
    "general": {
        "label": "General",
        "icon": "bi-chat-dots",
        "keywords": [],
        "description": "Answers drawn from the full interview experience.",
    },
    "dsa": {
        "label": "DSA Mode",
        "icon": "bi-code-slash",
        "keywords": [
            "array", "string", "linked list", "tree", "graph", "dynamic programming",
            "recursion", "sorting", "searching", "leetcode", "complexity", "algorithm",
            "data structure", "binary search", "hashmap", "hash map", "stack", "queue",
            "heap", "big o", "two pointer", "sliding window", "backtracking",
        ],
        "description": "Prioritizes coding / data-structures & algorithms questions.",
    },
    "system_design": {
        "label": "System Design Mode",
        "icon": "bi-diagram-3",
        "keywords": [
            "system design", "architecture", "scalability", "load balancer", "database",
            "sharding", "cache", "caching", "microservice", "api gateway", "queue",
            "throughput", "latency", "distributed", "availability", "consistency",
            "replication", "partitioning", "cdn", "design a", "high level design",
            "low level design",
        ],
        "description": "Prioritizes architecture and system design discussions.",
    },
    "sql": {
        "label": "SQL Mode",
        "icon": "bi-database",
        "keywords": [
            "sql", "query", "join", "select", "group by", "index", "database", "schema",
            "normalization", "primary key", "foreign key", "subquery", "aggregate",
            "having", "window function", "stored procedure", "transaction", "table",
        ],
        "description": "Prioritizes SQL and database questions.",
    },
    "hr": {
        "label": "HR Mode",
        "icon": "bi-people",
        "keywords": [
            "tell me about yourself", "strength", "weakness", "conflict", "teamwork",
            "leadership", "why do you want", "behavioral", "salary", "expectation",
            "manager", "deadline", "failure", "challenge", "motivate", "culture fit",
            "hr round", "situation", "star method",
        ],
        "description": "Prioritizes behavioral / HR round questions.",
    },
}

# ---------------------------------------------------------------------------
# Suggested questions shown in the chat UI, tailored per interview mode.
# {company} is substituted with the currently selected company at render time.
# ---------------------------------------------------------------------------
SUGGESTED_QUESTIONS = {
    "general": [
        "Summarize the interview experiences for {company}.",
        "What topics appear most frequently in {company} interviews?",
        "How many interview rounds does {company} typically have?",
        "What was the overall interview difficulty at {company}?",
    ],
    "dsa": [
        "What DSA questions were asked at {company}?",
        "Were any tree or graph problems asked at {company}?",
        "What is the difficulty level of {company}'s coding round?",
        "Were any dynamic programming questions asked at {company}?",
    ],
    "system_design": [
        "What system design questions were asked at {company}?",
        "Did {company} ask about designing a scalable system?",
        "What architecture topics came up in {company} interviews?",
        "Were caching or database design discussed at {company}?",
    ],
    "sql": [
        "Give me SQL questions asked by {company}.",
        "Were any SQL join questions asked at {company}?",
        "Did {company} ask about database schema design?",
        "What SQL query problems appeared in {company} interviews?",
    ],
    "hr": [
        "What HR questions are common at {company}?",
        "Were any behavioral questions asked at {company}?",
        "How does {company} evaluate teamwork and leadership?",
        "What questions about conflict resolution did {company} ask?",
    ],
}

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"
HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_PORT", "5000"))

# Ensure required directories exist at import time so every module can rely
# on them being present without repeating boilerplate.
for _dir in (DATA_DIR, EMBEDDINGS_DIR, UPLOAD_DIR):
    os.makedirs(_dir, exist_ok=True)

for _company in DEFAULT_COMPANIES:
    os.makedirs(os.path.join(DATA_DIR, _company), exist_ok=True)
