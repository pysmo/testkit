"""Fetch testkit's multi-phase fixture from USGS and EarthScope.

One deep event (`selection.EVENT_LABEL`) recorded by Alaska broadband
stations (BHZ only), with the instrument response removed and labelled
initial picks for P and pP. The picks and the fetch window come from
`pinned_arrivals.py`, so this script carries no travel-time logic and needs
no ObsPy. `pin_arrivals.py` re-pins the table.

Writes into `../../src/testkit/assets/multi_phase_events`, whatever the
current working directory:

    cd scripts/multi_phase_events && uv run python fetch_multi_phase_events.py
"""

from pathlib import Path

import pandas as pd
from pin_arrivals import fetch_event
from pinned_arrivals import PINNED_ARRIVALS
from selection import EVENT_LABEL, STATIONS, USGS_EVENTID, station_phases

from pysmo import MiniEvent, MiniStation
from pysmo.classes import SAC, StationXML
from pysmo.functions import detrend, taper
from pysmo.tools.signal import remove_response
from pysmo.tools.web import fetch_stationxml

OUTPUT_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "testkit"
    / "assets"
    / "multi_phase_events"
)

# Window around the pinned P, as in `aimbat-sampledata`. pP arrives 94 to
# 99 s after P, which leaves room for an ICCS window after it.
MARGIN_BEFORE = pd.Timedelta(minutes=2)
DURATION_AFTER = pd.Timedelta(minutes=3)

# SAC header holding each phase's pick, and its label header. pP uses t5,
# clear of the t1 to t3 that AIMBAT v1 writes.
PICK_HEADERS = {"P": "t0", "pP": "t5"}

_IDEP_BY_UNITS = {"m": "disp", "m/s": "vel", "m/s**2": "acc"}


def _deconvolve(sac: SAC, station: MiniStation) -> str:
    """Remove the instrument response from `sac.seismogram`, in place.

    Returns the SAC `idep` value matching the response's input units.
    """
    seismogram = sac.seismogram
    xml = fetch_stationxml(station=station)
    response = StationXML.from_bytes(xml, time=seismogram.begin_time).response

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


def _fetch_station(key: str, event: MiniEvent, event_dir: Path) -> bool:
    station = STATIONS[key]
    arrivals = {
        phase: pd.Timestamp(PINNED_ARRIVALS[key][phase])
        for phase in station_phases(key)
    }
    starttime = arrivals["P"] - MARGIN_BEFORE
    endtime = arrivals["P"] + DURATION_AFTER
    try:
        sac = SAC.fetch(station=station, starttime=starttime, endtime=endtime)
        # dataselect can return a short prefix instead of an error when the
        # station has a gap partway through.
        if sac.seismogram.end_time < endtime - pd.Timedelta(seconds=1):
            raise RuntimeError(
                f"incomplete data: got {sac.seismogram.begin_time} to "
                f"{sac.seismogram.end_time}, requested up to {endtime}"
            )
        idep = _deconvolve(sac, station)
    except Exception as exc:  # noqa: BLE001 - skip and report, don't abort the run
        print(f"skip {key}: {exc}")
        return False

    sac.native.idep = idep
    # v7 for double-precision o and t headers (float32 visibly truncates them).
    sac.native.nvhdr = 7
    sac.event.latitude = event.latitude
    sac.event.longitude = event.longitude
    sac.event.depth = event.depth
    sac.event.time = event.time
    for phase, time in arrivals.items():
        header = PICK_HEADERS[phase]
        setattr(sac.timestamps, header, time)
        setattr(sac.native, f"k{header}", phase)

    filename = f"{station.network}.{station.name}.--.BHZ"
    sac.write(event_dir / filename)
    print(f"fetched {EVENT_LABEL}/{filename}: {', '.join(arrivals)}")
    return True


def main() -> None:
    event = fetch_event(USGS_EVENTID)
    event_dir = OUTPUT_DIR / EVENT_LABEL
    event_dir.mkdir(parents=True, exist_ok=True)
    fetched = sum(_fetch_station(key, event, event_dir) for key in sorted(STATIONS))
    if fetched == 0:
        raise RuntimeError(f"{EVENT_LABEL}: no stations fetched")
    print(f"{EVENT_LABEL}: {fetched}/{len(STATIONS)} stations fetched")


if __name__ == "__main__":
    main()
