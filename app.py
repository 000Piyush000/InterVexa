"""
AI Interview Copilot — Flask application entry point.

This module only wires together routes; all business logic (document
processing, embeddings, retrieval, prompting and LLM calls) lives in the
`utils/` package so this file stays small and easy to read.
"""

import io
import os
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file, session

import config
from utils.embeddings import EmbeddingModelError
from utils.chat_export import build_chat_pdf
from utils.companies import create_company, get_company_icon
from utils.faqs import FaqError, add_faq, get_faqs
from utils.file_utils import UploadError, sanitize_company_name, save_uploaded_file
from utils.llm import (
    OllamaGenerationError,
    OllamaModelMissingError,
    OllamaUnavailableError,
    check_ollama_status,
    generate_answer,
)
from utils.pdf_loader import DocumentLoadError
from utils.prompt import NO_CONTEXT_MESSAGE, build_messages
from utils.retriever import compute_confidence, retrieve
from utils.topics import get_frequent_topics
from utils.vector_store import VectorStoreError, build_or_update_index, get_index_stats

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _discover_companies():
    """Default companies plus any custom company folders the user created."""
    names = list(config.DEFAULT_COMPANIES)
    if os.path.isdir(config.DATA_DIR):
        for entry in sorted(os.listdir(config.DATA_DIR)):
            full_path = os.path.join(config.DATA_DIR, entry)
            if os.path.isdir(full_path) and entry not in names and not entry.startswith("."):
                names.append(entry)
    return names


def _company_summaries():
    summaries = []
    for name in _discover_companies():
        stats = get_index_stats(name)
        summaries.append(
            {
                "name": name,
                "has_index": stats["has_index"],
                "num_files": stats["num_files"],
                "num_chunks": stats["num_chunks"],
                "is_default": name in config.DEFAULT_COMPANIES,
                "icon": config.COMPANY_LOGOS.get(name) or get_company_icon(name) or "bi-building",
            }
        )
    return summaries


def _error_response(message, status=400, error_type=None):
    payload = {"success": False, "error": message}
    if error_type:
        payload["error_type"] = error_type
    return jsonify(payload), status


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template(
        "index.html",
        companies=_company_summaries(),
        ollama_status=check_ollama_status(),
        default_companies=config.DEFAULT_COMPANIES,
    )


@app.route("/upload", methods=["GET"])
def upload_page():
    return render_template(
        "upload.html",
        companies=_company_summaries(),
        default_companies=config.DEFAULT_COMPANIES,
        max_size_mb=config.MAX_CONTENT_LENGTH_MB,
    )


@app.route("/chat")
def chat_page():
    return render_template(
        "chat.html",
        companies=_company_summaries(),
        selected_company=request.args.get("company", ""),
        selected_mode=request.args.get("mode", "general"),
        modes=config.INTERVIEW_MODES,
        ollama_status=check_ollama_status(),
        history=session.get("chat_history", []),
    )


# ---------------------------------------------------------------------------
# Upload + processing routes
# ---------------------------------------------------------------------------
@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        company_choice = (request.form.get("company") or "").strip()
        custom_company = (request.form.get("custom_company") or "").strip()

        if not company_choice or company_choice.lower() == "custom":
            if not custom_company:
                raise UploadError("Please provide a custom company name.")
            company = sanitize_company_name(custom_company)
        else:
            company = sanitize_company_name(company_choice)

        files = request.files.getlist("files")
        if not files or all(f.filename == "" for f in files):
            raise UploadError("No file was selected.")

        saved_files = []
        upload_errors = []
        for file_storage in files:
            if file_storage.filename == "":
                continue
            try:
                saved_path = save_uploaded_file(file_storage, company)
                saved_files.append(os.path.basename(saved_path))
            except UploadError as exc:
                upload_errors.append({"file": file_storage.filename, "error": str(exc)})

        if not saved_files:
            return jsonify(
                {"success": False, "error": "No valid files were uploaded.", "details": upload_errors}
            ), 400

        stats = build_or_update_index(company)
        return jsonify(
            {
                "success": True,
                "company": company,
                "saved_files": saved_files,
                "upload_errors": upload_errors,
                "processing": stats,
            }
        )

    except UploadError as exc:
        return _error_response(str(exc), 400)
    except (DocumentLoadError, VectorStoreError) as exc:
        return _error_response(str(exc), 422)
    except EmbeddingModelError as exc:
        return _error_response(str(exc), 500, "embedding_failed")
    except Exception:  # noqa: BLE001
        app.logger.exception("Unexpected upload error")
        return _error_response("An unexpected error occurred while processing the upload.", 500)


