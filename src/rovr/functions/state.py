import json
import os
from os import path
from typing import Any, Dict
from contextlib import suppress

from rovr.variables.maps import VAR_TO_DIR


def _ui_state_filename() -> str:
    """Return the current UI state filename computed from VAR_TO_DIR.

    This is computed on demand (instead of at import time) so tests and any
    runtime modifications to VAR_TO_DIR are respected.
    """
    return path.join(VAR_TO_DIR["CONFIG"], "ui_state.json")
_DEFAULT_STATE: Dict[str, Any] = {
    "version": 1,
    # These keys are intentionally optional; callers should merge with
    # runtime defaults (eg. values from `config`) when applying.
    "show_hidden_files": None,
    "footer_visible": None,
    "pinned_sidebar_visible": None,
    "preview_visible": None,
    "compact_mode": None,
}


def _ensure_config_dir() -> None:
    cfg_dir = VAR_TO_DIR["CONFIG"]
    if not path.exists(cfg_dir):
        os.makedirs(cfg_dir, exist_ok=True)


def load_ui_state() -> Dict[str, Any]:
    """Load persisted UI state from the user's config directory.

    Returns an empty dict on any error (missing file, parse error, etc.) so
    callers can fall back to sensible defaults.
    """
    ui_file = _ui_state_filename()
    # If the config directory / file doesn't exist, just return defaults.
    if not path.exists(ui_file):
        return {}
    try:
        with open(ui_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            # simple versioning: if missing, assume defaults
            if data.get("version") != _DEFAULT_STATE["version"]:
                # Future: add migrations here
                # For now, be tolerant and return what we can
                return {**_DEFAULT_STATE, **data}
            return data
    except (OSError, json.JSONDecodeError):
        # Corrupted or unreadable file — fallback to defaults
        return {}


def save_ui_state(state: Dict[str, Any]) -> None:
    """Persist UI state to disk atomically.

    The function will create the config directory if necessary and will
    overwrite the previous state. Errors are swallowed because state save
    should never block quitting the app.
    """
    _ensure_config_dir()
    state_to_write = {**_DEFAULT_STATE, **(state or {})}
    # ensure version present
    state_to_write["version"] = _DEFAULT_STATE["version"]
    ui_file = _ui_state_filename()
    tmp = ui_file + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state_to_write, f, indent=2)
        os.replace(tmp, ui_file)
    except OSError:
        # best-effort; don't raise
        with suppress(OSError):
            pass


def build_state_from_app(app, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Construct a state dict from the running application.

    `config` may be provided; otherwise only values discoverable from the
    UI are returned. Missing keys are set to None so callers can merge with
    defaults.
    """
    state: Dict[str, Any] = {}
    # show_hidden_files comes from config prefer that if provided
    if config is not None and "settings" in config:
        state["show_hidden_files"] = bool(
            config["settings"].get("show_hidden_files", False)
        )

    try:
        footer = app.query_one("#footer")
        state["footer_visible"] = bool(getattr(footer, "display", True))
    except Exception:
        state["footer_visible"] = None

    try:
        pinned = app.query_one("#pinned_sidebar_container")
        state["pinned_sidebar_visible"] = bool(getattr(pinned, "display", True))
    except Exception:
        state["pinned_sidebar_visible"] = None

    try:
        preview = app.query_one("#preview_sidebar")
        state["preview_visible"] = bool(getattr(preview, "display", True))
    except Exception:
        state["preview_visible"] = None

    # compact mode tracked via app.classes
    try:
        state["compact_mode"] = "compact" in getattr(app, "classes", [])
    except Exception:
        state["compact_mode"] = None

    state["version"] = _DEFAULT_STATE["version"]
    return state
