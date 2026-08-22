# ICCS/MCCC array fixture: 3 Alaska teleseismic events

Shared fixture for `pysmo.tools.iccs` and AIMBAT's ICCS → QC → MCCC
workflow tests — a small teleseismic array (`AK`/`AV`/`TA` networks,
BHZ-only) recorded across three separate earthquakes, with real station
overlap between events (so alignment/MCCC exercises can compare the same
station across events, not just within one).

## Provenance chain

This dataset did **not** originate here. It went through several stages,
each in a different repo:

1. An earlier stage fetched 10 candidate teleseismic events (USGS event
   catalogue + EarthScope waveforms/response), intersected station
   availability across all of them, and spread ~40 shared stations by
   latitude — so most stations have multi-event coverage.
2. Reviewed inside **AIMBAT**: narrowed 10 events → 5, then 5 → 3, and
   within each of the surviving 3 events, deselected (not deleted)
   individual seismograms during manual QC. This selection lives in an
   AIMBAT project database (`aimbat.db`).
3. **Extracted here**: the final (event, station) selection was read back
   out of that `aimbat.db` (`aimbatseismogramparameters."select"`, joined
   through to `aimbatdatasource.sourcename`), then **`fetch_iccs_events.py`
   independently re-fetches** every file directly from USGS + EarthScope by
   event ID and station code — it does not read any files from the earlier
   stage. That stage was only ever the source of the *selection* (which
   events, which stations); this package has no runtime or regeneration
   dependency on it.

The two events considered in the earlier 5-event shortlist but
**not** carried forward here are `fiji_region` and `nepal` — dropped in
the 5→3 AIMBAT review (not defective, just not chosen). Notably
`fiji_region` was the *old* `derive_fixture.py` source for pysmo's
previous ICCS fixture (see below) — that coupling is now fully retired.

## Events

| Label | USGS eventid | Origin time (UTC) | Location | Depth | Mag | Selected stations |
|---|---|---|---|---|---|---|
| `solomon_islands` | [usc000phx5](https://earthquake.usgs.gov/earthquakes/eventpage/usc000phx5) | 2014-04-12T20:14:39.300Z | Kirakira, Solomon Islands | 22.6 km | 7.6 | 16 |
| `komandorskiye_ostrova` | [us20009x42](https://earthquake.usgs.gov/earthquakes/eventpage/us20009x42) | 2017-07-17T23:34:13.740Z | Commander Islands, Russia | 10 km | 7.7 | 25 |
| `iraq` | [us2000bmcg](https://earthquake.usgs.gov/earthquakes/eventpage/us2000bmcg) | 2017-11-12T18:18:17.180Z | Halabja, Iraq | 19 km | 7.3 | 27 |

12 stations are shared across all 3 events: `AK.BWN`, `AK.CCB`, `AK.EYAK`,
`AK.FYU`, `AK.GRNC`, `AK.JIS`, `AK.KIAG`, `AK.KNK`, `AK.MCK`, `AK.PAX`,
`AK.PNL`, `TA.POKR`. Full per-event station lists (with epicentral
distance/azimuth) are in `fetch_iccs_events.py`'s `EVENT_STATIONS`/
`STATIONS` dicts — not duplicated here to avoid two sources of truth that
can drift.

All stations are within `MAX_P_DISTANCE_DEG` (~87° at most, well short of
the ~100° P-shadow zone) and single-channel BHZ, `location="--"`.

## Window and processing

Same P-coda window methodology used at the earlier stage, so re-fetching
here reproduces what was already manually QC'd in AIMBAT:

- Predicted P arrival via `haversine` (epicentral distance) +
  `fetch_travel_times`.
- Window: predicted P − 2 minutes to predicted P + 3 minutes.
- Instrument response removed (`remove_response`, StationXML-derived
  `pre_filt`); SAC `idep` set to match (`vel` for velocity, etc).
- SAC `nvhdr=7` (double-precision `o`/`t0` — v6/float32 visibly truncates
  predicted P).
- `evla`/`evlo`/`evdp`/`o` set from the (independently re-fetched) USGS
  event metadata; `t0` set to the predicted P arrival, as an initial pick
  for ICCS-style workflows.

## Files

```
iccs_events/
  solomon_islands/
    AK.ATKA.--.BHZ
    ...
  komandorskiye_ostrova/
    AK.BWN.--.BHZ
    ...
  iraq/
    AK.BWN.--.BHZ
    ...
```

One subdirectory per event (named by label, not timestamp, since there
are only 3 stable named events here), each containing
`NETWORK.STATION.--.BHZ` SAC files. No
`manifest.csv` — `iccs_events_assets`'s pytest fixture (`fixtures.py`)
discovers files by globbing each event subdirectory, keyed by event label
then `NETWORK.STATION`.

## Regenerating

```sh
cd scripts/iccs_events
python fetch_iccs_events.py
```

Lives in `scripts/iccs_events/` (outside `src/`, since it depends on
`pysmo` to do the fetching/response-removal, and this package must not
depend on `pysmo`) but writes into this directory. Unlike
`fetch_reference_event.py`, no separate annotation step is needed — event
metadata and the initial P-pick are set inline during the fetch, exactly
as they were at the earlier stage.

Re-running this script does **not** redo the AIMBAT selection — the
`EVENT_STATIONS`/`STATIONS` dicts are the frozen result of that manual QC
pass. If the selection itself ever needs to change, that has to happen in
AIMBAT again first, then be re-extracted into this script.

## Licence / attribution

`AK`/`AV`/`TA` are public seismic networks; data served via
`service.earthscope.org` (formerly IRIS DMC). Event parameters are public
USGS earthquake-catalogue information, not derived from any single
proprietary source.
