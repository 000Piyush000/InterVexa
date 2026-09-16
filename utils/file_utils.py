"""
Upload validation and safe file persistence helpers.
"""

import os
import re
import time

from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, DATA_DIR


class UploadError(Exception):
    """Raised when an uploaded file or target company is invalid."""


def allowed_file(filename):
    if not filename or "." not in filename:
        return False
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def sanitize_company_name(raw_name):
    """Turn user-supplied company text into a safe folder name.

    Keeps letters, numbers, spaces, hyphens and underscores; collapses
    whitespace; title-cases the result for consistent display.
    """
    if not raw_name or not raw_name.strip():
        raise UploadError("Company name cannot be empty.")

    cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", raw_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise UploadError("Company name must contain at least one letter or number.")
    if len(cleaned) > 60:
        cleaned = cleaned[:60].strip()
    return cleaned.title()


def validate_upload(file_storage):
    """Validate an incoming Flask/Werkzeug FileStorage object."""
    if file_storage is None or file_storage.filename == "":
        raise UploadError("No file was selected.")
    if not allowed_file(file_storage.filename):
        raise UploadError("Only PDF and TXT files are supported.")


def save_uploaded_file(file_storage, company):
    """Persist an uploaded file under data/<company>/, avoiding name collisions.

    Returns the absolute path the file was saved to.
    """
    validate_upload(file_storage)

    company_dir = os.path.join(DATA_DIR, company)
    os.makedirs(company_dir, exist_ok=True)

    filename = secure_filename(file_storage.filename)
    if not filename:
        raise UploadError("Uploaded filename is invalid.")

    base, extension = os.path.splitext(filename)
    candidate = filename
    destination = os.path.join(company_dir, candidate)

    if os.path.exists(destination):
        timestamp = int(time.time())
        candidate = f"{base}_{timestamp}{extension}"
        destination = os.path.join(company_dir, candidate)

    file_storage.save(destination)

    if os.path.getsize(destination) == 0:
        os.remove(destination)
        raise UploadError(f"'{filename}' is empty.")

    return destination
