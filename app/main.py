import asyncio
import os

import apis
import logger
import notifier
import state
import tz

ORIGIN = os.getenv("ORIGIN", "Montréal, QC")
DESTINATION = os.getenv("DESTINATION", "Québec City, QC")
ACTIVE_HOURS_START = int(os.getenv("ACTIVE_HOURS_START", "5"))
ACTIVE_HOURS_END = int(os.getenv("ACTIVE_HOURS_END", "20"))
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "10"))
THRESHOLD_OUTBOUND = float(os.getenv("THRESHOLD_OUTBOUND_MINUTES", "90"))
THRESHOLD_INBOUND = float(os.getenv("THRESHOLD_INBOUND_MINUTES", "90"))


def _is_active_hours() -> bool:
    hour = tz.now().hour
    return ACTIVE_HOURS_START <= hour < ACTIVE_HOURS_END


def _classify(average: float | None, threshold: float) -> str:
    if average is None:
        return state.ABOVE
    return state.BELOW if average <= threshold else state.ABOVE


async def poll() -> None:
    print(f"[{tz.now().strftime('%H:%M:%S')}] Polling...")
    data = await apis.fetch_both_directions()

    current = state.load()

    outbound_result = data["outbound"]
    inbound_result = data["inbound"]

    new_outbound = _classify(outbound_result["average"], THRESHOLD_OUTBOUND)
    new_inbound = _classify(inbound_result["average"], THRESHOLD_INBOUND)

    logger.log_result("OUTBOUND", outbound_result, THRESHOLD_OUTBOUND, new_outbound)
    logger.log_result("INBOUND", inbound_result, THRESHOLD_INBOUND, new_inbound)

    initial_run = current["outbound"] == state.UNKNOWN

    if new_outbound != current["outbound"]:
        label = "État initial" if initial_run else f"{current['outbound']} → {new_outbound}"
        print(f"  OUTBOUND {label}")
        notifier.send("OUTBOUND", outbound_result, THRESHOLD_OUTBOUND, new_outbound, ORIGIN, DESTINATION, initial=initial_run)

    if new_inbound != current["inbound"]:
        label = "État initial" if initial_run else f"{current['inbound']} → {new_inbound}"
        print(f"  INBOUND {label}")
        notifier.send("INBOUND", inbound_result, THRESHOLD_INBOUND, new_inbound, DESTINATION, ORIGIN, initial=initial_run)

    state.save(new_outbound, new_inbound)

    avg_out = outbound_result["average"]
    avg_in = inbound_result["average"]
    orig = ORIGIN.split(',')[0]
    dest = DESTINATION.split(',')[0]
    print(f"  → {orig}→{dest}: {avg_out:.1f}min ({new_outbound}) | {dest}→{orig}: {avg_in:.1f}min ({new_inbound})" if avg_out and avg_in else "  → No data")


async def main() -> None:
    print(f"Travel monitor started — {ORIGIN} ↔ {DESTINATION}")
    print(f"Active hours: {ACTIVE_HOURS_START}h–{ACTIVE_HOURS_END}h | Poll: {POLL_INTERVAL_MINUTES}min")
    print(f"Thresholds: outbound={THRESHOLD_OUTBOUND}min, inbound={THRESHOLD_INBOUND}min")

    while True:
        if _is_active_hours():
            try:
                await poll()
            except Exception as e:
                print(f"[ERROR] {e}")
        else:
            print(f"[{tz.now().strftime('%H:%M:%S')}] Outside active hours, sleeping...")

        await asyncio.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    asyncio.run(main())
