"""Fetch testkit's ICCS/MCCC array fixture from USGS + EarthScope.

Three Alaska-recorded teleseismic events (`AK`/`AV`/`TA` networks, BHZ only),
with instrument response removed and an initial P-pick annotated, exactly as
`pysmo.tools.iccs`/`aimbat` expect. The event/station selection below is
**not** rediscovered or reselected here — it is the exact result of manual
QC review carried out inside AIMBAT (deselecting, not deleting, seismograms
in an `aimbat.db` project built from `../data-example`), then extracted from
that database. See `PROVENANCE.md` (in the output directory) for the full
history and rationale, and this repo's `HANDOFF.md`.

This script never reads from `data-example` — it re-fetches each event and
station independently from USGS/EarthScope by event ID and station
code/coordinates, so testkit has no runtime or regeneration dependency on
that repo (which may keep changing). Only the *selection* (which events,
which stations) came from there originally.

Re-run with `uv run python fetch_iccs_events.py` from this directory to
regenerate the dataset from scratch; it writes into
``../../src/testkit/assets/iccs_events`` regardless of the current working
directory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pysmo import MiniEvent, MiniStation
from pysmo.classes import SAC, StationXML
from pysmo.functions import detrend, taper
from pysmo.lib.io import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.tools.azdist import haversine
from pysmo.tools.signal import remove_response
from pysmo.tools.web import fetch_stationxml, fetch_travel_times

OUTPUT_DIR = (
    Path(__file__).parent.parent.parent / "src" / "testkit" / "assets" / "iccs_events"
)

USGS_EVENT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Same P-coda window formula as data-example's fetch_events.py, so
# re-fetching here reproduces what was already manually QC'd in AIMBAT.
MARGIN_BEFORE = pd.Timedelta(minutes=2)
DURATION_AFTER = pd.Timedelta(minutes=3)


@dataclass(frozen=True)
class EventSpec:
    label: str
    usgs_eventid: str


EVENTS = [
    EventSpec("solomon_islands", "usc000phx5"),
    EventSpec("komandorskiye_ostrova", "us20009x42"),
    EventSpec("iraq", "us2000bmcg"),
]

# One shared station pool (lat/lon as discovered/curated in data-example),
# keyed by "NET.STA" — most stations are used by more than one event.
STATIONS: dict[str, MiniStation] = {
    key: MiniStation(
        name=key.split(".")[1],
        network=key.split(".")[0],
        location="--",
        channel="BHZ",
        latitude=lat,
        longitude=lon,
    )
    for key, (lat, lon) in {
        "AK.ATKA": (52.2015991210938, -174.197494506836),
        "AK.BAL": (61.0359992980957, -142.346206665039),
        "AK.BWN": (64.1732025146484, -149.299102783203),
        "AK.CAPN": (60.7682991027832, -151.153900146484),
        "AK.CAST": (63.4188003540039, -152.084396362305),
        "AK.CCB": (64.6453018188477, -147.805297851563),
        "AK.CHI": (55.8218002319336, -155.622497558594),
        "AK.CHUM": (63.8827018737793, -152.315200805664),
        "AK.EYAK": (60.548698425293, -145.75),
        "AK.FIRE": (61.1426010131836, -150.216400146484),
        "AK.FYU": (66.5656967163086, -145.23420715332),
        "AK.GRNC": (60.7314987182617, -141.755798339844),
        "AK.HIN": (60.3959999084473, -146.503494262695),
        "AK.JIS": (58.2757987976074, -134.384796142578),
        "AK.KAI": (59.9267997741699, -144.418792724609),
        "AK.KHIT": (60.442699432373, -143.251007080078),
        "AK.KIAG": (60.9230995178223, -142.360504150391),
        "AK.KLU": (61.4924011230469, -145.922698974609),
        "AK.KNK": (61.4131011962891, -148.45849609375),
        "AK.MCK": (63.7318000793457, -148.937301635742),
        "AK.NICH": (60.2356986999512, -143.971298217773),
        "AK.PAX": (62.969898223877, -145.46989440918),
        "AK.PIN": (60.0959014892578, -140.252502441406),
        "AK.PNL": (59.6669998168945, -139.401397705078),
        "AK.SAMH": (60.1293983459473, -140.782806396484),
        "AK.SKN": (61.9799995422363, -151.531692504883),
        "AK.YAH": (60.3582992553711, -141.751007080078),
        "AV.AKRB": (54.1291999816895, -166.07080078125),
        "AV.MAPS": (53.8082008361816, -166.940704345703),
        "AV.RDDF": (60.5912017822266, -152.688293457031),
        "AV.SPCP": (61.2654991149902, -152.154998779297),
        "AV.SSBA": (54.771800994873, -164.126495361328),
        "TA.POKR": (65.1171035766602, -147.433502197266),
        "TA.TOLK": (68.6408004760742, -149.572402954102),
    }.items()
}

# Selected (not deselected) seismograms per event, exactly as narrowed by
# hand in AIMBAT.
EVENT_STATIONS: dict[str, list[str]] = {
    "solomon_islands": [
        "AK.ATKA",
        "AK.BAL",
        "AK.BWN",
        "AK.CCB",
        "AK.EYAK",
        "AK.FYU",
        "AK.GRNC",
        "AK.HIN",
        "AK.JIS",
        "AK.KIAG",
        "AK.KNK",
        "AK.MCK",
        "AK.PAX",
        "AK.PNL",
        "TA.POKR",
        "TA.TOLK",
    ],
    "komandorskiye_ostrova": [
        "AK.BWN",
        "AK.CAPN",
        "AK.CAST",
        "AK.CCB",
        "AK.CHUM",
        "AK.EYAK",
        "AK.FIRE",
        "AK.FYU",
        "AK.GRNC",
        "AK.JIS",
        "AK.KHIT",
        "AK.KIAG",
        "AK.KLU",
        "AK.KNK",
        "AK.MCK",
        "AK.NICH",
        "AK.PAX",
        "AK.PIN",
        "AK.PNL",
        "AK.SAMH",
        "AV.AKRB",
        "AV.MAPS",
        "AV.RDDF",
        "AV.SSBA",
        "TA.POKR",
    ],
    "iraq": [
        "AK.BWN",
        "AK.CAPN",
        "AK.CAST",
        "AK.CCB",
        "AK.CHI",
        "AK.CHUM",
        "AK.EYAK",
        "AK.FYU",
        "AK.GRNC",
        "AK.HIN",
        "AK.JIS",
        "AK.KAI",
        "AK.KHIT",
        "AK.KIAG",
        "AK.KLU",
        "AK.KNK",
        "AK.MCK",
        "AK.NICH",
        "AK.PAX",
        "AK.PIN",
        "AK.PNL",
        "AK.SAMH",
        "AK.SKN",
        "AK.YAH",
        "AV.SPCP",
        "TA.POKR",
        "TA.TOLK",
    ],
}


def _fetch_event(eventid: str) -> MiniEvent:
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


_IDEP_BY_UNITS = {"m": "disp", "m/s": "vel", "m/s**2": "acc"}


def _deconvolve(sac: SAC, station: MiniStation) -> str:
    """Remove the instrument response from `sac.seismogram`, in place.

    Returns the SAC `idep` value matching `response.input_units`, for the
    caller to set.
    """
    seismogram = sac.seismogram
    xml = fetch_stationxml(station=station)
    response = StationXML.from_bytes(xml, time=seismogram.begin_time)

    nyquist = 0.5 / seismogram.delta.total_seconds()
    stage_nyquist = min(
        (stage.input_sample_rate / 2 for stage in response.stages), default=nyquist
    )
    f4 = 0.8 * min(nyquist, stage_nyquist)
    f3 = f4 * 0.9
    f1 = min(abs(pole) for pole in response.poles if pole != 0) / 10
    f2 = f1 * 10

    detrend(seismogram)
    taper(seismogram, 0.05)
    remove_response(seismogram, response, pre_filt=(f1, f2, f3, f4))
    return _IDEP_BY_UNITS.get(response.input_units.lower(), "unkn")


def _fetch_one_event(spec: EventSpec, event: MiniEvent) -> None:
    event_dir = OUTPUT_DIR / spec.label
    event_dir.mkdir(parents=True, exist_ok=True)

    fetched = 0
    for key in EVENT_STATIONS[spec.label]:
        station = STATIONS[key]
        dist_deg = haversine(event, station)
        try:
            travel_times = fetch_travel_times(event.depth / 1000.0, dist_deg, ["P"])
            predicted_p = event.time + pd.Timedelta(seconds=travel_times["P"])
            starttime = predicted_p - MARGIN_BEFORE
            endtime = predicted_p + DURATION_AFTER
            sac = SAC.fetch(station=station, starttime=starttime, endtime=endtime)
            # dataselect can return a short prefix instead of erroring
            # outright when the station has a data gap partway through.
            if sac.seismogram.end_time < endtime - pd.Timedelta(seconds=1):
                raise RuntimeError(
                    f"incomplete data: got {sac.seismogram.begin_time} to "
                    f"{sac.seismogram.end_time}, requested up to {endtime}"
                )
            idep = _deconvolve(sac, station)
        except Exception as exc:  # noqa: BLE001 - skip and log, don't abort the run
            print(f"skip {spec.label} {key}: {exc}")
            continue

        sac.native.idep = idep
        # v7 for double-precision o/t0 (float32 visibly truncates predicted_p).
        sac.native.nvhdr = 7
        sac.event.latitude = event.latitude
        sac.event.longitude = event.longitude
        sac.event.depth = event.depth
        sac.event.time = event.time
        sac.timestamps.t0 = predicted_p  # initial pick, for ICCS-style workflows

        filename = f"{station.network}.{station.name}.--.BHZ"
        sac.write(event_dir / filename)
        fetched += 1
        print(f"fetched {spec.label}/{filename}: {starttime} to {endtime}")

    expected = len(EVENT_STATIONS[spec.label])
    if fetched == 0:
        raise RuntimeError(f"{spec.label}: no stations fetched, check geometry")
    print(f"{spec.label}: {fetched}/{expected} stations fetched")


def main() -> None:
    for spec in EVENTS:
        event = _fetch_event(spec.usgs_eventid)
        _fetch_one_event(spec, event)


if __name__ == "__main__":
    main()
