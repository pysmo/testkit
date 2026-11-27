"""Check the three-component fixture against its selection and pinned table.

The files must be the selected sites and channels, carry the pinned picks on
the right channels, and the files under `special/` must each have the one
property they are there for. The reference R/T must agree with pysmo's
rotation. The pP and SKS backend checks need ObsPy (testkit's `fetch` group)
and are skipped without it.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pysmo.tools.components")

from pysmo import MiniEvent, MiniLocation  # noqa: E402
from pysmo.classes import SAC, MSeed  # noqa: E402
from pysmo.tools.azdist import backazimuth, haversine  # noqa: E402
from pysmo.tools.components import Components, rotate_to_rt  # noqa: E402

from testkit.fixtures import THREE_COMPONENT_EVENTS_DIR, _sites  # noqa: E402

sys.path.insert(
    0, str(Path(__file__).parent.parent / "scripts" / "three_component_events")
)

from fetch_three_component_events import DELTA, PICK_HEADERS  # noqa: E402
from three_component_arrivals import PINNED_ARRIVALS, PINNED_EVENTS  # noqa: E402
from three_component_backends import PHASE_BACKENDS  # noqa: E402
from three_component_selection import (  # noqa: E402
    EVENTS,
    MISSING_ORIENTATION,
    P_ON_ALL_CHANNELS,
    ROTATED_AS_BHN,
    Site,
    is_horizontal,
    phases_on_channel,
)

TOLERANCE = pd.Timedelta(milliseconds=100)
SPECIAL = THREE_COMPONENT_EVENTS_DIR / "special"

_FILES = [
    pytest.param(label, site, channel, id=f"{label}-{site.key}.{channel}")
    for label, spec in EVENTS.items()
    for site in spec.sites
    for channel in site.channels
]


def _path(label: str, key: str, channel: str) -> Path:
    return THREE_COMPONENT_EVENTS_DIR / label / f"{key}.{channel}"


@pytest.mark.parametrize("label", sorted(EVENTS))
def test_every_selected_file_is_shipped(label: str) -> None:
    shipped = {
        f"{key}.{channel}"
        for key, channels in _sites(THREE_COMPONENT_EVENTS_DIR / label).items()
        for channel in channels
    }
    selected = {
        f"{site.key}.{channel}"
        for site in EVENTS[label].sites
        for channel in site.channels
    }
    assert shipped == selected


@pytest.mark.parametrize(("label", "site", "channel"), _FILES)
def test_picks_are_on_their_channels(label: str, site: Site, channel: str) -> None:
    sac = SAC.from_file(_path(label, site.key, channel))
    phases = phases_on_channel(EVENTS[label].phases, channel)
    for phase, header in PICK_HEADERS.items():
        time = getattr(sac.timestamps, header)
        if phase in phases:
            pinned = pd.Timestamp(PINNED_ARRIVALS[label][site.key][phase])
            assert abs(time - pinned) < TOLERANCE
            assert getattr(sac.native, f"k{header}").strip() == phase
        else:
            assert time is None


@pytest.mark.parametrize(("label", "site", "channel"), _FILES)
def test_sampling_and_orientation(label: str, site: Site, channel: str) -> None:
    sac = SAC.from_file(_path(label, site.key, channel))
    if site.resample:
        assert sac.seismogram.delta == DELTA
    expected_dip = 0.0 if is_horizontal(channel) else -90.0
    assert sac.orientation.dip == pytest.approx(expected_dip)


def test_orientation_differs_between_events() -> None:
    fiji = SAC.from_file(_path("fiji_region", "AK.GRNC.--", "BHN"))
    solomon = SAC.from_file(_path("solomon_islands", "AK.GRNC.--", "BHN"))
    assert fiji.orientation.azimuth != solomon.orientation.azimuth


_PINNED = [
    pytest.param(label, key, phase, id=f"{label}-{key}-{phase}")
    for label, sites in PINNED_ARRIVALS.items()
    for key, values in sites.items()
    for phase in values
    if phase in PHASE_BACKENDS
]


@pytest.mark.parametrize(("label", "key", "phase"), _PINNED)
def test_pinned_arrival_tracks_its_backend(label: str, key: str, phase: str) -> None:
    if phase in ("pP", "SKS"):
        pytest.importorskip("obspy")
    pinned_event = PINNED_EVENTS[label]
    event = MiniEvent(
        latitude=float(pinned_event["latitude"]),
        longitude=float(pinned_event["longitude"]),
        depth=float(pinned_event["depth"]),
        time=pd.Timestamp(pinned_event["time"]),
    )
    site = PINNED_ARRIVALS[label][key]
    location = MiniLocation(
        latitude=float(site["latitude"]), longitude=float(site["longitude"])
    )
    fresh = PHASE_BACKENDS[phase](
        depth=event.depth, distance=haversine(event, location), phases=[phase]
    )
    assert abs(event.time + fresh[phase] - pd.Timestamp(site[phase])) < TOLERANCE


def test_missing_orientation() -> None:
    label, key = MISSING_ORIENTATION
    for path in _sites(SPECIAL / "missing_orientation")[key].values():
        sac = SAC.from_file(path)
        assert sac.native.cmpaz is None
        assert sac.native.cmpinc is None


def test_p_on_all_channels() -> None:
    _, key = P_ON_ALL_CHANNELS
    files = _sites(SPECIAL / "p_on_all_channels")[key]
    picks = {SAC.from_file(path).timestamps.t0 for path in files.values()}
    assert len(files) == 3
    assert len(picks) == 1
    assert None not in picks


def test_rotated_as_bhn() -> None:
    label, key = ROTATED_AS_BHN
    rotated = SAC.from_file(_sites(SPECIAL / "rotated_as_bhn")[key]["BHN"])
    shipped = SAC.from_file(_path(label, key, "BHN"))
    assert rotated.station.channel == shipped.station.channel == "BHN"
    assert rotated.orientation.azimuth != pytest.approx(shipped.orientation.azimuth)


@pytest.mark.parametrize("key", sorted(_sites(SPECIAL / "reference_rt")))
def test_reference_rt_agrees_with_pysmo(key: str) -> None:
    shipped = {
        channel: SAC.from_file(path)
        for channel, path in _sites(THREE_COMPONENT_EVENTS_DIR / "central_peru")[
            key
        ].items()
        if is_horizontal(channel)
    }
    first = next(iter(shipped.values()))
    components = Components(
        [(sac.seismogram, sac.orientation) for sac in shipped.values()]
    )
    r, t = rotate_to_rt(components, backazimuth(first.event, first.station))
    reference = _sites(SPECIAL / "reference_rt")[key]
    for computed, name in ((r, "R"), (t, "T")):
        expected = SAC.from_file(reference[first.station.channel[:2] + name])
        scale = np.max(np.abs(expected.seismogram.data))
        np.testing.assert_allclose(
            computed.data, expected.seismogram.data, atol=1e-4 * scale
        )


def test_multiplexed() -> None:
    files = next(iter(_sites(SPECIAL / "multiplexed").values()))
    segments = MSeed.all_from_file(files["mseed"])
    assert len({segment.channel for segment in segments}) == 3
    assert files["xml"].read_bytes().count(b"<Channel ") == 3


def test_gappy() -> None:
    files = next(iter(_sites(SPECIAL / "gappy").values()))
    channels = [segment.channel for segment in MSeed.all_from_file(files["mseed"])]
    assert len(channels) > len(set(channels))


PREPARED = THREE_COMPONENT_EVENTS_DIR / "prepared"
_ROTATED = {"fiji_region": "T", "solomon_islands": "T", "central_peru": "LQT"}


@pytest.mark.parametrize("label", sorted(EVENTS))
def test_prepared_channels(label: str) -> None:
    """Each band of a site is Z plus T, or Z plus L, Q and T."""
    shipped = _sites(THREE_COMPONENT_EVENTS_DIR / label)
    prepared = _sites(PREPARED / label)
    assert prepared.keys() == shipped.keys()
    for key, channels in shipped.items():
        bands = {channel[:2] for channel in channels}
        expected = {band + c for band in bands for c in "Z" + _ROTATED[label]}
        assert set(prepared[key]) == expected, key


@pytest.mark.parametrize("label", sorted(EVENTS))
def test_prepared_picks_on_every_channel(label: str) -> None:
    """Every pick of a site is on every prepared channel of the site."""
    for key, channels in _sites(PREPARED / label).items():
        for channel, path in channels.items():
            sac = SAC.from_file(path)
            for phase in EVENTS[label].phases:
                header = PICK_HEADERS[phase]
                time = getattr(sac.timestamps, header)
                pinned = pd.Timestamp(PINNED_ARRIVALS[label][key][phase])
                assert abs(time - pinned) < pd.Timedelta(milliseconds=1), (
                    f"{key}.{channel}: {phase}"
                )
                assert getattr(sac.native, f"k{header}").strip() == phase


@pytest.mark.parametrize("key", sorted(_sites(PREPARED / "central_peru")))
def test_prepared_q_is_rotated_from_z_and_r(key: str) -> None:
    """Q = -Z sin(i) + R cos(i), with R from the shipped horizontals and i from Q's dip."""
    shipped = {
        channel: SAC.from_file(path)
        for channel, path in _sites(THREE_COMPONENT_EVENTS_DIR / "central_peru")[
            key
        ].items()
    }
    vertical = next(sac for c, sac in shipped.items() if not is_horizontal(c))
    baz = backazimuth(vertical.event, vertical.station)
    radial = sum(
        np.asarray(sac.seismogram.data)
        * np.cos(np.radians(sac.orientation.azimuth - (baz + 180)))
        for c, sac in shipped.items()
        if is_horizontal(c)
    )
    prepared = _sites(PREPARED / "central_peru")[key]
    q = SAC.from_file(prepared[vertical.station.channel[:2] + "Q"])
    incidence = np.radians(q.orientation.dip)
    z = np.asarray(vertical.seismogram.data)
    expected = -z * np.sin(incidence) + radial * np.cos(incidence)
    assert q.orientation.azimuth == pytest.approx((baz + 180) % 360, abs=1e-3)
    np.testing.assert_allclose(
        q.seismogram.data, expected, atol=1e-4 * np.max(np.abs(expected))
    )
