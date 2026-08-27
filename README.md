# testkit

Shared pytest fixtures and test assets for the [pysmo](https://github.com/pysmo/pysmo) and
[aimbat](https://github.com/pysmo/aimbat) test suites.

## Installation

This package is not published to PyPI. Install it directly from GitHub, pinned to a tag:

```bash
uv add "testkit @ git+https://github.com/pysmo/testkit@v0.1.0"
```

## Usage

Fixtures are registered as a pytest plugin (via the `pytest11` entry point), so
installing `testkit` is enough — no `conftest.py` import required. Request them
as ordinary fixture parameters; there are no importable path constants, only
fixtures:

```python
from pathlib import Path


def test_something(reference_event_assets: dict[str, Path]) -> None:
    sac_file = reference_event_assets["sac_bhz"]
    ...


def test_array_alignment(iccs_events_assets: dict[str, dict[str, Path]]) -> None:
    komandorskiye = iccs_events_assets["komandorskiye_ostrova"]
    sac_file = komandorskiye["AK.BWN"]
    ...
```

Available fixtures:

- **`reference_event_assets`** — `dict[str, Path]` keyed by format (e.g.
  `"sac_bhz"`, `"stationxml_lhz"`, `"quakeml"`). A single real event/station
  recording (IU.ANMO, 2010-02-27 Maule, Chile) in every format EarthScope
  offers, plus the event-level QuakeML (`"quakeml"`, one file, not
  per-channel) from USGS `fdsnws-event`. See
  `src/testkit/assets/reference_event/PROVENANCE.md`.
- **`iccs_events_assets`** — `dict[str, dict[str, Path]]` keyed by event label
  (`"solomon_islands"`, `"komandorskiye_ostrova"`, `"iraq"`) then by
  `NETWORK.STATION`. A 3-event Alaska teleseismic array (SAC BHZ, response
  already removed) for `pysmo.tools.iccs`/AIMBAT array-alignment tests. See
  `src/testkit/assets/iccs_events/PROVENANCE.md`.

## Development

Dependencies are managed with [uv](https://docs.astral.sh/uv/).

```bash
make sync   # install deps
make lint   # ruff check + format --check
make mypy   # type check
make tests  # run the test suite
```
