import os
import requests
import tz

NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_BASE = "https://ntfy.sh"


def _fmt_duration(minutes: float | None) -> str:
    if minutes is None:
        return "N/A (erreur)"
    h = int(minutes) // 60
    m = int(minutes) % 60
    if h:
        return f"{h}h{m:02d}"
    return f"{m}min"


def _build_message(direction_label: str, result: dict, threshold: float, new_state: str, origin: str, destination: str, initial: bool = False) -> tuple[str, str]:
    orig_short = origin.split(',')[0]
    dest_short = destination.split(',')[0]
    route = f"{orig_short} → {dest_short}"
    if initial:
        emoji = "🔵"
        label = "sous le seuil" if new_state == "BELOW_THRESHOLD" else "au-dessus du seuil"
        title = f"{emoji} {route} : état initial ({label})"
    elif new_state == "BELOW_THRESHOLD":
        emoji = "🟢"
        title = f"{emoji} {route} : sous le seuil!"
    else:
        emoji = "🔴"
        title = f"{emoji} {route} : au-dessus du seuil"

    google = _fmt_duration(result["google"])
    mapbox = _fmt_duration(result["mapbox"])
    here = _fmt_duration(result["here"])
    ors = _fmt_duration(result["ors"])
    average = _fmt_duration(result["average"])
    threshold_str = _fmt_duration(threshold)
    now = tz.now().strftime("%Y-%m-%d %H:%M")

    body = (
        f"Google Maps : {google}\n"
        f"Mapbox      : {mapbox}\n"
        f"HERE        : {here}\n"
        f"ORS         : {ors}\n"
        f"\n"
        f"Moyenne : {average} | Seuil : {threshold_str}\n"
        f"📍 {origin} → {destination}\n"
        f"🕐 {now}"
    )
    return title, body


def send(direction: str, result: dict, threshold: float, new_state: str, origin: str, destination: str, initial: bool = False) -> None:
    if not NTFY_TOPIC:
        print(f"  [notifier] NTFY_TOPIC non configuré, notification ignorée")
        return

    title, body = _build_message(direction, result, threshold, new_state, origin, destination, initial)

    try:
        requests.post(
            f"{NTFY_BASE}/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers={
                "Title": title.encode("utf-8"),
                "Priority": "default",
                "Tags": "car,traffic",
            },
            timeout=10,
        )
        print(f"  [notifier] Envoyé: {title}")
    except Exception as e:
        print(f"  [notifier] Erreur ntfy: {e}")
