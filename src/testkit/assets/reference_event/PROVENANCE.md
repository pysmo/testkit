# Reference event: 2010-02-27 Maule, Chile

pysmo's primary test fixture identity, replacing the previously undocumented
`testfile.sac`. Chosen because it was already the de facto reference event in
three existing live-network tests (`tests/tools/test_web_live.py`,
`tests/integration/test_response_removal_live.py`,
`tests/lib/io/test_sacio.py`), rather than picking a new one.

- **Event**: 2010-02-27 Maule, Chile earthquake, M8.8. Origin lat `-36.122`,
  lon `-72.898`, depth `22900.0` m, origin time `2010-02-27T06:34:11.53Z`.
- **Station**: `IU.ANMO.00` (Albuquerque Seismological Laboratory), channels
  `BHZ` and `LHZ`. lat `34.945981`, lon `-106.457133`. Network `IU` is part
  of the Global Seismographic Network (USGS/EarthScope/NSF); its
  `restrictedStatus` is `open`.
- **Window**: `2010-02-27T06:44:06.04Z` to `2010-02-27T07:31:59.31Z`
  (~47.9 minutes, 57465 samples for BHZ at 20 Hz). **Pinned**, not
  recomputed: `fetch_reference_event.py` hardwires both timestamps
  (`STARTTIME`/`ENDTIME`) so the bundle regenerates deterministically. The
  derivation of each end, recorded for history:
  - **Start**: predicted P arrival minus 2 minutes. The predicted P came
    from EarthScope's `irisws-traveltime` service (retired 2026; the bundle
    was first cut against it): P ≈ 714.51 s after origin at this 77.638°
    epicentral distance / 22.9 km depth geometry, i.e.
    `2010-02-27T06:46:06.04Z`, matching `test_response_removal_live.py`'s
    convention. pysmo's in-house `travel_times()` now predicts the same
    arrival to ~1 ms; `tests/test_traveltime_windows.py` checks the pinned
    start still agrees with it within 100 ms.
  - **End**: origin time + (epicentral distance in km / 3.0 km/s) + 10
    minutes. An initial, phase-relative-only window (P − 2 min to P + 15
    min) was tried first and found inadequate: it ended before the S
    arrival had fully passed and long before surface waves — for a
    shallow (22.9 km) M8.8, often the largest-amplitude phase of the whole
    recording — which arrive tens of minutes after P, not tens of seconds.
    3.0 km/s is a conservative (slow) bound on the fundamental-mode
    Rayleigh/Love dispersion train's group velocity, chosen to cover the
    full dispersed wave train rather than just its fast onset; +10 minutes
    gives some coda after that. There is no single agreed rule for exactly
    how much margin is "enough" — this is a deliberate, documented choice,
    not a universal formula.

## Files

