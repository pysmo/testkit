"""Check the multi-phase fixture's labels and pinned arrivals.

The shipped picks must match the pinned table, carry their phase labels,
and still agree with the travel-time backends within 100 ms. The pP check
needs ObsPy (testkit's `fetch` group) and is skipped without it.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("pysmo.tools.traveltime")

from pysmo.classes import SAC  # noqa: E402
from pysmo.tools.azdist import haversine  # noqa: E402

from testkit.fixtures import MULTI_PHASE_EVENTS_DIR  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "multi_phase_events"))

from fetch_multi_phase_events import PICK_HEADERS  # noqa: E402
from pinned_arrivals import PINNED_ARRIVALS  # noqa: E402
from selection import EVENT_LABEL, STATIONS, station_phases  # noqa: E402
from traveltime_backends import PHASE_BACKENDS  # noqa: E402

TOLERANCE = pd.Timedelta(milliseconds=100)

_EVENT_DIR = MULTI_PHASE_EVENTS_DIR / EVENT_LABEL
_FILES = {
    ".".join(sac_file.name.split(".")[:2]): sac_file
    for sac_file in sorted(_EVENT_DIR.glob("*.BHZ"))
}
_PICKS = [
    pytest.param(key, phase, id=f"{key}-{phase}")
    for key in sorted(_FILES)
    for phase in station_phases(key)
]


def test_every_station_is_shipped() -> None:
    assert sorted(_FILES) == sorted(STATIONS)


@pytest.mark.parametrize("key", sorted(_FILES))
def test_only_the_station_phases_are_picked(key: str) -> None:
    sac = SAC.from_file(_FILES[key])
    for phase, header in PICK_HEADERS.items():
        time = getattr(sac.timestamps, header)
        if phase in station_phases(key):
            assert time is not None
            assert getattr(sac.native, f"k{header}").strip() == phase
        else:
            assert time is None


@pytest.mark.parametrize(("key", "phase"), _PICKS)
def test_pick_matches_the_pinned_arrival(key: str, phase: str) -> None:
    sac = SAC.from_file(_FILES[key])
    pinned = pd.Timestamp(PINNED_ARRIVALS[key][phase])
    assert abs(getattr(sac.timestamps, PICK_HEADERS[phase]) - pinned) < TOLERANCE


@pytest.mark.parametrize(("key", "phase"), _PICKS)
def test_pinned_arrival_tracks_its_backend(key: str, phase: str) -> None:
    if phase == "pP":
        pytest.importorskip("obspy")
    sac = SAC.from_file(_FILES[key])
    event = sac.event
    distance = haversine(event, sac.station)
    fresh = PHASE_BACKENDS[phase](depth=event.depth, distance=distance, phases=[phase])
    pinned = pd.Timestamp(PINNED_ARRIVALS[key][phase])
    assert abs(event.time + fresh[phase] - pinned) < TOLERANCE
