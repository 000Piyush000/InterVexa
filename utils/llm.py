"""
Thin wrapper around the local Ollama server for answer generation.

All Ollama-specific error handling lives here so the rest of the app only
ever deals with the small set of exceptions defined below.
"""

import ollama

from config import LLM_REQUEST_TIMEOUT, LLM_TEMPERATURE, OLLAMA_HOST, OLLAMA_MODEL


class OllamaUnavailableError(Exception):
    """Raised when the local Ollama server cannot be reached at all."""


class OllamaModelMissingError(Exception):
    """Raised when Ollama is running but the configured model is not pulled."""


class OllamaGenerationError(Exception):
    """Raised when Ollama is reachable but generation fails for another reason."""


_client = ollama.Client(host=OLLAMA_HOST, timeout=LLM_REQUEST_TIMEOUT)


def _is_connection_error(exc):
    message = str(exc).lower()
    connection_hints = ("connection", "refused", "failed to establish", "timed out", "timeout")
    return any(hint in message for hint in connection_hints)


def _is_model_missing_error(exc):
    message = str(exc).lower()
    return "not found" in message or "no such model" in message or "pull" in message


def check_ollama_status():
    """Return a dict describing whether Ollama is reachable and the model is available.

    {"available": bool, "model_available": bool, "error": str | None}
    """
    try:
        response = _client.list()
    except Exception as exc:  # noqa: BLE001 - any connection failure lands here
        return {"available": False, "model_available": False, "error": str(exc)}

    models = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
    model_names = []
    for model in models:
        name = model.get("name") if isinstance(model, dict) else getattr(model, "model", None)
        if name:
            model_names.append(name)

    model_available = any(
        name == OLLAMA_MODEL or name.startswith(f"{OLLAMA_MODEL}:") for name in model_names
    )
    return {"available": True, "model_available": model_available, "error": None}


def generate_answer(messages):
    """Send chat messages to the local Llama 3 model and return the answer text.

    Raises:
        OllamaUnavailableError: the Ollama server is not running / not reachable.
        OllamaModelMissingError: Ollama is running but the model isn't pulled.
        OllamaGenerationError: any other failure during generation.
    """
    try:
        response = _client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            options={"temperature": LLM_TEMPERATURE},
            stream=False,
        )
    except Exception as exc:  # noqa: BLE001 - ollama raises several distinct error types
        if _is_model_missing_error(exc):
            raise OllamaModelMissingError(
                f"The model '{OLLAMA_MODEL}' is not available in Ollama. "
                f"Run `ollama pull {OLLAMA_MODEL}` and try again."
            ) from exc
        if _is_connection_error(exc):
            raise OllamaUnavailableError(
                "Could not reach the local Ollama server. Make sure Ollama is installed "
                f"and running (`ollama serve`) at {OLLAMA_HOST}."
            ) from exc
        raise OllamaGenerationError(f"Answer generation failed: {exc}") from exc

    message = response.get("message") if isinstance(response, dict) else getattr(response, "message", None)
    content = None
    if isinstance(message, dict):
        content = message.get("content")
    elif message is not None:
        content = getattr(message, "content", None)

    if not content or not content.strip():
        raise OllamaGenerationError("Ollama returned an empty response.")

    return content.strip()