@app.route("/process", methods=["POST"])
def process_company():
    try:
        payload = request.get_json(silent=True) or request.form
        raw_company = (payload.get("company") or "").strip()
        if not raw_company:
            raise UploadError("Please specify a company to process.")
        company = sanitize_company_name(raw_company)
        force = str(payload.get("force", "false")).lower() in ("1", "true", "yes")

        stats = build_or_update_index(company, force_rebuild=force)
        return jsonify({"success": True, "company": company, "processing": stats})

    except UploadError as exc:
        return _error_response(str(exc), 400)
    except (DocumentLoadError, VectorStoreError) as exc:
        return _error_response(str(exc), 422)
    except EmbeddingModelError as exc:
        return _error_response(str(exc), 500, "embedding_failed")
    except Exception:  # noqa: BLE001
        app.logger.exception("Unexpected processing error")
        return _error_response("An unexpected error occurred while processing documents.", 500)


# ---------------------------------------------------------------------------
# Chat / RAG routes
# ---------------------------------------------------------------------------
@app.route("/api/ask", methods=["POST"])
def ask():
    try:
        payload = request.get_json(silent=True) or {}
        company_raw = (payload.get("company") or "").strip()
        mode = (payload.get("mode") or "general").strip()
        question = (payload.get("question") or "").strip()

        if not company_raw:
            return _error_response("Please select a company first.", 400)
        if not question:
            return _error_response("Please enter a question.", 400)
        if mode not in config.INTERVIEW_MODES:
            mode = "general"

        company = sanitize_company_name(company_raw)

        results = retrieve(company, question, mode=mode, top_k=config.TOP_K)
        confidence = compute_confidence(results)
        relevant_results = [r for r in results if r["similarity"] >= config.MIN_RELEVANCE_SCORE]

        if not relevant_results:
            answer_text = NO_CONTEXT_MESSAGE
            sources = []
        else:
            messages = build_messages(company, mode, relevant_results, question)
            answer_text = generate_answer(messages)
            sources = [
                {"source": r["source"], "chunk_id": r["chunk_id"], "similarity": r["similarity"]}
                for r in relevant_results
            ]

        now = datetime.utcnow().isoformat()
        history = session.get("chat_history", [])
        history.append({"role": "user", "content": question, "company": company, "mode": mode, "timestamp": now})
        history.append(
            {
                "role": "assistant",
                "content": answer_text,
                "sources": sources,
                "confidence": confidence,
                "company": company,
                "mode": mode,
                "timestamp": now,
            }
        )
        session["chat_history"] = history
        session.modified = True

        return jsonify(
            {
                "success": True,
                "answer": answer_text,
                "sources": sources,
                "confidence": confidence,
                "company": company,
                "mode": mode,
            }
        )

    except VectorStoreError as exc:
        return _error_response(str(exc), 404, "no_index")
    except OllamaUnavailableError as exc:
        return _error_response(str(exc), 503, "ollama_unavailable")
    except OllamaModelMissingError as exc:
        return _error_response(str(exc), 503, "ollama_model_missing")
    except OllamaGenerationError as exc:
        return _error_response(str(exc), 502, "generation_failed")
    except EmbeddingModelError as exc:
        return _error_response(str(exc), 500, "embedding_failed")
    except Exception:  # noqa: BLE001
        app.logger.exception("Unexpected error answering question")
        return _error_response("An unexpected error occurred while answering your question.", 500)


