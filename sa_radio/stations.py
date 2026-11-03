"""The radio stations of GTA San Andreas and which game tracks belong to each one."""
from dataclasses import dataclass

from .tables import ADVERTS, BANTER_LISTS, STATIONS_DATA


def _span(r):
    return list(range(r[0], r[1] + 1)) if r else []


@dataclass
class Station:
    id: str
    name: str
    pack: str               # stream pack in audio/streams
    music: list             # track id of each song body
    intros: list            # (first, last) DJ intros of each song
    outros: list            # (first, last) DJ outros of each song
    idents: list
    banter_lists: dict      # DJ chat by context: general, morning, evening, night, rain, fog...
    restricted_ads: list

    @property
    def ads(self):
        return [a for a in range(ADVERTS[0], ADVERTS[1] + 1) if a not in self.restricted_ads]


def _build():
    out = {}
    for d in STATIONS_DATA:
        out[d["id"]] = Station(
            id=d["id"], name=d["name"], pack=d["pack"], music=d["music"], intros=d["intros"],
            outros=d["outros"], idents=_span(d["idents"]), banter_lists=BANTER_LISTS[d["id"]],
            restricted_ads=d["restricted_ads"])
    return out


STATIONS = _build()
