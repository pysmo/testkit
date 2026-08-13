"""Pytest fixtures shared across the pysmo and aimbat test suites.

Registered as a pytest plugin via the ``pytest11`` entry point, so any project
with ``testkit`` installed picks these up automatically — no ``conftest.py``
import required.
"""

from pathlib import Path

import pytest

REFERENCE_EVENT_DIR = Path(__file__).parent / "assets" / "reference_event"
"""Directory of a real IU.ANMO event recording (SAC, mseed, GeoCSV, SACPZ, StationXML).

See ``PROVENANCE.md`` in that directory for how the data was fetched.
"""


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
    }