@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    session["chat_history"] = []
    session.modified = True
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Supporting API routes
# ---------------------------------------------------------------------------
@app.route("/api/companies")
def api_companies():
    return jsonify({"success": True, "companies": _company_summaries()})


@app.route("/api/companies", methods=["POST"])
def api_add_company():
    try:
        payload = request.get_json(silent=True) or {}
        raw_name = (payload.get("name") or "").strip()
        icon = (payload.get("icon") or "").strip() or None
        if not raw_name:
            raise UploadError("Please provide a company name.")

        name = sanitize_company_name(raw_name)
        create_company(name, icon)
        stats = get_index_stats(name)
        return jsonify(
            {
                "success": True,
                "company": {
                    "name": name,
                    "has_index": stats["has_index"],
                    "num_files": stats["num_files"],
                    "num_chunks": stats["num_chunks"],
                    "is_default": name in config.DEFAULT_COMPANIES,
                    "icon": config.COMPANY_LOGOS.get(name) or get_company_icon(name) or "bi-building",
                },
            }
        )
    except UploadError as exc:
        return _error_response(str(exc), 400)
    except Exception:  # noqa: BLE001
        app.logger.exception("Unexpected error adding company")
        return _error_response("An unexpected error occurred while adding the company.", 500)


# ---------------------------------------------------------------------------
# Help & Support FAQs
# ---------------------------------------------------------------------------
@app.route("/api/faqs")
def api_faqs_list():
    return jsonify({"success": True, "faqs": get_faqs()})


@app.route("/api/faqs", methods=["POST"])
def api_faqs_add():
    try:
        payload = request.get_json(silent=True) or {}
        entry = add_faq(payload.get("question"), payload.get("answer"))
        return jsonify({"success": True, "faq": entry})
    except FaqError as exc:
        return _error_response(str(exc), 400)
    except Exception:  # noqa: BLE001
        app.logger.exception("Unexpected error adding FAQ")
        return _error_response("An unexpected error occurred while adding the FAQ.", 500)


@app.route("/api/suggested_questions")
def api_suggested_questions():
    mode = request.args.get("mode", "general")
    company = request.args.get("company") or "this company"
    if mode not in config.SUGGESTED_QUESTIONS:
        mode = "general"
    questions = [template.format(company=company) for template in config.SUGGESTED_QUESTIONS[mode]]
    return jsonify({"success": True, "questions": questions})


@app.route("/api/topics")
def api_topics():
    company = request.args.get("company") or None
    return jsonify({"success": True, "topics": get_frequent_topics(company=company)})


@app.route("/api/status")
def api_status():
    return jsonify({"success": True, "ollama": check_ollama_status(), "companies": _company_summaries()})


@app.route("/download_chat", methods=["POST"])
def download_chat():
    try:
        payload = request.get_json(silent=True) or {}
        messages = payload.get("messages") or session.get("chat_history", [])
        pdf_bytes = build_chat_pdf(messages, company=payload.get("company"), mode=payload.get("mode"))
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        filename = f"interview_copilot_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)
    except Exception:  # noqa: BLE001
        app.logger.exception("Failed to export chat as PDF")
        return _error_response("Could not generate the PDF export.", 500)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return _error_response("The requested resource was not found.", 404)
    return render_template(
        "index.html",
        companies=_company_summaries(),
        ollama_status=check_ollama_status(),
        default_companies=config.DEFAULT_COMPANIES,
    ), 404


@app.errorhandler(413)
def too_large(_error):
    return _error_response(f"Upload too large. Max size is {config.MAX_CONTENT_LENGTH_MB} MB.", 413)


@app.errorhandler(500)
def server_error(_error):
    return _error_response("Internal server error. Check the server logs for details.", 500)


if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
