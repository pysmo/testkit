"""Compute the multi-phase fixture's arrivals and write `pinned_arrivals.py`.

Each phase's travel time comes from the backend `traveltime_backends`
names for it. Run only to re-cut the fixture, never as part of a routine
regeneration, which reads the pinned table instead:

    cd scripts/multi_phase_events && uv run --group fetch python pin_arrivals.py
"""

import json
from pathlib import Path

import pandas as pd
from selection import STATIONS, USGS_EVENTID, station_phases
from traveltime_backends import PHASE_BACKENDS, arrival_times

from pysmo import MiniEvent
from pysmo.lib.io import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.tools.azdist import haversine

USGS_EVENT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
TABLE_PATH = Path(__file__).parent / "pinned_arrivals.py"


def fetch_event(eventid: str) -> MiniEvent:
    """Event location and origin time from the USGS catalogue."""
    data = http_get(
        USGS_EVENT_URL,
        {"eventid": eventid, "format": "geojson"},
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        request_retries=DEFAULT_REQUEST_RETRIES,
        retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    )
    feature = json.loads(data)
    lon, lat, depth_km = feature["geometry"]["coordinates"]
    origin_ms = feature["properties"]["time"]
    return MiniEvent(
        latitude=lat,
        longitude=lon,
        depth=depth_km * 1000.0,
        time=pd.Timestamp(origin_ms, unit="ms", tz="UTC"),
    )


def main() -> None:
    event = fetch_event(USGS_EVENTID)
    backends = ", ".join(
        f"{phase}: {backend.__name__}"  # type: ignore[attr-defined]
        for phase, backend in PHASE_BACKENDS.items()
    )
    lines = [
        '"""Pinned arrivals for the multi-phase fixture.',
        "",
        "Written by `pin_arrivals.py`, not by hand. Keyed by `NETWORK.STATION`,",
        "then by phase. `fetch_multi_phase_events.py` writes these as the",
        "initial picks and anchors the fetch window on P.",
        "",
        f"Backends: {backends}.",
        '"""',
        "",
        "PINNED_ARRIVALS: dict[str, dict[str, str]] = {",
    ]
    for key in sorted(STATIONS):
        distance = haversine(event, STATIONS[key])
        times = arrival_times(
            depth=event.depth, distance=distance, phases=station_phases(key)
        )
        lines.append(f'    "{key}": {{')
        for phase, travel_time in times.items():
            lines.append(
                f'        "{phase}": "{(event.time + travel_time).round("us").isoformat()}",'
            )
        lines.append("    },")
    lines.append("}")
    TABLE_PATH.write_text("\n".join(lines) + "\n")
    print(f"wrote {TABLE_PATH}")


if __name__ == "__main__":
    main()
