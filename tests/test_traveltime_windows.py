"""Check the pinned fetch-window predicted-P arrivals still track pysmo.

The ``reference_event`` and ``iccs_events`` bundles pin their predicted-P
arrival (EarthScope ``irisws-traveltime``, retired 2026) rather than
recomputing it, so they regenerate deterministically. This is the one place
in testkit that carries a ``pysmo.tools.traveltime`` dependency: it recomputes
P with pysmo's current in-house tau-p solver and flags drift from the pinned
value beyond 100 ms — turning "solver moved, fixtures silently re-window on
regen" into a visible failure and a conscious decision.

The pinned values themselves are unaffected by any solver drift this test
reports; the ``iccs_events`` windows carry 2 minutes of pre-roll and the
``reference_event`` window end is surface-wave-derived. The test guards the
*documented choice*, not fixture usability.
"""

from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("pysmo.tools.traveltime")

from pysmo import Event, MiniEvent, MiniStation, Station  # noqa: E402
from pysmo.classes import SAC  # noqa: E402
from pysmo.tools.azdist import haversine  # noqa: E402
from pysmo.tools.traveltime import travel_times  # noqa: E402

from testkit.fixtures import ICCS_EVENTS_DIR  # noqa: E402

TOLERANCE = pd.Timedelta(milliseconds=100)

# reference_event: the single IU.ANMO.00 / 2010 Maule geometry. Pinned
# predicted P = fetch-window start + 2 min (see fetch_reference_event.py).
_REFERENCE_EVENT = MiniEvent(
    latitude=-36.122,
    longitude=-72.898,
    depth=22900.0,
    time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
)
_REFERENCE_STATION = MiniStation(
    name="ANMO",
    network="IU",
    location="00",
    channel="BHZ",
    latitude=34.945981,
    longitude=-106.457133,
)
_REFERENCE_PREDICTED_P = pd.Timestamp("2010-02-27T06:46:06.04Z")

# iccs_events geometries where pysmo's P and the pinned EarthScope P
# diverge by more than 100 ms. Just one: AV.AKRB (14.56 deg) sits on a
# branch-crossover cusp near the lower edge of the upper-mantle
# triplication, where pysmo's first-arrival pick and EarthScope's disagree
# by ~177 ms on which branch arrives first; the geometries on either side
# (14.1 deg, 15.6 deg) agree to under 1 ms. Immaterial to the window
# (2 min of pre-roll). xfail is non-strict so a solver tweak that closes
# the cusp turns it green without breaking CI.
_KNOWN_SOLVER_DIVERGENCE: frozenset[tuple[str, str]] = frozenset(
    {
        ("komandorskiye_ostrova", "AV.AKRB"),
    }
)

_ICCS_PARAMS: list[object] = []
for _sac_file in sorted(ICCS_EVENTS_DIR.glob("*/*.BHZ")):
    _label = _sac_file.parent.name
    _net, _sta = _sac_file.name.split(".")[:2]
    _marks = (
        [pytest.mark.xfail(reason="branch-crossover cusp", strict=False)]
        if (_label, f"{_net}.{_sta}") in _KNOWN_SOLVER_DIVERGENCE
        else []
    )
    _ICCS_PARAMS.append(
        pytest.param(_sac_file, id=f"{_label}-{_net}.{_sta}", marks=_marks)
    )


def _predicted_p(event: Event, station: Station) -> pd.Timestamp:
    distance = haversine(event, station)
    arrivals = travel_times(depth=event.depth, distance=distance, phases=["P"])
    assert "P" in arrivals, f"solver returned no P arrival at {distance:.2f} deg"
    return event.time + arrivals["P"]


def test_reference_event_window() -> None:
    fresh = _predicted_p(_REFERENCE_EVENT, _REFERENCE_STATION)
    assert abs(fresh - _REFERENCE_PREDICTED_P) < TOLERANCE


@pytest.mark.parametrize("sac_file", _ICCS_PARAMS)
def test_iccs_event_window(sac_file: object) -> None:
    sac = SAC.from_file(str(sac_file))
    pinned = sac.timestamps.t0
    assert pinned is not None, "shipped iccs SAC has no t0 pick"
    fresh = _predicted_p(sac.event, sac.station)
    assert abs(fresh - pinned) < TOLERANCE
