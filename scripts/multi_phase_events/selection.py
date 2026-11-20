"""Event and stations of the multi-phase fixture.

One deep event, so that pP arrives well clear of P (94 to 99 s after it at
these distances). The stations are a subset of the `aimbat-sampledata`
Fiji stations, spread over the distance range (72 to 90 deg). Each
records P and pP, except `PHASE_EXCEPTIONS`.
"""

from __future__ import annotations

from pysmo import MiniStation

EVENT_LABEL = "fiji_region"
USGS_EVENTID = "usc000stdc"

PHASES = ("P", "pP")

STATIONS: dict[str, MiniStation] = {
    key: MiniStation(
        name=key.split(".")[1],
        network=key.split(".")[0],
        location="--",
        channel="BHZ",
        latitude=lat,
        longitude=lon,
    )
    for key, (lat, lon) in {
        "AK.ATKA": (52.2015991210938, -174.197494506836),
        "AK.BAL": (61.0359992980957, -142.346206665039),
        "AK.CCB": (64.6453018188477, -147.805297851563),
        "AK.CHI": (55.8218002319336, -155.622497558594),
        "AK.CHUM": (63.8827018737793, -152.315200805664),
        "AK.FYU": (66.5656967163086, -145.23420715332),
        "AK.HIN": (60.3959999084473, -146.503494262695),
        "AK.JIS": (58.2757987976074, -134.384796142578),
        "AK.KNK": (61.4131011962891, -148.45849609375),
        "AK.MCK": (63.7318000793457, -148.937301635742),
        "AK.PAX": (62.969898223877, -145.46989440918),
        "AV.AKRB": (54.1291999816895, -166.07080078125),
        "AV.RDDF": (60.5912017822266, -152.688293457031),
        "TA.POKR": (65.1171035766602, -147.433502197266),
    }.items()
}

# Stations that keep only some of `PHASES`. AV.AKRB has the weakest P of
# the set, and MCCC cycle-skips its pP by about 6 s, so it carries no pP
# pick. The phases then differ in their seismograms.
PHASE_EXCEPTIONS: dict[str, tuple[str, ...]] = {
    "AV.AKRB": ("P",),
}


def station_phases(key: str) -> tuple[str, ...]:
    """Phases picked at a station."""
    return PHASE_EXCEPTIONS.get(key, PHASES)
