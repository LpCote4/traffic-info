import csv
import os
import tz

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "travel_log.csv")

_HEADERS = [
    "timestamp", "direction",
    "google_min", "mapbox_min", "here_min", "ors_min",
    "average_min", "threshold_min", "state",
]


def _fmt(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def log_result(direction: str, result: dict, threshold: float, state: str) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    write_header = not os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(_HEADERS)
        writer.writerow([
            tz.now().strftime("%Y-%m-%d %H:%M"),
            direction,
            _fmt(result["google"]),
            _fmt(result["mapbox"]),
            _fmt(result["here"]),
            _fmt(result["ors"]),
            _fmt(result["average"]),
            f"{threshold:.0f}",
            state,
        ])
