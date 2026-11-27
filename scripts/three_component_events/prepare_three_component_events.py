"""Write the prepared copy of testkit's three-component fixture.

Reads the shipped event directories (no network) and writes `prepared/`,
the same sites as data are commonly prepared for AIMBAT: the horizontals
rotated with pysmo, and every pick of a site on every channel of the site.

- `fiji_region` and `solomon_islands`: Z and T (`rotate_to_rt`).
- `central_peru`: Z, L, Q and T (`rotate_to_lqt`), with the SKS incidence
  angle at each site from ObsPy's TauP.

Each band of a site (BH, LH) is rotated on its own, from its Z and its two
horizontals (N/E or 1/2) with their own orientations. Run after
`fetch_three_component_events.py`, which removes `prepared/` with the rest:

    cd scripts/three_component_events && uv run --group fetch python prepare_three_component_events.py
"""

import copy
import shutil

from fetch_three_component_events import OUTPUT_DIR, PICK_HEADERS
from three_component_backends import incidence_angle
from three_component_selection import EVENTS, is_horizontal

from pysmo import MiniOrientation
from pysmo.classes import SAC
from pysmo.tools.azdist import backazimuth, haversine
from pysmo.tools.components import (
    Components,
    lqt_orientations,
    rotate_to_lqt,
    rotate_to_rt,
    rt_orientations,
)

PREPARED_DIR = OUTPUT_DIR / "prepared"

LQT_PHASE = {"central_peru": "SKS"}
"""Events rotated to L, Q and T, with the phase whose incidence angle is used."""


def _picks(sacs: list[SAC]) -> dict[str, tuple[object, str]]:
    """Every labelled pick of a site's channels, by header."""
    picks: dict[str, tuple[object, str]] = {}
    for sac in sacs:
        for header in PICK_HEADERS.values():
            time = getattr(sac.timestamps, header)
            if time is not None:
                picks[header] = (time, getattr(sac.native, f"k{header}"))
    return picks


def _rotated(
    vertical: SAC, channel: str, data: object, orientation: MiniOrientation
) -> SAC:
    sac = copy.deepcopy(vertical)
    sac.seismogram.data = data  # type: ignore[assignment]
    sac.station.channel = channel
    sac.orientation.azimuth = orientation.azimuth
    sac.orientation.dip = orientation.dip
    return sac


def prepare_band(
    label: str, channels: dict[str, SAC]
) -> tuple[dict[str, SAC], float | None]:
    """Z and the rotated channels of one band of a site, and the incidence used.

    Args:
        label: Event label, which decides between T and L/Q/T.
        channels: The band's Z and two horizontals, by channel code.
    """
    vertical_code = next(c for c in channels if not is_horizontal(c))
    vertical = channels[vertical_code]
    horizontals = sorted(c for c in channels if is_horizontal(c))
    band = vertical_code[:2]
    components = Components(
        [
            (channels[c].seismogram, channels[c].orientation)
            for c in (vertical_code, *horizontals)
        ]
    )
    baz = backazimuth(vertical.event, vertical.station)
    out = {vertical_code: vertical}
    incidence = None
    if label in LQT_PHASE:
        incidence = incidence_angle(
            depth=vertical.event.depth,
            distance=haversine(vertical.event, vertical.station),
            phase=LQT_PHASE[label],
        )
        rotated = zip(
            "LQT",
            rotate_to_lqt(components, baz, incidence),
            lqt_orientations(baz, incidence),
        )
    else:
        _, transverse = rotate_to_rt(components, baz)
        rotated = zip("T", [transverse], rt_orientations(baz)[1:])
    for component, seismogram, orientation in rotated:
        code = band + component
        out[code] = _rotated(vertical, code, seismogram.data, orientation)
    return out, incidence


def main() -> None:
    if PREPARED_DIR.exists():
        shutil.rmtree(PREPARED_DIR)
    for label in EVENTS:
        directory = PREPARED_DIR / label
        directory.mkdir(parents=True)
        keys = sorted(
            {p.name.rsplit(".", 1)[0] for p in (OUTPUT_DIR / label).iterdir()}
        )
        for key in keys:
            shipped = {
                p.name.rsplit(".", 1)[1]: SAC.from_file(p)
                for p in sorted((OUTPUT_DIR / label).glob(f"{key}.*"))
            }
            picks = _picks(list(shipped.values()))
            for band in sorted({c[:2] for c in shipped}):
                channels = {c: s for c, s in shipped.items() if c[:2] == band}
                prepared, incidence = prepare_band(label, channels)
                for code, sac in prepared.items():
                    for header in PICK_HEADERS.values():
                        time, name = picks.get(header, (None, None))
                        setattr(sac.timestamps, header, time)
                        setattr(sac.native, f"k{header}", name)
                    sac.write(directory / f"{key}.{code}", nvhdr=7)
                note = "" if incidence is None else f", incidence {incidence:.2f}"
                print(f"{label} {key} {band}: {sorted(prepared)}{note}")


if __name__ == "__main__":
    main()
