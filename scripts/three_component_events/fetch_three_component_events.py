"""Fetch testkit's three-component fixture from EarthScope.

Writes, from the pinned table in `three_component_arrivals.py` (no
travel-time logic, no ObsPy):

- one directory per event in `three_component_selection.EVENTS`, with a SAC
  file per site and channel: response removed, resampled to 20 Hz unless the
  site keeps its native rate, orientation from StationXML, labelled picks on
  the channels each phase is measured on (P and pP on Z, S and SKS on the
  horizontals);
- `special/`, files with one deliberate property each, for the tests that
  need it (see `PROVENANCE.md`).

Writes into `../../src/testkit/assets/three_component_events`, replacing what
is there, whatever the current working directory:

    cd scripts/three_component_events && uv run python fetch_three_component_events.py
"""

import copy
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from three_component_arrivals import PINNED_ARRIVALS, PINNED_EVENTS
from three_component_selection import (
    EVENTS,
    GAPPY,
    GAPPY_EVENT,
    MISSING_ORIENTATION,
    MULTIPLEXED,
    MULTIPLEXED_EVENT,
    P_ON_ALL_CHANNELS,
    ROTATED_AS_BHN,
    Site,
    is_horizontal,
    phases_on_channel,
)

from pysmo import MiniEvent, MiniStation
from pysmo.classes import SAC, StationXML
from pysmo.exceptions import MissingValueError
from pysmo.functions import detrend, resample, taper
from pysmo.lib.io import (
    DEFAULT_REQUEST_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    http_get,
)
from pysmo.tools.azdist import backazimuth
from pysmo.tools.signal import lowpass, remove_response
from pysmo.tools.web import fetch_stationxml

OUTPUT_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "testkit"
    / "assets"
    / "three_component_events"
)
SPECIAL_DIR = OUTPUT_DIR / "special"

DATASELECT_URL = "https://service.earthscope.org/fdsnws/dataselect/1/query"
STATION_URL = "https://service.earthscope.org/fdsnws/station/1/query"


def _get(url: str, params: dict[str, str]) -> bytes:
    return http_get(
        url,
        params,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        request_retries=DEFAULT_REQUEST_RETRIES,
        retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    )


# As in `aimbat-sampledata`: from 2 min before the first arrival to 3 min
# after the last, shared by every channel of a site.
MARGIN_BEFORE = pd.Timedelta(minutes=2)
DURATION_AFTER = pd.Timedelta(minutes=3)

DELTA = pd.Timedelta(seconds=0.05)
# Below the new Nyquist (10 Hz): resample's Fourier method cuts the spectrum
# hard, so the low-pass keeps it from ringing.
RESAMPLE_LOWPASS_HZ = 8.0

# SAC header holding each phase's pick, and its label header. t1 to t3 stay
# free for AIMBAT v1.
PICK_HEADERS = {"P": "t0", "pP": "t5", "S": "t6", "SKS": "t7"}

_IDEP_BY_UNITS = {"m": "disp", "m/s": "vel", "m/s**2": "acc"}


def event_of(label: str) -> MiniEvent:
    pinned = PINNED_EVENTS[label]
    return MiniEvent(
        latitude=float(pinned["latitude"]),
        longitude=float(pinned["longitude"]),
        depth=float(pinned["depth"]),
        time=pd.Timestamp(pinned["time"]),
    )


def arrivals_of(
    label: str, key: str, phases: tuple[str, ...]
) -> dict[str, pd.Timestamp]:
    pinned = PINNED_ARRIVALS[label][key]
    return {phase: pd.Timestamp(pinned[phase]) for phase in phases}


