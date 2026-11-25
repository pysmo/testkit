"""Pin the three-component fixture's events, site coordinates and arrivals.

Writes `three_component_arrivals.py`. Each phase's travel time comes from
the backend `three_component_backends` names for it. Run only to re-cut the
fixture, never as part of a routine regeneration, which reads the pinned
table instead:

    cd scripts/three_component_events
    uv run --group fetch python pin_three_component_arrivals.py
"""

import json
from pathlib import Path
from pprint import pformat

import pandas as pd
from three_component_backends import PHASE_BACKENDS, arrival_times
from three_component_selection import (
    EVENTS,
    GAPPY,
    GAPPY_EVENT,
    GAPPY_EVENTID,
    GAPPY_PHASES,
)

from pysmo import MiniEvent, MiniLocation
from pysmo.lib.io import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.tools.azdist import haversine

USGS_EVENT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
STATION_URL = "https://service.earthscope.org/fdsnws/station/1/query"
TABLE_PATH = Path(__file__).parent / "three_component_arrivals.py"


def _get(url: str, params: dict[str, str]) -> bytes:
    return http_get(
        url,
        params,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        request_retries=DEFAULT_REQUEST_RETRIES,
        retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    )


def fetch_event(eventid: str) -> MiniEvent:
    """Event location and origin time from the USGS catalogue."""
    feature = json.loads(
        _get(USGS_EVENT_URL, {"eventid": eventid, "format": "geojson"})
    )
    lon, lat, depth_km = feature["geometry"]["coordinates"]
    return MiniEvent(
        latitude=lat,
        longitude=lon,
        depth=depth_km * 1000.0,
        time=pd.Timestamp(feature["properties"]["time"], unit="ms", tz="UTC"),
    )


def _site_location(network: str, station: str, time: pd.Timestamp) -> MiniLocation:
    text = _get(
        STATION_URL,
        {
            "net": network,
            "sta": station,
            "level": "station",
            "format": "text",
            "starttime": (time - pd.Timedelta(days=1)).floor("s").isoformat(),
            "endtime": (time + pd.Timedelta(days=1)).floor("s").isoformat(),
        },
    ).decode("ascii")
    lat, lon = text.splitlines()[1].split("|")[2:4]
    return MiniLocation(latitude=float(lat), longitude=float(lon))


def _pin(
    event: MiniEvent, site_keys: list[str], phases: tuple[str, ...]
) -> dict[str, dict[str, str]]:
    pinned: dict[str, dict[str, str]] = {}
    for key in site_keys:
        network, station, _ = key.split(".")
        location = _site_location(network, station, event.time)
        times = arrival_times(
            depth=event.depth, distance=haversine(event, location), phases=phases
        )
        pinned[key] = {
            "latitude": str(location.latitude),
            "longitude": str(location.longitude),
            **{
                phase: (event.time + t).round("us").isoformat()
                for phase, t in times.items()
            },
        }
    return pinned


def main() -> None:
    events: dict[str, dict[str, str]] = {}
    arrivals: dict[str, dict[str, dict[str, str]]] = {}
    specs = [
        (label, spec.usgs_eventid, spec.phases, sorted({s.key for s in spec.sites}))
        for label, spec in EVENTS.items()
    ] + [(GAPPY_EVENT, GAPPY_EVENTID, GAPPY_PHASES, [GAPPY.key])]
    for label, eventid, phases, keys in specs:
        event = fetch_event(eventid)
        events[label] = {
            "usgs_eventid": eventid,
            "time": event.time.isoformat(),
            "latitude": str(event.latitude),
            "longitude": str(event.longitude),
            "depth": str(event.depth),
        }
        arrivals[label] = _pin(event, keys, phases)

    backends = ", ".join(
        f"{phase}: {backend.__name__}"  # type: ignore[attr-defined]
        for phase, backend in PHASE_BACKENDS.items()
    )
    TABLE_PATH.write_text(
        '"""Pinned events, site coordinates and arrivals, three-component fixture.\n'
        "\n"
        "Written by `pin_three_component_arrivals.py`, not by hand.\n"
        "`PINNED_ARRIVALS` is keyed by event label, then\n"
        "`NETWORK.STATION.LOCATION`; each site has its latitude, longitude and\n"
        "the arrival time of each phase.\n"
        "\n"
        f"Backends: {backends}.\n"
        '"""\n'
        "\n"
        f"PINNED_EVENTS: dict[str, dict[str, str]] = {pformat(events, width=80)}\n"
        "\n"
        "PINNED_ARRIVALS: dict[str, dict[str, dict[str, str]]] = "
        f"{pformat(arrivals, width=80)}\n"
    )
    print(f"wrote {TABLE_PATH}")


if __name__ == "__main__":
    main()
