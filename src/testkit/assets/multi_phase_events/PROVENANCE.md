# Multi-phase fixture: one deep event with P and pP

A deep teleseismic event recorded by Alaska broadband stations (`AK`, `AV`
and `TA` networks, BHZ only), with labelled initial picks for two phases,
P and pP. It serves tests of processing several phases of one event: two
phases with different seismograms, each aligned on its own.

## Event

| Label | USGS eventid | Origin time (UTC) | Location | Depth | Mag | Stations |
|---|---|---|---|---|---|---|
| `fiji_region` | [usc000stdc](https://earthquake.usgs.gov/earthquakes/eventpage/usc000stdc) | 2014-11-01T18:57:22.380Z | Fiji region | 434 km | 7.1 | 14 |

At 434 km depth, pP arrives 94 to 99 s after P at these distances (72 to
90 deg), well clear of P, and sP about 45 s after pP. The stations are a
subset of the `aimbat-sampledata` Fiji stations, spread over the distance
range. The list is in `scripts/multi_phase_events/selection.py`.

## Picks

| Phase | Header | Label | Stations |
|---|---|---|---|
| P | `t0` | `kt0 = "P"` | all 14 |
| pP | `t5` | `kt5 = "pP"` | all but `AV.AKRB` |

`t5` is clear of the `t1` to `t3` that AIMBAT v1 writes. `AV.AKRB` has the
weakest P of the set, and MCCC cycle-skips its pP by about 6 s, so it has
no pP pick. The two phases therefore differ in their seismograms.

The picks are predicted arrivals in the iasp91 model, pinned in
`scripts/multi_phase_events/pinned_arrivals.py`. P comes from pysmo's
built-in solver. pP comes from ObsPy's TauP, since pysmo's solver does not
cover depth phases. `traveltime_backends.py` names the backend for each
phase. `tests/test_multi_phase_events.py` checks that each pinned arrival
still agrees with its backend within 100 ms. The pP check runs only with
ObsPy installed.

In AIMBAT, ICCS and MCCC align both phases from these picks: after MCCC,
the median MCCC CC is about 0.7 for each phase.

## Window and processing

- Window: pinned P minus 2 minutes to pinned P plus 3 minutes.
- Instrument response removed (`remove_response`, `pre_filt` from the
  StationXML response). SAC `idep` set to match.
- SAC `nvhdr = 7`, for double-precision `o` and `t` headers.
- `evla`, `evlo`, `evdp` and `o` from the USGS event catalogue.

## Files

```
multi_phase_events/
  fiji_region/
    AK.ATKA.--.BHZ
    ...
```

One subdirectory per event, named by label, with `NETWORK.STATION.--.BHZ`
SAC files. The `multi_phase_events_assets` fixture finds them by globbing,
keyed by event label, then by `NETWORK.STATION`.

## Regenerating

From `scripts/multi_phase_events`:

```sh
uv run python fetch_multi_phase_events.py
```

This reads the pinned arrivals and needs no ObsPy. Re-pinning them, only
for a deliberate change of stations, phases or backends, needs the
`fetch` dependency group:

```sh
uv run --group fetch python pin_arrivals.py
```

## Licence and attribution

`AK`, `AV` and `TA` are public seismic networks. Data are served by
`service.earthscope.org` (formerly IRIS DMC). Event parameters are public
USGS earthquake-catalogue information.