def window(arrivals: dict[str, pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = min(arrivals.values()) - MARGIN_BEFORE
    return start, max(arrivals.values()) + DURATION_AFTER


def _station(label: str, site: Site, channel: str) -> MiniStation:
    pinned = PINNED_ARRIVALS[label][site.key]
    return MiniStation(
        name=site.station,
        network=site.network,
        location=site.location,
        channel=channel,
        latitude=float(pinned["latitude"]),
        longitude=float(pinned["longitude"]),
    )


def _deconvolve(sac: SAC, station: MiniStation) -> tuple[str, StationXML]:
    """Remove the instrument response, in place, as `aimbat-sampledata` does.

    Returns the SAC `idep` value and the channel epoch, which carries the
    orientation.
    """
    seismogram = sac.seismogram
    epoch = StationXML.from_bytes(
        fetch_stationxml(station=station), time=seismogram.begin_time
    )
    response = epoch.response
    nyquist = 0.5 / seismogram.delta.total_seconds()
    stage_nyquist = min(
        (stage.input_sample_rate / 2 for stage in response.stages), default=nyquist
    )
    f4 = 0.8 * min(nyquist, stage_nyquist)
    f1 = min(abs(pole) for pole in response.poles if pole != 0) / 10
    detrend(seismogram)
    taper(seismogram, 0.05)
    remove_response(seismogram, response, pre_filt=(f1, f1 * 10, f4 * 0.9, f4))
    return _IDEP_BY_UNITS.get(response.input_units.lower(), "unkn"), epoch


def _fetch_channel(
    station: MiniStation, site: Site, start: pd.Timestamp, end: pd.Timestamp
) -> SAC:
    sac = SAC.fetch(station=station, starttime=start, endtime=end)
    # dataselect can return a short prefix instead of an error when the
    # station has a gap partway through.
    if sac.seismogram.end_time < end - pd.Timedelta(seconds=1):
        raise RuntimeError(f"incomplete data up to {sac.seismogram.end_time}")
    idep, epoch = _deconvolve(sac, station)
    sac.native.idep = idep
    if site.resample:
        lowpass(sac.seismogram, RESAMPLE_LOWPASS_HZ, corners=4, zerophase=True)
        resample(sac.seismogram, DELTA)
    try:
        azimuth, dip = epoch.azimuth, epoch.dip
    except MissingValueError:
        pass
    else:
        sac.orientation.azimuth = azimuth
        sac.orientation.dip = dip
    return sac


def _fetch_site(label: str, site: Site, event: MiniEvent, event_dir: Path) -> bool:
    phases = EVENTS[label].phases
    arrivals = arrivals_of(label, site.key, phases)
    start, end = window(arrivals)
    try:
        fetched = {
            channel: _fetch_channel(_station(label, site, channel), site, start, end)
            for channel in site.channels
        }
    except Exception as exc:  # noqa: BLE001 - skip and report, don't abort the run
        print(f"skip {label}/{site.key} {site.channels[0][:2]}: {exc}")
        return False
    for channel, sac in fetched.items():
        sac.event.latitude = event.latitude
        sac.event.longitude = event.longitude
        sac.event.depth = event.depth
        sac.event.time = event.time
        for phase in phases_on_channel(phases, channel):
            header = PICK_HEADERS[phase]
            setattr(sac.timestamps, header, arrivals[phase])
            setattr(sac.native, f"k{header}", phase)
        # v7 for double-precision o and t headers.
        sac.write(event_dir / f"{site.key}.{channel}", nvhdr=7)
    print(f"fetched {label}/{site.key} {', '.join(site.channels)}")
    return True


def _shipped(label: str, key: str) -> dict[str, SAC]:
    """The shipped channels of a site, keyed by channel code."""
    return {
        path.name.rsplit(".", 1)[1]: SAC.from_file(path)
        for path in sorted((OUTPUT_DIR / label).glob(f"{key}.*"))
    }


def _write(sacs: dict[str, SAC], directory: Path, key: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for channel, sac in sacs.items():
        sac.write(directory / f"{key}.{channel}", nvhdr=7)


def _missing_orientation() -> None:
    label, key = MISSING_ORIENTATION
    sacs = _shipped(label, key)
    for sac in sacs.values():
        sac.native.cmpaz = None
        sac.native.cmpinc = None
    _write(sacs, SPECIAL_DIR / "missing_orientation", key)


def _p_on_all_channels() -> None:
    label, key = P_ON_ALL_CHANNELS
    sacs = _shipped(label, key)
    p_pick = sacs["BHZ"].timestamps.t0
    for channel, sac in sacs.items():
        if is_horizontal(channel):
            sac.timestamps.t0 = p_pick
            sac.native.kt0 = "P"
    _write(sacs, SPECIAL_DIR / "p_on_all_channels", key)


def reference_rt(sacs: dict[str, SAC]) -> tuple[SAC, SAC]:
    """R and T from a site's two horizontals, by direct projection.

    Each horizontal contributes its data times the cosine of the angle
    between its azimuth (from its header) and the target's. R points away
    from the source (back azimuth + 180), T 90 deg clockwise from R.
    Independent of pysmo's rotation code, so it can check it.
    """
    horizontals = [sac for channel, sac in sacs.items() if is_horizontal(channel)]
    first = horizontals[0]
    baz = backazimuth(first.event, first.station)
    out = []
    for name, target in (("R", (baz + 180) % 360), ("T", (baz + 270) % 360)):
        data = sum(
            np.asarray(sac.seismogram.data, dtype=float)
            * np.cos(np.radians(sac.orientation.azimuth - target))
            for sac in horizontals
        )
        sac = _copy(first)
        sac.seismogram.data = data
        sac.station.channel = first.station.channel[:2] + name
        sac.orientation.azimuth = target
        sac.orientation.dip = 0.0
        for header in PICK_HEADERS.values():
            setattr(sac.timestamps, header, getattr(first.timestamps, header))
        out.append(sac)
    return out[0], out[1]


def _copy(sac: SAC) -> SAC:
    return copy.deepcopy(sac)


def _reference_rt_and_rotated_as_bhn() -> None:
    label = "central_peru"
    for key in sorted({site.key for site in EVENTS[label].sites}):
        sacs = _shipped(label, key)
        if not sacs:
            continue
        r, t = reference_rt(sacs)
        _write(
            {r.station.channel: r, t.station.channel: t},
            SPECIAL_DIR / "reference_rt",
            key,
        )
        if (label, key) == ROTATED_AS_BHN:
            # R, but labelled as the site's BHN: a second source for that stream.
            r.station.channel = "BHN"
            _write({"BHN": r}, SPECIAL_DIR / "rotated_as_bhn", key)


def _raw(
    label: str, site: Site, phases: tuple[str, ...]
) -> tuple[bytes, pd.Timestamp, pd.Timestamp]:
    start, end = window(arrivals_of(label, site.key, phases))
    data = _get(
        DATASELECT_URL,
        {
            "net": site.network,
            "sta": site.station,
            "loc": site.location,
            "cha": ",".join(site.channels),
            "starttime": start.isoformat(),
            "endtime": end.isoformat(),
        },
    )
    return data, start, end


def _multiplexed() -> None:
    data, start, end = _raw(
        MULTIPLEXED_EVENT, MULTIPLEXED, EVENTS[MULTIPLEXED_EVENT].phases
    )
    xml = _get(
        STATION_URL,
        {
            "net": MULTIPLEXED.network,
            "sta": MULTIPLEXED.station,
            "loc": MULTIPLEXED.location,
            "cha": ",".join(MULTIPLEXED.channels),
            "level": "response",
            "starttime": start.isoformat(),
            "endtime": end.isoformat(),
        },
    )
    directory = SPECIAL_DIR / "multiplexed"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{MULTIPLEXED.key}.mseed").write_bytes(data)
    (directory / f"{MULTIPLEXED.key}.xml").write_bytes(xml)


def _gappy() -> None:
    data, _, _ = _raw(GAPPY_EVENT, GAPPY, ("P", "S"))
    directory = SPECIAL_DIR / "gappy"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{GAPPY.key}.mseed").write_bytes(data)


def main() -> None:
    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
    for label, spec in EVENTS.items():
        event_dir = OUTPUT_DIR / label
        event_dir.mkdir(parents=True)
        event = event_of(label)
        fetched = sum(_fetch_site(label, site, event, event_dir) for site in spec.sites)
        print(f"{label}: {fetched}/{len(spec.sites)} sites fetched")
    _missing_orientation()
    _p_on_all_channels()
    _reference_rt_and_rotated_as_bhn()
    _multiplexed()
    _gappy()
    print("special files written")


if __name__ == "__main__":
    main()
