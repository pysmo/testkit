# Three-component fixture: orientation, several channels per station, rotation

Three teleseismic events recorded on three components by Alaska broadband
stations, a `special/` directory of files that each have one property a
test needs, and a `prepared/` copy of the events rotated to Z/T and
Z/L/Q/T with every pick on every channel. It serves tests of orientation,
several channels and location codes at one station, mixed sampling rates,
rotation to R/T and L/Q/T, miniSEED with several channels or a gap,
choosing a phase's channels, and the checks that refuse ambiguous data.

Fetched by `scripts/three_component_events/fetch_three_component_events.py`
from the pinned table in `three_component_arrivals.py`, written by
`pin_three_component_arrivals.py`. Most sites are also in
`aimbat-sampledata` and are processed the same way, but the two are
fetched independently.

## Events

| Label | USGS eventid | Origin time (UTC) | Depth | Mag | Phases | Sites |
|---|---|---|---|---|---|---|
| `fiji_region` | [usc000stdc](https://earthquake.usgs.gov/earthquakes/eventpage/usc000stdc) | 2014-11-01T18:57:22.380Z | 434 km | 7.1 | P, pP, S | 12 |
| `central_peru` | [usb000s5x1](https://earthquake.usgs.gov/earthquakes/eventpage/usb000s5x1) | 2014-08-24T23:21:45.520Z | 101 km | 6.8 | SKS | 9 |
| `solomon_islands` | [usc000phx5](https://earthquake.usgs.gov/earthquakes/eventpage/usc000phx5) | 2014-04-12T20:14:39.300Z | 22.6 km | 7.6 | P, S | 1 |

`central_peru` is 88 to 108 deg from the sites, mostly in the core shadow,
so it has SKS but no P. `solomon_islands` holds one site, `AK.GRNC`, whose
horizontals point 16 and 106 deg there and 0 and 90 deg at `fiji_region`:
one stream whose orientation depends on the event.

## Sites and channels

The sites are in `three_component_selection.py`. Files are named
`NETWORK.STATION.LOCATION.CHANNEL`.

- **As in `aimbat-sampledata`** (BHZ/BHN/BHE, location `--`, response
  removed, low-passed at 8 Hz and resampled to 20 Hz): `AK.BAL`, `AK.CCB`,
  `AK.CHI` (Fiji only), `AK.CHUM` (Peru only), `AK.GRNC` (Fiji, Solomon
  Islands), `AK.KNK`, `AK.PAX`, `AV.AKRB`, `TA.POKR`, `TA.TOLK`.
  `AK.CCB`'s BHN and BHE point 6 and 96 deg.
- **Kept at their native rate**, response removed:
    - `IU.COLA.00` BHZ/BH1/BH2 at 20 Hz, horizontals at 51 and 141 deg
      (Fiji, Peru);
    - `IU.COLA.10` BHZ/BH1/BH2 at 40 Hz, horizontals at 1 and 91 deg
      (Fiji): two location codes at one station, at different rates;
    - `AK.PAX.--` LHZ/LHN/LHE at 1 Hz (Fiji), beside its BH channels.
- **`TA.TOLK.01`** BHZ/BHN/BHE (Fiji), resampled like the sample sites,
  beside `TA.TOLK.--`: two location codes at one station.

`IU.COLA.10` HH (100 Hz) was tried and left out: its data end early at
Fiji and are missing at Peru.

Each channel's azimuth and dip come from its StationXML epoch at the event
and are written through pysmo's `SAC.orientation` (`cmpaz`, `cmpinc`).

## Windows and picks

From 2 min before the first pinned arrival to 3 min after the last, shared
by every channel of a site. Picks are the pinned arrivals (iasp91), on the
channels each phase is measured on:

| Phase | Header | Label | Channels | Backend |
|---|---|---|---|---|
| P | `t0` | `kt0 = "P"` | Z | pysmo |
| pP | `t5` | `kt5 = "pP"` | Z | ObsPy TauP |
| S | `t6` | `kt6 = "S"` | horizontals | pysmo |
| SKS | `t7` | `kt7 = "SKS"` | horizontals | ObsPy TauP |

S and SKS are on both horizontals, as the station's arrival time, for the
rotated components to take over. `t1` to `t3` stay free for AIMBAT v1.
Files are SAC v7, so `o` and the picks keep double precision.

## `special/`

| Directory | Files | Property |
|---|---|---|
| `missing_orientation` | `AK.BAL.--` at Fiji | `cmpaz`/`cmpinc` cleared |
| `p_on_all_channels` | `AK.KNK.--` at Fiji | the P pick also on BHN and BHE |
| `rotated_as_bhn` | `TA.POKR.--.BHN` at Peru | the reference R, labelled as the site's BHN: a second source for that stream |
| `reference_rt` | every Peru site | R (`??R`) and T (`??T`) |
| `multiplexed` | `AK.PAX.--` at Fiji | raw counts, BHZ/BHN/BHE in one miniSEED file, with their StationXML (`.xml`) |
| `gappy` | `AK.KNK.--` at `nepal` (2015-04-25) | raw counts, BHZ/BHN/BHE, each in two segments with a 10 s gap at 06:33:59 |

Files in `special/` repeat streams of the event directories, so a test
that ingests both sees second sources for the same streams.

The miniSEED files are the EarthScope dataselect replies as served, in
counts. The gap is real: `AK.KNK` has it at all three channels.

`reference_rt` is computed by direct projection, independently of pysmo's
rotation code, so it can check it: each horizontal contributes its data
times the cosine of the angle between its azimuth (from its header) and the
target's. R points away from the source (back azimuth + 180 deg), T 90 deg
clockwise from R. This handles horizontals that are not at 0 and 90 deg
(`AK.CCB`, `IU.COLA.00`). `tests/test_three_component_events.py` checks it
against `pysmo.tools.components.rotate_to_rt`.

## `prepared/`

The event directories' sites again, as data are commonly prepared before
ingestion: the horizontals rotated with pysmo, and every pick of a site on
every channel of the site. Written from the shipped files by
`prepare_three_component_events.py`, with no download.

| Event | Channels of each band |
|---|---|
| `fiji_region`, `solomon_islands` | Z and T (`rotate_to_rt`) |
| `central_peru` | Z, L, Q and T (`rotate_to_lqt`) |

Each band of a site (BH, and LH at `AK.PAX`) is rotated on its own, from
its Z and its two horizontals (N/E or 1/2) with their own orientations, at
the back azimuth from the site to the event. The SKS incidence angle comes
from ObsPy's TauP (iasp91, at the receiver, not corrected for the free
surface). A rotated file is a copy of the band's Z with the rotated data,
channel code and orientation: T at the back azimuth + 270 deg, dip 0; L
and Q at the back azimuth + 180 deg, dips `incidence - 90` and
`incidence`. `tests/test_three_component_events.py` checks the channels,
the picks and Q against `-Z sin(i) + R cos(i)`.

## Regenerating

```sh
cd scripts/three_component_events
uv run --group fetch python pin_three_component_arrivals.py  # only to re-cut
uv run ruff format three_component_arrivals.py
uv run python fetch_three_component_events.py
uv run --group fetch python prepare_three_component_events.py
```

`fetch_three_component_events.py` removes every subdirectory, `prepared/`
included, so `prepare_three_component_events.py` runs after it.

Pinning needs the `fetch` group (ObsPy's TauP for pP and SKS); fetching
does not. `tests/test_three_component_events.py` checks that every selected
file is shipped, the picks and their channels, the sampling and
orientation, the `special/` properties, and that each pinned arrival still
agrees with its backend within 100 ms (pP and SKS only with ObsPy).

## Licence / attribution

- **`AK`**: Alaska Earthquake Center, University of Alaska Fairbanks.
- **`AV`**: Alaska Volcano Observatory, USGS and University of Alaska
  Fairbanks Geophysical Institute.
- **`TA`**: USArray Transportable Array, NSF-funded EarthScope/IRIS.
- **`IU`**: Global Seismograph Network (GSN, IRIS/USGS).

Waveforms and station metadata from `service.earthscope.org`. Event
parameters from the USGS FDSN event service.
