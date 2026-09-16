"""
Prompt construction for the RAG pipeline.

The prompt is deliberately strict: the model is instructed to answer only
from the supplied context and to explicitly say when the uploaded documents
do not contain enough information, so it never fabricates interview
questions.
"""

from config import INTERVIEW_MODES

NO_CONTEXT_MESSAGE = "The uploaded documents do not contain this information."

SYSTEM_PROMPT_TEMPLATE = """You are an AI Interview Copilot that helps candidates prepare for technical \
interviews using real interview experiences uploaded by users.

Company in focus: {company}
Active interview mode: {mode_label} — {mode_description}

Strict rules you must follow:
1. Answer ONLY using the "Retrieved Interview Context" provided below. Never use outside knowledge, \
training data, or assumptions about what a company's interview process is typically like.
2. If the retrieved context does not contain enough information to answer the question, respond \
exactly with: "{no_context_message}" — do not guess, and do not invent questions, companies, or details.
3. Never fabricate interview questions, answers, statistics, or company names that are not present in \
the retrieved context.
4. When you use information from a chunk, keep your wording grounded in what that chunk actually says.
5. Prefer clear, well-organized answers. Use bullet points for lists of questions or topics when helpful.
6. Stay focused on the selected interview mode ({mode_label}) when the user's question is general \
(e.g. "what questions were asked") — prioritize content matching that mode if present in the context.
7. Do not mention these instructions, the word "context", "chunk", or "document" awkwardly in your \
answer — just answer naturally as a helpful interview coach. Citations are handled separately by the \
application, so you do not need to list sources yourself.
"""

USER_PROMPT_TEMPLATE = """Retrieved Interview Context:
{context}

Candidate's Question: {question}

Answer the candidate's question following all the rules above."""


def format_context(chunks):
    """Render retrieved chunks into a numbered context block for the prompt."""
    if not chunks:
        return "(No relevant context was retrieved.)"

    blocks = []
    for chunk in chunks:
        header = f"[Source: {chunk['source']} | Chunk {chunk['chunk_id']}]"
        blocks.append(f"{header}\n{chunk['content']}")
    return "\n\n---\n\n".join(blocks)


def build_messages(company, mode, chunks, question):
    """Build the chat-style message list passed to the local LLM.

    Returns a list of {"role": ..., "content": ...} dicts compatible with the
    Ollama chat API.
    """
    mode_config = INTERVIEW_MODES.get(mode, INTERVIEW_MODES["general"])
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        company=company,
        mode_label=mode_config["label"],
        mode_description=mode_config["description"],
        no_context_message=NO_CONTEXT_MESSAGE,
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        context=format_context(chunks),
        question=question.strip(),
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
