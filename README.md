# travel-monitor

Monitors two daily commute routes and sends push notifications via [ntfy](https://ntfy.sh) when travel time crosses a threshold. Polls up to 4 APIs (HERE, Google Maps, Mapbox, ORS) in parallel and averages the results.

---

## Commands

```bash
# Start
./run.sh

# Start with rebuild (after code changes)
./run.sh --build

# Start fresh (clear state + logs)
./run.sh --clear

# Start fresh + rebuild
./run.sh --clear --build

# Run in background
./run.sh -d

# View live logs
docker compose logs -f

# Stop
docker compose down
```

---

## Installation

**1. Clone and enter the repo**
```bash
git clone <repo-url> && cd traffic-info
```

**2. Create config file**
```bash
cp config/settings.example.env config/settings.env
```

**3. Get a HERE API key**
- Go to [developer.here.com](https://developer.here.com) → your project → **API Keys** → Create API Key
- Paste it as `HERE_API_KEY` in `config/settings.env`

**4. Set up ntfy**
- Pick a secret topic name (acts as a password)
- Install the [ntfy app](https://ntfy.sh) on your phone and subscribe to your topic
- Set `NTFY_TOPIC=your-secret-topic` in `config/settings.env`

**5. Fill in your routes**
```env
MORNING_ORIGIN="100 rue Claude-Audy, Saint-Jérôme, QC"
MORNING_DESTINATION="200 rue Bridge, Montréal, QC"
EVENING_ORIGIN="200 rue Bridge, Montréal, QC"
EVENING_DESTINATION="100 rue Claude-Audy, Saint-Jérôme, QC"
```

**6. Launch**
```bash
./run.sh --build
```

---

## How it works

Each poll (default every 10 min):
1. Checks if current time is within the morning or evening active window
2. Geocodes addresses via HERE (cached after first call)
3. Fetches travel time from each configured API in parallel
4. Computes the average
5. Compares to the threshold and to the previous state
6. Sends a ntfy notification **only when the state changes** (e.g. under → over threshold)
7. Logs every result to `data/travel_log.csv`

**Notification states:** `🔵 état initial` → `🟢 sous le seuil` ↔ `🔴 au-dessus du seuil`

**Key files:**
| File | Role |
|---|---|
| `config/settings.env` | Your config (gitignored) |
| `data/state.json` | Current state per trip (gitignored) |
| `data/travel_log.csv` | Full history CSV (gitignored) |
