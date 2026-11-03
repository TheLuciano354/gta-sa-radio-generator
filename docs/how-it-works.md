# How it works

*[Leer en español](como-funciona.md)*

## 1. Extracting the game audio (`sa_radio/extract.py`)

- `audio/CONFIG/StrmPaks.dat` lists the stream packs (16-byte entries; entry 2 is empty, so pack indexes do not match a naive list).
- `audio/CONFIG/TrakLkup.dat` lists the 1922 tracks as 12-byte records: pack, offset, length.
- Every pack in `audio/streams` is XOR-encrypted with a 16-byte key, aligned to the start of the file.
- Each track is an 8068-byte header (beat data, Ogg length, sample rate) followed by a plain Ogg Vorbis file. The length in `TrakLkup.dat` does not include that header.

The extractor writes one file per track to `library/<PACK>/<id>.ogg` (global track id) and their durations to `library/library.json`. Only the 11 music stations and the adverts pack are copied.

## 2. Station data (`sa_radio/tables.py`)

- Song bodies, intros, outros, idents and the adverts each station never plays come from the PC track tables in gta-reversed (`scripts/RadioStreamsPC.h`).
- DJ chatter is split by context (general, morning, evening, night, rain, fog, sunny, story) using the tables in `gta_sa.exe` at `0x8C8BF0`-`0x8C8FAF`.

## 3. Sequencing (`sa_radio/engine.py`)

The logic is taken from `CAERadioTrackManager` in `gta_sa.exe` 1.0 US (same addresses as gta-reversed).

**A song** (`QueueUpTracksForStation`, `0x4EA670`) is always intro (1 of 3) + body + outro (1 of 3). The song bodies start and end at full volume, so they are never played alone.

**After each song** (`CheckForTrackConcatenation`, `0x4EA930`):

1. If fewer than 2 songs have played in a row, 50% chance to go straight to the next song, with an ident before it half of the time.
2. Otherwise, an ident (50%) and then DJ chatter or, if no chatter is chosen, an advert.
3. After chatter or an advert comes the next song directly, never an ident.

The songs-in-a-row counter is reset by chatter and adverts, not by idents.

**DJ chatter** (`ChooseDJBanterIndex`, `0x4EA2D0`):

- 40% of the time no chatter is chosen (an advert plays instead).
- Rain or fog: 50% chance of a weather line.
- By game hour: 6-8 h morning, 18-20 h evening, 22-2 h night lines, 30% chance.
- Otherwise a general line.
- The game also has "sunny" lines, but its hour check (`>= 8 and < 6`) can never be true, so they never play. The *fix bug* option plays them in clear weather from 8 to 18 h.

The game clock runs at 1 game minute per real second, so a long broadcast moves through the day.

**Anti-repetition** (the game's history sizes): songs `min(20, n - 2)`, idents `min(8, n - 2)`, chatter `min(15, general - 2)`, adverts the last 40. Adverts restricted for a station are never chosen there.

**Story chatter**: in the game each line plays once after a given mission. With the option on, each break has a 15% chance of one of them, at random, each one played only once.

## 4. Rendering (`sa_radio/render.py`)

All tracks are 48 kHz. ffmpeg joins the timeline into one file (WAV, MP3 or Opus), optionally normalized to -16 LUFS over the whole broadcast. Each render also writes a `.txt` running order and a `.timeline.json` with the start time, duration and game track of every item.
