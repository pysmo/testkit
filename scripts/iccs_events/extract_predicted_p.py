"""Rebuild ``predicted_p.py`` from the committed ICCS SAC ``t0`` headers.

The ICCS bundle is frozen: ``fetch_iccs_events.py`` reads the pinned
predicted-P arrivals from ``predicted_p.py`` rather than recomputing them,
and every shipped SAC already carries that same value as ``t0``. This
script just reads those ``t0`` values back out and regenerates the table,
so the two can't drift. Run it only after a deliberate re-cut of the
bundle, never as part of a routine regeneration.

    cd scripts/iccs_events && uv run python extract_predicted_p.py
"""

from pathlib import Path

from pysmo.classes import SAC

ASSETS_DIR = (
    Path(__file__).parent.parent.parent / "src" / "testkit" / "assets" / "iccs_events"
)
TABLE_PATH = Path(__file__).parent / "predicted_p.py"

HEADER = '''"""Pinned predicted-P arrivals for the ICCS/MCCC array fixture.

One entry per shipped ``iccs_events`` SAC file, keyed by ``(event label,
"NETWORK.STATION")``. These are the values ``fetch_iccs_events.py`` writes
into each SAC as ``t0`` (the initial pick) and uses to anchor the fetch
window (``t0 - 2 min`` to ``t0 + 3 min``).

Frozen, not recomputed. Originally from EarthScope's ``irisws-traveltime``
(retired 2026); the bundle was first cut against it. Regenerated straight
back out of the committed SAC ``t0`` headers by ``extract_predicted_p.py``
in this directory, so the table and the shipped files agree by
construction. ``tests/test_traveltime_windows.py`` checks these still
track pysmo's current tau-p solver, which now agrees to a few ms
everywhere except one branch-crossover cusp (see that test).
"""

PREDICTED_P: dict[tuple[str, str], str] = {'''


def main() -> None:
    by_label: dict[str, dict[str, str]] = {}
    for sac_file in sorted(ASSETS_DIR.glob("*/*.BHZ")):
        sac = SAC.from_file(str(sac_file))
        key = f"{sac.station.network}.{sac.station.name}"
        by_label.setdefault(sac_file.parent.name, {})[key] = (
            sac.timestamps.t0.isoformat()
        )

    lines = [HEADER]
    for label, entries in by_label.items():
        lines.append(f"    # {label}")
        for key, iso in entries.items():
            lines.append(f'    ("{label}", "{key}"): "{iso}",')
    lines.append("}\n")
    TABLE_PATH.write_text("\n".join(lines))
    print(f"wrote {sum(len(v) for v in by_label.values())} entries to {TABLE_PATH}")


if __name__ == "__main__":
    main()