Every format EarthScope offers for this station/window, for both channels,
fetched as raw bytes/text — never parsed and re-serialised through pysmo's
own classes (see `fetch_reference_event.py`'s docstring for why):

- `iu_anmo_00_{bhz,lhz}.sac`
- `iu_anmo_00_{bhz,lhz}.mseed`
- `iu_anmo_00_{bhz,lhz}.geocsv`
- `iu_anmo_00_{bhz,lhz}_response.xml` (StationXML, `level=response`)
- `iu_anmo_00_{bhz,lhz}.pz` (SAC PZ)
- `maule_2010.quakeml` (QuakeML 1.2, `fdsnws-event`, `format=xml`) — event
  metadata is not per-channel, so this is **one file for the whole bundle**,
  not an `iu_anmo_00_{bhz,lhz}` pair. Fetched from USGS, not EarthScope (see
  below).

`iu_anmo_00_bhz.sac` is the canonical fixture used throughout the test
suite (replacing `testfile.sac`). The LHZ set and non-SAC BHZ formats exist
for future-proofing (e.g. a future miniSEED reader) and multi-channel
StationXML coverage. `maule_2010.quakeml` exists for pysmo's QuakeML parser
tests and the "project as code" doctest.

## Event metadata (QuakeML)

`maule_2010.quakeml` is the `fdsnws-event` QuakeML 1.2 document for the
Maule mainshock, fetched from USGS
(`https://earthquake.usgs.gov/fdsnws/event/1/query`), **not** EarthScope:
EarthScope decommissioned its own event service
(`service.earthscope.org/fdsnws/event` now returns HTTP 410 Gone), and USGS
is the authoritative source for this event's `official` ANSS catalogue
entry — the same catalogue already cited for the `iccs_events` bundle.

The query is a **time-box + magnitude filter, not an event id**:

```
starttime=2010-02-27T06:00:00  endtime=2010-02-27T07:00:00  minmagnitude=8.5
format=xml  includeallorigins=false  includeallmagnitudes=false
includearrivals=false  nodata=404
```

QuakeML `publicID`s are not canonical across catalogues (USGS, ISC, EMSC
each issue a different one for this same earthquake), so a reproducible
box query is used instead. The 06:00–07:00 UTC window with
`minmagnitude=8.5` isolates the Maule mainshock alone — no aftershock in
that hour is anywhere near M8.5.

- **One `<event>` in the document** (verified: `grep -c '<event ' maule_2010.quakeml` → 1).
- **`publicID`** (informational only — pysmo tests must not assert its exact
  value): `quakeml:earthquake.usgs.gov/fdsnws/event/1/query?eventid=official20100227063411530_30&format=quakeml`
- **Fetched values** (preferred origin / magnitude): origin time
  `2010-02-27T06:34:11.530Z`, latitude `-36.122`, longitude `-72.898`,
  depth `22900` m (QuakeML `<depth>` is metres; `<uncertainty>` `9200`),
  magnitude `8.8` type `mww`, event type `earthquake`, description
  "2010 Maule, Chile Earthquake".

These origin/location/depth/magnitude values are public earthquake-catalogue
data, already used verbatim elsewhere in this bundle (the `EVENT =
MiniEvent(...)` block in `fetch_reference_event.py`, and the event summary
above). The document also carries `<creationInfo><creationTime>` stamps that
change on each fetch, so the file is not byte-identical across regenerations.

## Regenerating

```sh
cd scripts/reference_event
python fetch_reference_event.py
. ./annotate_event_metadata.sh
```

Both scripts live in `scripts/reference_event/` (outside `src/`, since they
depend on `pysmo` to do the fetching/annotating, and the installable
package and its fixtures must not depend on pysmo) but write into this
directory. The fetch window is pinned in the script (`STARTTIME`/`ENDTIME`)
rather than derived from a travel-time call, so regeneration needs no
travel-time service or solver.

`fetch_reference_event.py` downloads the waveform/response formats from
`service.earthscope.org` and `maule_2010.quakeml` from
`earthquake.usgs.gov` (one call, outside the per-channel loop). The QuakeML
needs no annotation step — unlike the SAC files below. FDSN dataselect has
no concept of an earthquake event, so the two `.sac` files come back with
no `evla`/`evlo`/`evdp`/`o` header set. `annotate_event_metadata.sh` adds
them afterwards using real
SAC's `ch` command (not pysmo's own writer — this keeps the annotation an
externally-produced edit rather than round-tripping through the exact code
these fixtures are meant to help validate), using the catalogue values
above. It only sets `evla`/`evlo`/`evdp`/`o`; the reference time
(`nzyear`/.../`b`) is left exactly as fetched (the true data start time),
so `o` is computed relative to that reference rather than moving it:
`o = -594.539` seconds (origin time minus the fetched reference time).

Note `iztype` is deliberately left as `unkn` (its default), not set to
`o`. Setting `iztype = "o"` is SAC's convention for declaring the
reference time *itself* to be the event origin — which is not what's
happening here (the reference time stays the true data start time; `o` is
just an ordinary offset from it). This has a real behavioural consequence
in pysmo: `SacEvent.time` can be freely reassigned on these files
(`sac.event.time = ...` works normally), unlike a file with `iztype ==
"o"`, where pysmo's `SacIO` locks `o` at `0` and raises `RuntimeError` on
any attempt to change it (see `tests/lib/io/test_sacio.py`'s
`test_iztype_prevents_zero_time_change`, which now constructs its own
minimal `SacIO()` for that specific case rather than relying on this
fixture, since this fixture no longer exercises it).

Requires a local SAC installation (`SACHOME`/`SACAUX`/`PATH` set per SAC's
own `sacinit.sh`) for the annotation step only.

## Licence / attribution

Network `IU` is part of the Global Seismographic Network, operated jointly
by the USGS, IRIS/EarthScope, and the NSF; its StationXML `restrictedStatus`
is `open` (verified for this station/epoch when the bundle was fetched —
re-check if regenerating far in the future, in case network policy
changes). Data served via `service.earthscope.org` (formerly IRIS DMC).
Event parameters (origin time/location/depth/magnitude) are public
earthquake-catalogue information for the 2010-02-27 Maule, Chile
earthquake, not derived from any single proprietary source.
