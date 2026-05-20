import json
import os
import tz

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "state.json")

ABOVE = "ABOVE_THRESHOLD"
BELOW = "BELOW_THRESHOLD"
UNKNOWN = "UNKNOWN"

_DEFAULT = {
    "morning": UNKNOWN,
    "evening": UNKNOWN,
    "last_updated": None,
}


def load() -> dict:
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        last = data.get("last_updated")
        if last and tz.now().date().isoformat() not in last:
            print(f"  [state] Nouveau jour — reset de l'état")
            return dict(_DEFAULT)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULT)


def save(morning: str, evening: str) -> None:
    state = {
        "morning": morning,
        "evening": evening,
        "last_updated": tz.now().isoformat(timespec="seconds"),
    }
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
