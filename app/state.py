import json
import os
import tz

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")

ABOVE = "ABOVE_THRESHOLD"
BELOW = "BELOW_THRESHOLD"
UNKNOWN = "UNKNOWN"

_DEFAULT = {
    "outbound": UNKNOWN,
    "inbound": UNKNOWN,
    "last_updated": None,
}


def load() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT)


def save(outbound: str, inbound: str) -> None:
    state = {
        "outbound": outbound,
        "inbound": inbound,
        "last_updated": tz.now().isoformat(timespec="seconds"),
    }
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
