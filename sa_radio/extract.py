"""Build the local library from the game's audio/streams packs.

Every pack is XOR-encrypted with a 16-byte key (relative to the start of the file).
audio/CONFIG/TrakLkup.dat lists the 1922 tracks: pack, offset and length. Each track is
an 8068-byte header (beat data, ogg length, sample rate) followed by an Ogg Vorbis file;
the length in TrakLkup.dat does not include that header.

Library layout:
    library/library.json        tracks extracted and their durations
    library/<PACK>/<id>.ogg     one file per game track (global track id)
"""
import json
import os
import struct
import time

from .stations import STATIONS
from .tables import ADVERTS

KEY = bytes.fromhex("EA3AC4A19AA814F348B0D7239DE8FFF1")
HEADER = 8068
ADVERTS_PACK = "ADVERTS"


def game_files_ok(game_dir):
    return (os.path.isfile(os.path.join(game_dir, "audio", "CONFIG", "TrakLkup.dat"))
            and os.path.isdir(os.path.join(game_dir, "audio", "streams")))


def read_lookup(game_dir):
    config = os.path.join(game_dir, "audio", "CONFIG")
    with open(os.path.join(config, "StrmPaks.dat"), "rb") as f:
        raw = f.read()
    packs = [raw[i:i + 16].split(b"\0", 1)[0].decode("ascii") for i in range(0, len(raw), 16)]
    with open(os.path.join(config, "TrakLkup.dat"), "rb") as f:
        raw = f.read()
    tracks = []
    for i in range(len(raw) // 12):
        pack, offset, length = struct.unpack_from("<B3xII", raw, i * 12)
        tracks.append((packs[pack], offset, length))
    return tracks


def decrypt(data, offset):
    shift = offset % 16
    key = (KEY[shift:] + KEY[:shift]) * (len(data) // 16 + 1)
    n = len(data)
    return (int.from_bytes(data, "little") ^ int.from_bytes(key[:n], "little")).to_bytes(n, "little")


def ogg_duration(data):
    """Duration from the granule position of the last Ogg page and the Vorbis sample rate."""
    rate = struct.unpack_from("<I", data, data.index(b"\x01vorbis") + 12)[0]
    last = data.rindex(b"OggS")
    return struct.unpack_from("<q", data, last + 6)[0] / rate


def build_library(game_dir, library_dir, progress=lambda msg, frac: None, cancelled=lambda: False):
    tracks = read_lookup(game_dir)
    wanted = {s.pack for s in STATIONS.values()} | {ADVERTS_PACK}
    ids = [i for i, (pack, _, _) in enumerate(tracks) if pack in wanted]
    first = {}
    for i in ids:
        first.setdefault(tracks[i][0], i)

    durations, handles = {}, {}
    try:
        for n, i in enumerate(ids):
            if cancelled():
                raise InterruptedError
            pack, offset, length = tracks[i]
            if n % 10 == 0:
                progress(f"Extrayendo pista {n + 1}/{len(ids)} ({pack})", n / len(ids))
            if pack not in handles:
                handles[pack] = open(os.path.join(game_dir, "audio", "streams", pack), "rb")
            f = handles[pack]
            f.seek(offset)
            data = decrypt(f.read(HEADER + length), offset)
            ogg_len = struct.unpack_from("<i", data, 8000)[0]
            ogg = data[HEADER:HEADER + ogg_len]
            rel = f"{pack}/{i}.ogg"
            os.makedirs(os.path.join(library_dir, pack), exist_ok=True)
            with open(os.path.join(library_dir, rel), "wb") as out:
                out.write(ogg)
            durations[str(i)] = ogg_duration(ogg)
    finally:
        for f in handles.values():
            f.close()

    lib = {"created": time.strftime("%Y-%m-%d %H:%M"), "game_dir": game_dir,
           "packs": {p: [first[p], max(i for i in ids if tracks[i][0] == p)] for p in first},
           "stations": [s.id for s in STATIONS.values() if s.pack in first],
           "adverts": ADVERTS_PACK in first, "tracks": len(ids), "durations": durations}
    with open(os.path.join(library_dir, "library.json"), "w", encoding="utf-8") as f:
        json.dump(lib, f, indent=1)
    progress("Terminado.", 1.0)
    return lib


def load_library(library_dir):
    try:
        with open(os.path.join(library_dir, "library.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None

