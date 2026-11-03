# GTA San Andreas Radio Generator

*[Leer en español](README.es.md)*

Recreates the radio stations of *Grand Theft Auto: San Andreas* from your own copy of the game: songs with their DJ intros and outros, DJ chatter, station idents and adverts, using the game's own sequencing and anti-repetition logic. Every broadcast is reproducible from a seed.

> **No game audio is included.** The app reads the audio files from a legal PC copy of the game that you own. Do not share the extracted `library/` folder or the rendered broadcasts.

## Requirements

- Windows, with Python 3.10+ (including tkinter), or the prebuilt `.exe`
- [ffmpeg](https://ffmpeg.org/) and ffprobe on the `PATH` (or `ffmpeg.exe` / `ffprobe.exe` next to the app)
- GTA San Andreas for PC installed (version 1.0 audio files)

## Usage

Run `SA Radio Generator.pyw` (double click), or `python -m sa_radio`. To build `SA Radio Generator.exe`, run `build.bat` (creates a local virtual environment and uses PyInstaller).

The interface is in Spanish; the option names below are translated.

1. **Game**: pick the GTA San Andreas folder and press *Extract game files*. This decrypts `audio/streams` and copies the 11 stations and the adverts into `library/` (~920 MB, a few seconds, done once). The game folder is only read.
2. **Broadcast** options:
   - *Station*: Playback FM, K-Rose, K-DST, Bounce FM, SF-UR, Radio Los Santos, Radio X, CSR 103.9, K-Jah West, Master Sounds 98.3, WCTR.
   - *Seed* and *Duration*.
   - *Adverts* and *Idents* on or off.
   - *DJ chatter*: none / few / normal (as in the game: 60% of breaks have chatter, the rest an advert) / many.
   - *Game hour at start* and *Weather*: the clock runs as in the game (1 game minute = 1 real second) and the DJ uses morning (6-8 h), evening (18-20 h), night (22-2 h), rain and fog lines like the game does.
   - *Story chatter*: lines the game plays only once after certain missions; here they play at random, once each.
   - *Fix the sunny chatter bug*: the game has clear-weather lines that never play because of a bug in its hour check; with this option they play from 8 to 18 h (the intended hours are unknown).
   - *Max songs in a row* without chatter or advert (2 in the game).
   - *Avoid repeats*: the game's history sizes (songs and chatter: up to 20/15 minus the last 2 possible; idents 8; adverts 40).
   - *Loudness*: original, or normalized to -16 LUFS over the whole broadcast (no gaps between intro and song).
   - *Format*: WAV, MP3 256 kbps or Opus 128 kbps (a single file).
3. *Preview* shows the running order; *Generate radio* renders the audio plus a `.txt` running order and a `.timeline.json`.

The same seed with the same options always produces the same broadcast. The broadcast ends after the first song that reaches the requested duration.

## How it works

The sequencing follows the game code, disassembled from `gta_sa.exe` 1.0 US (`CAERadioTrackManager` functions that [gta-reversed](https://github.com/gta-reversed/gta-reversed) has not decompiled yet). See [docs/how-it-works.md](docs/how-it-works.md) for the details.

## Project layout

| Path | Contents |
| --- | --- |
| `sa_radio/tables.py` | Track tables of the PC version and the DJ chatter lists read from the exe |
| `sa_radio/extract.py` | Decrypts the game's stream packs into `library/` |
| `sa_radio/stations.py` | Station definitions built from the tables |
| `sa_radio/engine.py` | Continuous-play logic (what plays after each song) |
| `sa_radio/render.py` | ffmpeg rendering, running order and timeline |
| `sa_radio/gui.py` | Tkinter interface |
| `scripts/` | The first standalone scripts (extractor, generator) and `RadioStreamsPC.h` from gta-reversed |
| `build.bat` | Builds the Windows `.exe` with PyInstaller |

Generated at runtime and not tracked by git: `library/`, `output/`, `settings.json`, `build/`, the `.exe`.

## Credits

- Track tables (`scripts/RadioStreamsPC.h`) from the [gta-reversed](https://github.com/gta-reversed/gta-reversed) project.
- *Grand Theft Auto: San Andreas* and all of its audio are © Rockstar Games / Take-Two Interactive. This is an unofficial fan project, not affiliated with or endorsed by them.

## License

Source code under the [MIT License](LICENSE). The license does not cover any game content.
