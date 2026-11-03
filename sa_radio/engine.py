"""Radio engine: the continuous-play logic of the game, disassembled from gta_sa.exe 1.0 US.

What follows the end of each song (CAERadioTrackManager::CheckForTrackConcatenation, 0x4EA930):
  - if fewer than 2 songs in a row and 50%: [50% ident] -> next song
  - otherwise: [50% ident] -> DJ chat, or an advert when no chat is chosen
  - after a chat or an advert comes the next song directly (never an ident).
A song is always intro (1 of 3) + body + outro (1 of 3) (QueueUpTracksForStation, 0x4EA670).

DJ chat (ChooseDJBanterIndex, 0x4EA2D0): 40% of the time no chat is chosen (advert instead).
Otherwise, by weather: rain or fog 50% their lines; then by game hour: 6-8 h morning,
18-20 h evening, 22-2 h night lines 30%; else general chat. The game also has "sunny"
lines, but a bug in the hour check (>= 8 and < 6) means they never play; with fix_bugs
they play in clear weather from 8 to 18 h (the intended hours are unknown).

Anti-repetition: songs min(20, n-2), idents min(8, n-2), chats min(15, general-2),
adverts last 40 plus the adverts each station never plays. The song counter that limits
songs in a row is reset by chats and adverts, not by idents.
"""
import random

from .extract import ADVERTS_PACK

DJ_LEVELS = {"none": 0.0, "few": 0.3, "normal": 0.6, "many": 0.9}  # chance of a chat in a break
LABELS = {"ident": "Identificativo", "dj": "Charla DJ", "morning": "Charla DJ (mañana)",
          "evening": "Charla DJ (tarde)", "night": "Charla DJ (noche)", "rain": "Charla DJ (lluvia)",
          "fog": "Charla DJ (niebla)", "sunny": "Charla DJ (sol)", "story": "Charla DJ (historia)", "ad": "Anuncio",
          "intro": "Intro DJ", "song": "Canción", "outro": "Outro DJ"}
GAME_SECONDS_PER_HOUR = 60  # one game minute lasts one real second


class Options:
    def __init__(self, ads=True, idents=True, dj="normal", story=False, max_in_row=2, avoid_repeats=True,
                 start_hour=12, weather="clear", fix_bugs=False):
        self.ads = ads
        self.idents = idents
        self.dj = dj
        self.story = story            # mission lines: in the game each one plays once, after its mission
        self.max_in_row = max_in_row
        self.avoid_repeats = avoid_repeats
        self.start_hour = start_hour
        self.weather = weather        # "clear", "cloudy", "rain" or "fog"
        self.fix_bugs = fix_bugs


def _span(r):
    return [] if r is None else list(range(r[0], r[1] + 1))


class Broadcast:
    def __init__(self, station, library, seed, options):
        self.st = station
        self.opt = options
        self.rng = random.Random(seed)
        self.durations = library["durations"]
        self.items, self.t = [], 0.0
        self.in_row = 0
        self.history = {"song": [], "ad": [], "dj": [], "ident": []}
        self.idents = station.idents if options.idents else []
        self.ads = station.ads if options.ads and library.get("adverts") else []
        self.lines = {k: _span(r) for k, r in station.banter_lists.items()}
        self.story = [t for k in ("story", "first", "first2") for t in self.lines.get(k, [])] if options.story else []
        self.word = "Programa" if station.id == "wctr" else "Canción"

    # -- selection ------------------------------------------------------------
    def _limit(self, kind, pool):
        game = {"song": 20, "ident": 8, "dj": 15, "ad": 40}[kind]
        if kind == "dj":
            return min(game, len(self.lines["general"]) - 2)
        return game if kind == "ad" else min(game, len(pool) - 2)

    def pick(self, kind, pool):
        """Random choice avoiding the recent history; None when everything was played recently
        (the game gives up on a chat in that case)."""
        hist = self.history[kind][:max(0, self._limit(kind, pool))] if self.opt.avoid_repeats else []
        fresh = [x for x in pool if x not in hist]
        if not fresh:
            if kind == "dj":
                return None
            fresh = pool
        x = self.rng.choice(fresh)
        self.history[kind] = ([x] + self.history[kind])[:40]
        return x

    def hour(self):
        return int(self.opt.start_hour + self.t / GAME_SECONDS_PER_HOUR) % 24

    def choose_chat(self):
        """ChooseDJBanterIndex: (kind, track) or None."""
        if self.story and self.rng.random() < 0.15:
            t = self.story.pop(self.rng.randrange(len(self.story)))
            return "story", t
        if self.rng.random() >= DJ_LEVELS[self.opt.dj]:
            return None
        w = self.opt.weather
        if w in ("rain", "fog") and self.lines.get(w) and self.rng.random() < 0.5:
            t = self.pick("dj", self.lines[w])
            if t is not None:
                return w, t
        h = self.hour()
        if w == "clear" and self.opt.fix_bugs and 8 <= h < 18 and self.lines.get("sunny") and self.rng.random() < 0.5:
            t = self.pick("dj", self.lines["sunny"])
            if t is not None:
                return "sunny", t
        kind = "morning" if 6 <= h < 9 else "evening" if 18 <= h < 21 else "night" if h >= 22 or h < 3 else None
        if kind and self.lines.get(kind) and self.rng.random() < 0.3:
            t = self.pick("dj", self.lines[kind])
            if t is not None:
                return kind, t
        if not self.lines.get("general"):
            return None
        t = self.pick("dj", self.lines["general"])
        return None if t is None else ("dj", t)

    # -- output -------------------------------------------------------------
    def add(self, kind, track, pack=None, song=None):
        if str(track) not in self.durations:
            return
        text = LABELS[kind]
        if song is not None:
            text = f"{self.word} {song + 1}" if kind == "song" else f"{text} ({self.word.lower()} {song + 1})"
        dur = self.durations[str(track)]
        self.items.append({"kind": kind, "text": text, "track": track, "hour": self.hour(),
                           "file": f"{pack or self.st.pack}/{track}.ogg", "start": self.t, "duration": dur})
        self.t += dur

    def ident(self):
        if self.idents:
            self.add("ident", self.pick("ident", self.idents))

    def song(self):
        s = self.pick("song", list(range(len(self.st.music))))
        self.add("intro", self.rng.randint(*self.st.intros[s]), song=s)
        self.add("song", self.st.music[s], song=s)
        self.add("outro", self.rng.randint(*self.st.outros[s]), song=s)
        self.in_row += 1

    def after_song(self):
        """CheckForTrackConcatenation once the outro is playing."""
        if self.in_row < self.opt.max_in_row and self.rng.random() < 0.5:
            if self.rng.random() < 0.5:
                self.ident()
            return
        if self.rng.random() < 0.5:
            self.ident()
        chat = self.choose_chat()
        if chat:
            self.add(*chat)
            self.in_row = 0
        elif self.ads:
            self.add("ad", self.pick("ad", self.ads), pack=ADVERTS_PACK)
            self.in_row = 0

    def run(self, minutes):
        """Fill `minutes`; the broadcast ends after the first song that reaches the target."""
        self.ident()
        chat = self.choose_chat()
        if chat:
            self.add(*chat)
        self.song()
        while self.t < minutes * 60:
            self.after_song()
            self.song()
        return self.items


def build_timeline(station, library, seed, minutes, options):
    return Broadcast(station, library, seed, options).run(minutes)
