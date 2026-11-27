"""Pytest fixtures shared across the pysmo and aimbat test suites.

Registered as a pytest plugin via the ``pytest11`` entry point, so any project
with ``testkit`` installed picks these up automatically — no ``conftest.py``
import required.
"""

from pathlib import Path

import pytest

REFERENCE_EVENT_DIR = Path(__file__).parent / "assets" / "reference_event"
"""Directory of a real IU.ANMO event recording (SAC, mseed, GeoCSV, SACPZ, StationXML, QuakeML).

See ``PROVENANCE.md`` in that directory for how the data was fetched.
"""

ICCS_EVENTS_DIR = Path(__file__).parent / "assets" / "iccs_events"
"""Directory of a 3-event Alaska teleseismic array (SAC BHZ, response removed).

See ``PROVENANCE.md`` in that directory for the event/station list and how
the data was fetched and curated.
"""

MULTI_PHASE_EVENTS_DIR = Path(__file__).parent / "assets" / "multi_phase_events"
"""Directory of a deep event with labelled P and pP picks (SAC BHZ, response removed).

See ``PROVENANCE.md`` in that directory for the event, stations and picks.
"""

THREE_COMPONENT_EVENTS_DIR = Path(__file__).parent / "assets" / "three_component_events"
"""Directory of three events on three components, plus files with one property each.

See ``PROVENANCE.md`` in that directory for the events, sites, picks and
the files under ``special/``.
"""


def _sites(directory: Path) -> dict[str, dict[str, Path]]:
    """Files in `directory` keyed by ``NETWORK.STATION.LOCATION``, then by suffix."""
    sites: dict[str, dict[str, Path]] = {}
    for path in sorted(p for p in directory.iterdir() if p.is_file()):
        key, suffix = path.name.rsplit(".", 1)
        sites.setdefault(key, {})[suffix] = path
    return sites


@pytest.fixture()
def reference_event_assets() -> dict[str, Path]:
    """Paths to the reference event's seismogram/metadata files, keyed by format."""
    return {
        "sac_bhz": REFERENCE_EVENT_DIR / "iu_anmo_00_bhz.sac",
        "sac_lhz": REFERENCE_EVENT_DIR / "iu_anmo_00_lhz.sac",
        "mseed_bhz": REFERENCE_EVENT_DIR / "iu_anmo_00_bhz.mseed",
        "mseed_lhz": REFERENCE_EVENT_DIR / "iu_anmo_00_lhz.mseed",
        "geocsv_bhz": REFERENCE_EVENT_DIR / "iu_anmo_00_bhz.geocsv",
        "geocsv_lhz": REFERENCE_EVENT_DIR / "iu_anmo_00_lhz.geocsv",
        "sacpz_bhz": REFERENCE_EVENT_DIR / "iu_anmo_00_bhz.pz",
        "sacpz_lhz": REFERENCE_EVENT_DIR / "iu_anmo_00_lhz.pz",
        "stationxml_bhz": REFERENCE_EVENT_DIR / "iu_anmo_00_bhz_response.xml",
        "stationxml_lhz": REFERENCE_EVENT_DIR / "iu_anmo_00_lhz_response.xml",
        "quakeml": REFERENCE_EVENT_DIR / "maule_2010.quakeml",
    }


@pytest.fixture()
def iccs_events_assets() -> dict[str, dict[str, Path]]:
    """Paths to the ICCS/MCCC array fixture's SAC seismograms.

    Keyed by event label, then by ``NETWORK.STATION``.
    """
    return {
        event_dir.name: {
            ".".join(sac_file.name.split(".")[:2]): sac_file
            for sac_file in sorted(event_dir.glob("*.BHZ"))
        }
        for event_dir in sorted(ICCS_EVENTS_DIR.iterdir())
        if event_dir.is_dir()
    }


@pytest.fixture()
def multi_phase_events_assets() -> dict[str, dict[str, Path]]:
    """Paths to the multi-phase fixture's SAC seismograms.

    Keyed by event label, then by ``NETWORK.STATION``. Each file has a P
    pick in ``t0`` labelled ``kt0 = "P"``, and most have a pP pick in
    ``t5`` labelled ``kt5 = "pP"``.
    """
    return {
        event_dir.name: {
            ".".join(sac_file.name.split(".")[:2]): sac_file
            for sac_file in sorted(event_dir.glob("*.BHZ"))
        }
        for event_dir in sorted(MULTI_PHASE_EVENTS_DIR.iterdir())
        if event_dir.is_dir()
    }


@pytest.fixture()
def three_component_events_assets() -> dict[str, dict[str, dict[str, dict[str, Path]]]]:
    """Paths to the three-component fixture's files.

    ``"events"`` and ``"prepared"`` are keyed by event label, ``"special"``
    by the property its files have (``"missing_orientation"``,
    ``"p_on_all_channels"``, ``"rotated_as_bhn"``, ``"reference_rt"``,
    ``"multiplexed"``, ``"gappy"``). ``"prepared"`` holds the same sites as
    ``"events"`` with the horizontals rotated (Z and T, or Z, L, Q and T)
    and every pick of a site on every channel. Below that, all are keyed by
    ``NETWORK.STATION.LOCATION`` and then by channel code (``"BHZ"``) or,
    for miniSEED and StationXML, by file suffix (``"mseed"``, ``"xml"``).
    """
    return {
        group: {
            directory.name: _sites(directory)
            for directory in sorted(root.iterdir())
            if directory.is_dir() and directory.name not in {"special", "prepared"}
        }
        for group, root in (
            ("events", THREE_COMPONENT_EVENTS_DIR),
            ("special", THREE_COMPONENT_EVENTS_DIR / "special"),
            ("prepared", THREE_COMPONENT_EVENTS_DIR / "prepared"),
        )
    }
