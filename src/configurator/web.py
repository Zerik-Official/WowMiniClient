"""Temporary local Flask server that serves the web setup page."""

# Standard library
from __future__ import annotations
import secrets
import threading
import webbrowser
from pathlib import Path
from typing import Any

# Third-party
from flask import Flask, Response, abort, jsonify, render_template, request
from werkzeug.serving import BaseWSGIServer, make_server

# Project imports
from configurator.schema import (
    CHAT_TYPES,
    DIRECTIONS,
    GM_MODES,
    GUILD_EVENTS,
    LOCALES,
    PLATFORMS,
    RAID_ICON_SLOTS,
    SUPPORTED_VERSIONS,
    to_form,
)
from configurator.store import ConfigValidationError, load_raw, save
from utils.logger import Tags, log

HOST: str = "127.0.0.1"
KEY_HEADER: str = "X-Setup-Key"


def create_app(config_path: Path, key: str, finished: threading.Event) -> Flask:
    """
    Build the Flask application for the web setup page.

    Args:
        config_path: Destination of wowchat.toml.
        key: Random value the page must send back on every API call.
        finished: Event set when the user closes the setup.

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__)

    def check_key() -> None:
        """Reject API calls that do not come from the served page."""
        if not secrets.compare_digest(request.headers.get(KEY_HEADER, ""), key):
            abort(403)

    @app.get("/")
    def index() -> str:
        """Render the setup page with the current configuration."""
        if not secrets.compare_digest(request.args.get("key", ""), key):
            abort(403)
        return render_template(
            "index.html",
            key=key,
            config=to_form(load_raw(config_path)),
            config_path=str(config_path),
            exists=config_path.exists(),
            versions=SUPPORTED_VERSIONS,
            locales=LOCALES,
            platforms=PLATFORMS,
            chat_types=CHAT_TYPES,
            directions=DIRECTIONS,
            guild_events=GUILD_EVENTS,
            gm_modes=GM_MODES,
            raid_slots=RAID_ICON_SLOTS,
        )

    @app.post("/api/config")
    def save_config() -> tuple[Response, int]:
        """Validate and write the configuration sent by the page."""
        check_key()
        payload: Any = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(ok=False, error="The request body must be a JSON object."), 400
        try:
            path = save(payload, config_path)
        except ConfigValidationError as exc:
            return jsonify(ok=False, error=str(exc)), 422
        log("SUCCESS", Tags.CONFIG, f"Configuration saved to {path}")
        return jsonify(ok=True, path=str(path)), 200

    @app.post("/api/close")
    def close() -> tuple[Response, int]:
        """Stop the temporary server."""
        check_key()
        finished.set()
        return jsonify(ok=True), 200

    return app


def run(config_path: Path, open_browser: bool = True) -> None:
    """
    Serve the setup page on a free local port until the user closes it.

    Args:
        config_path: Destination of wowchat.toml.
        open_browser: Open the page in the default browser automatically.
    """
    key = secrets.token_urlsafe(24)
    finished = threading.Event()
    server: BaseWSGIServer = make_server(HOST, 0, create_app(config_path, key, finished))
    url = f"http://{HOST}:{server.server_port}/?key={key}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log("INFO", Tags.CONFIG, f"Setup page running at {url}")
    log("INFO", Tags.CONFIG, "Press Ctrl+C to stop it without saving.")
    if open_browser:
        webbrowser.open(url)

    try:
        while not finished.wait(0.5):
            pass
    except KeyboardInterrupt:
        log("WARNING", Tags.CONFIG, "Setup page stopped.")
    finally:
        server.shutdown()
        thread.join(timeout=2)
