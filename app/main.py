import asyncio
import os

import apis
import logger
import notifier
import state
import tz

MORNING_ORIGIN      = os.getenv("MORNING_ORIGIN",      "Montréal, QC")
MORNING_DESTINATION = os.getenv("MORNING_DESTINATION", "Québec City, QC")
EVENING_ORIGIN      = os.getenv("EVENING_ORIGIN",      MORNING_DESTINATION)
EVENING_DESTINATION = os.getenv("EVENING_DESTINATION", MORNING_ORIGIN)

ACTIVE_HOURS_MORNING_START = int(os.getenv("ACTIVE_HOURS_MORNING_START", "5"))
ACTIVE_HOURS_MORNING_END   = int(os.getenv("ACTIVE_HOURS_MORNING_END",   "20"))
ACTIVE_HOURS_EVENING_START = int(os.getenv("ACTIVE_HOURS_EVENING_START", "5"))
ACTIVE_HOURS_EVENING_END   = int(os.getenv("ACTIVE_HOURS_EVENING_END",   "20"))

POLL_INTERVAL_MINUTES  = int(os.getenv("POLL_INTERVAL_MINUTES",   "10"))
THRESHOLD_MORNING      = float(os.getenv("THRESHOLD_MORNING_MINUTES", "90"))
THRESHOLD_EVENING      = float(os.getenv("THRESHOLD_EVENING_MINUTES", "90"))


def _active(start: int, end: int) -> bool:
    return start <= tz.now().hour < end


def _classify(average: float | None, threshold: float) -> str:
    if average is None:
        return state.ABOVE
    return state.BELOW if average <= threshold else state.ABOVE


async def poll(do_morning: bool, do_evening: bool) -> None:
    print(f"[{tz.now().strftime('%H:%M:%S')}] Polling... (morning={'✓' if do_morning else '✗'} evening={'✓' if do_evening else '✗'})")
    data = await apis.fetch_both_trips(do_morning=do_morning, do_evening=do_evening)

    current  = state.load()
    new_morning = current.get("morning", state.UNKNOWN)
    new_evening = current.get("evening", state.UNKNOWN)
    initial_morning = current.get("morning", state.UNKNOWN) == state.UNKNOWN
    initial_evening = current.get("evening", state.UNKNOWN) == state.UNKNOWN

    if do_morning:
        result = data["morning"]
        new_morning = _classify(result["average"], THRESHOLD_MORNING)
        logger.log_result("MORNING", result, THRESHOLD_MORNING, new_morning)
        if new_morning != current.get("morning", state.UNKNOWN):
            label = "État initial" if initial_morning else f"{current['morning']} → {new_morning}"
            print(f"  MORNING {label}")
            notifier.send("MORNING", result, THRESHOLD_MORNING, new_morning, MORNING_ORIGIN, MORNING_DESTINATION, initial=initial_morning)
        avg = result["average"]
        orig = MORNING_ORIGIN.split(',')[0]
        dest = MORNING_DESTINATION.split(',')[0]
        print(f"  → {orig}→{dest}: {avg:.1f}min ({new_morning})" if avg else f"  → {orig}→{dest}: No data")

    if do_evening:
        result = data["evening"]
        new_evening = _classify(result["average"], THRESHOLD_EVENING)
        logger.log_result("EVENING", result, THRESHOLD_EVENING, new_evening)
        if new_evening != current.get("evening", state.UNKNOWN):
            label = "État initial" if initial_evening else f"{current['evening']} → {new_evening}"
            print(f"  EVENING {label}")
            notifier.send("EVENING", result, THRESHOLD_EVENING, new_evening, EVENING_ORIGIN, EVENING_DESTINATION, initial=initial_evening)
        avg = result["average"]
        orig = EVENING_ORIGIN.split(',')[0]
        dest = EVENING_DESTINATION.split(',')[0]
        print(f"  → {orig}→{dest}: {avg:.1f}min ({new_evening})" if avg else f"  → {orig}→{dest}: No data")

    state.save(new_morning, new_evening)


async def main() -> None:
    print(f"Travel monitor started")
    print(f"  Matin  : {MORNING_ORIGIN} → {MORNING_DESTINATION} ({ACTIVE_HOURS_MORNING_START}h–{ACTIVE_HOURS_MORNING_END}h, seuil {THRESHOLD_MORNING}min)")
    print(f"  Soir   : {EVENING_ORIGIN} → {EVENING_DESTINATION} ({ACTIVE_HOURS_EVENING_START}h–{ACTIVE_HOURS_EVENING_END}h, seuil {THRESHOLD_EVENING}min)")
    print(f"  Poll   : {POLL_INTERVAL_MINUTES}min")

    while True:
        do_morning = _active(ACTIVE_HOURS_MORNING_START, ACTIVE_HOURS_MORNING_END)
        do_evening = _active(ACTIVE_HOURS_EVENING_START, ACTIVE_HOURS_EVENING_END)

        if do_morning or do_evening:
            try:
                await poll(do_morning, do_evening)
            except Exception as e:
                print(f"[ERROR] {e}")
        else:
            print(f"[{tz.now().strftime('%H:%M:%S')}] Hors plage horaire, pause...")

        await asyncio.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(main())
