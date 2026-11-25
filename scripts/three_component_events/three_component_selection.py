"""Events, sites and channels of the three-component fixture.

Most sites are also in `aimbat-sampledata`, processed the same way (response
removed, resampled to 20 Hz). The others are here for what they show: two
location codes at one station, 1/2 horizontals at non-zero azimuths, other
sampling rates (`resample=False` keeps the native rate). `GAPPY` is fetched
raw for its data gap only.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    network: str
    station: str
    location: str
    channels: tuple[str, ...]
    resample: bool = True

    @property
    def key(self) -> str:
        """`NETWORK.STATION.LOCATION`, the fixture's key for the site."""
        return f"{self.network}.{self.station}.{self.location}"


@dataclass(frozen=True)
class EventSpec:
    usgs_eventid: str
    phases: tuple[str, ...]
    sites: tuple[Site, ...]


BH = ("BHZ", "BHN", "BHE")
BH12 = ("BHZ", "BH1", "BH2")
LH = ("LHZ", "LHN", "LHE")

# Horizontal channel endings: S and SKS are picked on these, P and pP on Z.
HORIZONTAL = ("N", "E", "1", "2")


def _sample(*keys: str) -> tuple[Site, ...]:
    """Sites as in `aimbat-sampledata`: location `--`, BHZ/BHN/BHE, 20 Hz."""
    sites = []
    for key in keys:
        network, station = key.split(".")
        sites.append(Site(network, station, "--", BH))
    return tuple(sites)


EVENTS: dict[str, EventSpec] = {
    # 434 km deep, 72 to 91 deg: P, pP and S.
    "fiji_region": EventSpec(
        "usc000stdc",
        ("P", "pP", "S"),
        _sample(
            "AK.BAL",
            "AK.CCB",
            "AK.CHI",
            "AK.GRNC",
            "AK.KNK",
            "AK.PAX",
            "AV.AKRB",
            "TA.POKR",
            "TA.TOLK",
        )
        + (
            Site("TA", "TOLK", "01", BH),
            Site("IU", "COLA", "00", BH12, resample=False),
            Site("IU", "COLA", "10", BH12, resample=False),
            Site("AK", "PAX", "--", LH, resample=False),
        ),
    ),
    # 88 to 108 deg, mostly in the core shadow: SKS only.
    "central_peru": EventSpec(
        "usb000s5x1",
        ("SKS",),
        _sample(
            "AK.BAL",
            "AK.CCB",
            "AK.CHUM",
            "AK.KNK",
            "AK.PAX",
            "AV.AKRB",
            "TA.POKR",
            "TA.TOLK",
        )
        + (Site("IU", "COLA", "00", BH12, resample=False),),
    ),
    # AK.GRNC's horizontals point 16 and 106 deg here, 0 and 90 at Fiji.
    "solomon_islands": EventSpec("usc000phx5", ("P", "S"), _sample("AK.GRNC")),
}

# Fetched raw (counts, miniSEED) for its data gap; window from its arrivals.
GAPPY_EVENT = "nepal"
GAPPY_EVENTID = "us20002926"
GAPPY_PHASES = ("P", "S")
GAPPY = Site("AK", "KNK", "--", BH)

# Fetched raw (counts, all channels in one miniSEED file) with its StationXML.
MULTIPLEXED_EVENT = "fiji_region"
MULTIPLEXED = Site("AK", "PAX", "--", BH)

# Derived from shipped files (see the fetch script).
MISSING_ORIENTATION = ("fiji_region", "AK.BAL.--")
P_ON_ALL_CHANNELS = ("fiji_region", "AK.KNK.--")
ROTATED_AS_BHN = ("central_peru", "TA.POKR.--")


def is_horizontal(channel: str) -> bool:
    return channel[-1] in HORIZONTAL


def phases_on_channel(phases: tuple[str, ...], channel: str) -> tuple[str, ...]:
    """The phases picked on `channel`: S and SKS on horizontals, the rest on Z."""
    horizontal = is_horizontal(channel)
    return tuple(p for p in phases if (p in ("S", "SKS")) == horizontal)
