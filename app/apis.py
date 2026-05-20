import asyncio
import os
import aiohttp

MORNING_ORIGIN      = os.getenv("MORNING_ORIGIN",      "Montréal, QC")
MORNING_DESTINATION = os.getenv("MORNING_DESTINATION", "Québec City, QC")
EVENING_ORIGIN      = os.getenv("EVENING_ORIGIN",      MORNING_DESTINATION)
EVENING_DESTINATION = os.getenv("EVENING_DESTINATION", MORNING_ORIGIN)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MAPBOX_TOKEN   = os.getenv("MAPBOX_TOKEN",   "")
HERE_API_KEY   = os.getenv("HERE_API_KEY",   "")
ORS_API_KEY    = os.getenv("ORS_API_KEY",    "")

_coord_cache: dict[str, tuple[float, float]] = {}


async def _geocode_here(session: aiohttp.ClientSession, address: str) -> tuple[float, float] | None:
    if not HERE_API_KEY:
        return None
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {"q": address, "apiKey": HERE_API_KEY, "limit": 1}
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            items = data.get("items", [])
            if items:
                pos = items[0]["position"]
                return (pos["lng"], pos["lat"])
            print(f"  [geocode/HERE] Aucun résultat pour: {address}")
    except Exception as e:
        print(f"  [geocode/HERE] Erreur pour '{address}': {e}")
    return None


async def _geocode_nominatim(session: aiohttp.ClientSession, address: str) -> tuple[float, float] | None:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}
    headers = {"User-Agent": "travel-monitor/1.0"}
    try:
        async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            print(f"  [geocode/Nominatim] '{address}' → {data}")
            if data:
                return (float(data[0]["lon"]), float(data[0]["lat"]))
    except Exception as e:
        print(f"  [geocode/Nominatim] Erreur pour '{address}': {e}")
    return None


async def _geocode(session: aiohttp.ClientSession, address: str) -> tuple[float, float]:
    if address in _coord_cache:
        return _coord_cache[address]

    result = await _geocode_here(session, address)
    source = "HERE"

    if result is None:
        result = await _geocode_nominatim(session, address)
        source = "Nominatim"

    if result is not None:
        _coord_cache[address] = result
        lon, lat = result
        print(f"  [geocode/{source}] {address} → ({lat:.4f}, {lon:.4f})")
        return result

    print(f"  [geocode] ÉCHEC pour '{address}' — les APIs basées sur coordonnées seront ignorées")
    return (0.0, 0.0)


async def _fetch_google(session: aiohttp.ClientSession, origin: str, destination: str) -> float | None:
    if not GOOGLE_API_KEY:
        return None
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_API_KEY,
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            element = data["rows"][0]["elements"][0]
            if element["status"] != "OK":
                return None
            duration_sec = element.get("duration_in_traffic", element["duration"])["value"]
            return duration_sec / 60.0
    except Exception:
        return None


async def _fetch_mapbox(session: aiohttp.ClientSession, ox: float, oy: float, dx: float, dy: float) -> float | None:
    if not MAPBOX_TOKEN:
        return None
    coords = f"{ox},{oy};{dx},{dy}"
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving-traffic/{coords}"
    params = {"access_token": MAPBOX_TOKEN, "annotations": "duration"}
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            return data["routes"][0]["duration"] / 60.0
    except Exception:
        return None


async def _fetch_here(session: aiohttp.ClientSession, ox: float, oy: float, dx: float, dy: float) -> float | None:
    if not HERE_API_KEY:
        return None
    url = "https://router.hereapi.com/v8/routes"
    params = {
        "transportMode": "car",
        "origin": f"{oy},{ox}",
        "destination": f"{dy},{dx}",
        "return": "travelSummary",
        "apiKey": HERE_API_KEY,
    }
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            duration_sec = data["routes"][0]["sections"][0]["travelSummary"]["duration"]
            return duration_sec / 60.0
    except Exception:
        return None


async def _fetch_ors(session: aiohttp.ClientSession, ox: float, oy: float, dx: float, dy: float) -> float | None:
    if not ORS_API_KEY:
        return None
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    body = {"coordinates": [[ox, oy], [dx, dy]]}
    try:
        async with session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            data = await resp.json()
            duration_sec = data["routes"][0]["summary"]["duration"]
            return duration_sec / 60.0
    except Exception:
        return None


async def fetch_both_trips(do_morning: bool = True, do_evening: bool = True) -> dict:
    async with aiohttp.ClientSession() as session:
        # Geocode all needed addresses in parallel (cache deduplicates)
        addresses = set()
        if do_morning:
            addresses.update([MORNING_ORIGIN, MORNING_DESTINATION])
        if do_evening:
            addresses.update([EVENING_ORIGIN, EVENING_DESTINATION])
        await asyncio.gather(*[_geocode(session, a) for a in addresses])

        tasks = {}
        if do_morning:
            mo_lon, mo_lat = _coord_cache.get(MORNING_ORIGIN,      (0.0, 0.0))
            md_lon, md_lat = _coord_cache.get(MORNING_DESTINATION, (0.0, 0.0))
            tasks["morning"] = _fetch_direction(session, MORNING_ORIGIN, MORNING_DESTINATION, mo_lon, mo_lat, md_lon, md_lat)
        if do_evening:
            eo_lon, eo_lat = _coord_cache.get(EVENING_ORIGIN,      (0.0, 0.0))
            ed_lon, ed_lat = _coord_cache.get(EVENING_DESTINATION, (0.0, 0.0))
            tasks["evening"] = _fetch_direction(session, EVENING_ORIGIN, EVENING_DESTINATION, eo_lon, eo_lat, ed_lon, ed_lat)

        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))


async def _fetch_direction(
    session: aiohttp.ClientSession,
    origin: str, destination: str,
    ox: float, oy: float, dx: float, dy: float,
) -> dict:
    google, mapbox, here, ors = await asyncio.gather(
        _fetch_google(session, origin, destination),
        _fetch_mapbox(session, ox, oy, dx, dy),
        _fetch_here(session, ox, oy, dx, dy),
        _fetch_ors(session, ox, oy, dx, dy),
    )
    values = [v for v in [google, mapbox, here, ors] if v is not None]
    return {
        "google": google,
        "mapbox": mapbox,
        "here": here,
        "ors": ors,
        "average": sum(values) / len(values) if values else None,
    }
