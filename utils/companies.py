"""
Explicit company creation and per-company display metadata (icon).

`config.DEFAULT_COMPANIES` / `config.COMPANY_LOGOS` cover the handful of
built-in companies. Anything a user adds through the "Add Company" flow (or
by typing a custom name during upload) is a plain folder under `data/` —
this module additionally lets those custom companies remember which icon
was picked for them, stored in `config.COMPANY_META_FILE`.
"""

import json
import os
import threading

import config

_lock = threading.Lock()


def _read_meta():
    if not os.path.isfile(config.COMPANY_META_FILE):
        return {}
    try:
        with open(config.COMPANY_META_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_meta(meta):
    os.makedirs(os.path.dirname(config.COMPANY_META_FILE), exist_ok=True)
    with open(config.COMPANY_META_FILE, "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)


def get_company_icon(name):
    """Return the saved icon class for a custom company, or None."""
    return _read_meta().get(name, {}).get("icon")


def create_company(name, icon=None):
    """Create the data/<name> folder so the company shows up everywhere
    the built-in companies do, optionally remembering a display icon.

    Returns True if the company already existed, False if newly created.
    """
    company_dir = os.path.join(config.DATA_DIR, name)
    with _lock:
        already_existed = os.path.isdir(company_dir)
        os.makedirs(company_dir, exist_ok=True)
        if icon:
            meta = _read_meta()
            meta[name] = {"icon": icon}
            _write_meta(meta)
    return already_existed
