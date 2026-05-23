"""
Lightweight web dashboard — reads state.json and travel_log.csv,
and allows editing settings.env at runtime.
Run alongside main.py inside the same container.
"""

import csv
import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR   = Path(__file__).resolve().parent
ROOT_DIR   = BASE_DIR.parent.parent          # repo root
DATA_DIR   = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
ENV_FILE   = CONFIG_DIR / "settings.env"
STATE_FILE = DATA_DIR  / "state.json"
LOG_FILE   = DATA_DIR  / "travel_log.csv"

app = FastAPI(title="Traffic Monitor")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── helpers ──────────────────────────────────────────────────────────────────

def _read_env() -> dict[str, str]:
    """Parse settings.env into a dict, ignoring blank lines and comments."""
    result: dict[str, str] = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env(data: dict[str, str]) -> None:
    """Rewrite settings.env preserving comments and key order."""
    if not ENV_FILE.exists():
        raise FileNotFoundError("settings.env not found")

    original = ENV_FILE.read_text().splitlines()
    written_keys: set[str] = set()
    new_lines: list[str] = []

    for line in original:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in data:
                new_lines.append(f"{k}={data[k]}")
                written_keys.add(k)
                continue
        new_lines.append(line)

    # Append any new keys not present in the original file
    for k, v in data.items():
        if k not in written_keys:
            new_lines.append(f"{k}={v}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")


def _read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"morning": "UNKNOWN", "evening": "UNKNOWN", "last_updated": None}


def _read_logs(limit: int = 200) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    rows: list[dict] = []
    with open(LOG_FILE, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows[-limit:][::-1]   # most recent first


# ── routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/state")
async def api_state():
    return JSONResponse(_read_state())


@app.get("/api/logs")
async def api_logs(limit: int = 200):
    return JSONResponse(_read_logs(limit))


@app.get("/api/settings")
async def api_settings():
    return JSONResponse(_read_env())


@app.post("/api/settings")
async def api_settings_update(request: Request):
    try:
        data: dict[str, str] = await request.json()
        # Sanitize: only allow alphanumeric keys + underscore
        sanitized = {
            k: str(v)
            for k, v in data.items()
            if re.fullmatch(r"[A-Z0-9_]+", k)
        }
        _write_env(sanitized)
        return JSONResponse({"ok": True})
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
