"""Tkinter window: pick the game folder, extract, choose a seed and render a broadcast."""
import json
import os
import queue
import secrets
import string
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .engine import Options, build_timeline
from .extract import build_library, game_files_ok, load_library
from .render import FORMATS, ffmpeg_available, render, stamp, tracklist_text
from .stations import STATIONS

# Packaged as an .exe the data lives next to the executable, not in the temporary bundle folder.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIBRARY = os.path.join(APP_DIR, "library")
SETTINGS = os.path.join(APP_DIR, "settings.json")
DJ_CHOICES = [("none", "Ninguna"), ("few", "Pocas"), ("normal", "Normal (juego)"), ("many", "Muchas")]
WEATHER_CHOICES = [("clear", "Despejado"), ("cloudy", "Nublado"), ("rain", "Lluvia"), ("fog", "Niebla")]


def guess_game_dir():
    candidates = [r"C:\Program Files (x86)\Rockstar Games\GTA San Andreas",
                  r"C:\Program Files\Rockstar Games\GTA San Andreas",
                  os.path.join(r"C:\Program Files (x86)\Steam", "steamapps", "common", "Grand Theft Auto San Andreas")]
    for drive in string.ascii_uppercase:
        candidates += [f"{drive}:\\Juegos\\PC\\GTA San Andreas", f"{drive}:\\GTA San Andreas",
                       os.path.join(f"{drive}:\\SteamLibrary", "steamapps", "common", "Grand Theft Auto San Andreas")]
    return next((c for c in candidates if game_files_ok(c)), "")


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=12)
        self.root = root
        self.events = queue.Queue()
        self.busy = False
        self.cancel = threading.Event()
        self.library = load_library(LIBRARY)

        s = load_settings()
        self.game_dir = tk.StringVar(value=s.get("game_dir") or guess_game_dir())
        self.out_dir = tk.StringVar(value=s.get("out_dir") or os.path.join(APP_DIR, "output"))
        self.station = tk.StringVar(value=s.get("station", ""))
        self.seed = tk.StringVar(value=str(s.get("seed", secrets.randbelow(2 ** 32))))
        self.minutes = tk.StringVar(value=str(s.get("minutes", 60)))
        self.ads = tk.BooleanVar(value=s.get("ads", True))
        self.idents = tk.BooleanVar(value=s.get("idents", True))
        self.story = tk.BooleanVar(value=s.get("story", False))
        self.fix_bugs = tk.BooleanVar(value=s.get("fix_bugs", False))
        self.start_hour = tk.StringVar(value=str(s.get("start_hour", 12)))
        self.weather = tk.StringVar(value=s.get("weather", "clear"))
        self.avoid_repeats = tk.BooleanVar(value=s.get("avoid_repeats", True))
        self.dj = tk.StringVar(value=s.get("dj", "normal"))
        self.max_in_row = tk.StringVar(value=str(s.get("max_in_row", 2)))
        self.loudness = tk.StringVar(value=s.get("loudness", "original"))
        self.fmt = tk.StringVar(value=s.get("fmt", "opus"))
        self.status = tk.StringVar(value="Listo.")

        self._build()
        self._refresh_library()
        self.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        root.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._poll)

    # -- layout -----------------------------------------------------------
    def _build(self):
        self.columnconfigure(0, weight=1)

        game = ttk.LabelFrame(self, text="1. Juego", padding=8)
        game.grid(row=0, column=0, sticky="ew")
        game.columnconfigure(1, weight=1)
        ttk.Label(game, text="Carpeta de GTA San Andreas").grid(row=0, column=0, sticky="w")
        ttk.Entry(game, textvariable=self.game_dir).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(game, text="Examinar…", command=self._pick_game).grid(row=0, column=2)
        self.extract_btn = ttk.Button(game, text="Extraer archivos del juego", command=self._extract)
        self.extract_btn.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.lib_label = ttk.Label(game, foreground="#555")
        self.lib_label.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(8, 0))

        radio = ttk.LabelFrame(self, text="2. Emisión", padding=8)
        radio.grid(row=1, column=0, sticky="ew", pady=10)
        radio.columnconfigure(1, weight=1)

        ttk.Label(radio, text="Emisora").grid(row=0, column=0, sticky="w")
        self.station_box = ttk.Combobox(radio, textvariable=self.station, state="readonly", width=30)
        self.station_box.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(radio, text="Semilla").grid(row=1, column=0, sticky="w", pady=4)
        seed_row = ttk.Frame(radio)
        seed_row.grid(row=1, column=1, sticky="w", padx=6)
        ttk.Entry(seed_row, textvariable=self.seed, width=14).pack(side="left")
        ttk.Button(seed_row, text="Nueva semilla", command=self._new_seed).pack(side="left", padx=6)

        ttk.Label(radio, text="Duración (minutos)").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(radio, from_=1, to=1440, textvariable=self.minutes, width=8).grid(
            row=2, column=1, sticky="w", padx=6)

        opts = ttk.Frame(radio)
        opts.grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Checkbutton(opts, text="Anuncios", variable=self.ads).pack(side="left")
        ttk.Checkbutton(opts, text="Identificativos", variable=self.idents).pack(side="left", padx=12)
        ttk.Checkbutton(opts, text="Charlas de la historia", variable=self.story).pack(side="left")
        ttk.Checkbutton(opts, text="Corregir bug de las charlas de sol",
                        variable=self.fix_bugs).pack(side="left", padx=12)
        ttk.Checkbutton(opts, text="Evitar repeticiones", variable=self.avoid_repeats).pack(side="left")

        ttk.Label(radio, text="Charlas del DJ").grid(row=4, column=0, sticky="w")
        dj = ttk.Frame(radio)
        dj.grid(row=4, column=1, sticky="w", padx=6)
        for key, label in DJ_CHOICES:
            ttk.Radiobutton(dj, text=label, value=key, variable=self.dj).pack(side="left", padx=(0, 12))

        ttk.Label(radio, text="Hora del juego al empezar").grid(row=5, column=0, sticky="w", pady=4)
        ttk.Spinbox(radio, from_=0, to=23, textvariable=self.start_hour, width=5).grid(
            row=5, column=1, sticky="w", padx=6)

        ttk.Label(radio, text="Clima").grid(row=6, column=0, sticky="w")
        weather = ttk.Frame(radio)
        weather.grid(row=6, column=1, sticky="w", padx=6)
        for key, label in WEATHER_CHOICES:
            ttk.Radiobutton(weather, text=label, value=key, variable=self.weather).pack(side="left", padx=(0, 12))

        ttk.Label(radio, text="Máx. canciones seguidas").grid(row=7, column=0, sticky="w")
        ttk.Spinbox(radio, from_=1, to=10, textvariable=self.max_in_row, width=5).grid(
            row=7, column=1, sticky="w", padx=6)

        ttk.Label(radio, text="Volumen").grid(row=8, column=0, sticky="w", pady=4)
        vol = ttk.Frame(radio)
        vol.grid(row=8, column=1, sticky="w", padx=6)
        ttk.Radiobutton(vol, text="Original del juego", value="original",
                        variable=self.loudness).pack(side="left")
        ttk.Radiobutton(vol, text="Normalizado (-16 LUFS)", value="normalized",
                        variable=self.loudness).pack(side="left", padx=12)

        ttk.Label(radio, text="Formato").grid(row=9, column=0, sticky="w")
        fmt = ttk.Frame(radio)
        fmt.grid(row=9, column=1, sticky="w", padx=6)
        for key, spec in FORMATS.items():
            ttk.Radiobutton(fmt, text=spec["label"], value=key, variable=self.fmt).pack(side="left", padx=(0, 12))

        ttk.Label(radio, text="Carpeta de salida").grid(row=10, column=0, sticky="w", pady=4)
        out = ttk.Frame(radio)
        out.grid(row=10, column=1, sticky="ew", padx=6)
        out.columnconfigure(0, weight=1)
        ttk.Entry(out, textvariable=self.out_dir).grid(row=0, column=0, sticky="ew")
        ttk.Button(out, text="Examinar…", command=self._pick_out).grid(row=0, column=1, padx=(6, 0))

        buttons = ttk.Frame(radio)
        buttons.grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.preview_btn = ttk.Button(buttons, text="Vista previa", command=self._preview)
        self.preview_btn.pack(side="left")
        self.render_btn = ttk.Button(buttons, text="Generar radio", command=self._render)
        self.render_btn.pack(side="left", padx=6)
        self.cancel_btn = ttk.Button(buttons, text="Cancelar", command=self.cancel.set, state="disabled")
        self.cancel_btn.pack(side="left")

        lst = ttk.LabelFrame(self, text="Escaleta", padding=4)
        lst.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        lst.columnconfigure(0, weight=1)
        lst.rowconfigure(0, weight=1)
        self.text = tk.Text(lst, height=14, wrap="none", font=("Consolas", 9), state="disabled")
        self.text.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(lst, orient="vertical", command=self.text.yview)
        sy.grid(row=0, column=1, sticky="ns")
        sx = ttk.Scrollbar(lst, orient="horizontal", command=self.text.xview)
        sx.grid(row=1, column=0, sticky="ew")
        self.text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        bottom = ttk.Frame(self)
        bottom.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        bottom.columnconfigure(1, weight=1)
        self.progress = ttk.Progressbar(bottom, maximum=1.0, length=220)
        self.progress.grid(row=0, column=0)
        ttk.Label(bottom, textvariable=self.status).grid(row=0, column=1, sticky="w", padx=8)

    # -- helpers ----------------------------------------------------------
    def _refresh_library(self):
        lib = self.library
        names = [STATIONS[s].name for s in (lib or {}).get("stations", []) if s in STATIONS]
        self.station_box["values"] = names
        if names and self.station.get() not in names:
            self.station.set(next((n for n in names if n == "K-DST"), names[0]))
        if lib:
            self.lib_label["text"] = (f"Biblioteca lista: {len(names)} emisoras, {lib['tracks']} pistas "
                                      f"(extraída {lib['created']}).")
        else:
            self.lib_label["text"] = "Aún no se han extraído los archivos del juego."
        state = "normal" if lib and not self.busy else "disabled"
        self.preview_btn["state"] = self.render_btn["state"] = state

    def _set_busy(self, busy):
        self.busy = busy
        self.extract_btn["state"] = "disabled" if busy else "normal"
        self.cancel_btn["state"] = "normal" if busy else "disabled"
        self._refresh_library()

    def _pick_game(self):
        path = filedialog.askdirectory(title="Carpeta de GTA San Andreas", initialdir=self.game_dir.get() or None)
        if path:
            self.game_dir.set(os.path.normpath(path))

    def _pick_out(self):
        path = filedialog.askdirectory(title="Carpeta de salida", initialdir=self.out_dir.get() or None)
        if path:
            self.out_dir.set(os.path.normpath(path))

    def _new_seed(self):
        self.seed.set(str(secrets.randbelow(2 ** 32)))

    def _show(self, text):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")

    def _read_options(self):
        try:
            seed = int(self.seed.get())
            minutes = float(self.minutes.get().replace(",", "."))
            max_in_row = int(self.max_in_row.get())
            start_hour = int(self.start_hour.get()) % 24
        except ValueError:
            messagebox.showerror("Datos no válidos", "La semilla, la hora y el máximo de canciones seguidas deben ser "
                                                     "números enteros, y la duración un número.")
            return None
        if not 0 < minutes <= 1440:
            messagebox.showerror("Datos no válidos", "La duración debe estar entre 1 y 1440 minutos.")
            return None
        station = next(s for s in STATIONS.values() if s.name == self.station.get())
        options = Options(ads=self.ads.get(), idents=self.idents.get(), dj=self.dj.get(),
                          story=self.story.get(), max_in_row=max(1, max_in_row),
                          avoid_repeats=self.avoid_repeats.get(), start_hour=start_hour,
                          weather=self.weather.get(), fix_bugs=self.fix_bugs.get())
        return {"station": station, "seed": seed, "minutes": minutes, "options": options}

    def _timeline(self, opts):
        return build_timeline(opts["station"], self.library, opts["seed"], opts["minutes"], opts["options"])

    def _header(self, opts, items):
        end = items[-1]["start"] + items[-1]["duration"]
        songs = sum(1 for it in items if it["kind"] == "song")
        return (f"{opts['station'].name} · semilla {opts['seed']} · {stamp(end)} · "
                f"{songs} canciones · {len(items)} piezas")

    def _save_settings(self):
        data = {"game_dir": self.game_dir.get(), "out_dir": self.out_dir.get(), "station": self.station.get(),
                "seed": self.seed.get(), "minutes": self.minutes.get(), "ads": self.ads.get(),
                "idents": self.idents.get(), "story": self.story.get(), "fix_bugs": self.fix_bugs.get(),
                "start_hour": self.start_hour.get(), "weather": self.weather.get(),
                "avoid_repeats": self.avoid_repeats.get(), "dj": self.dj.get(),
                "max_in_row": self.max_in_row.get(), "loudness": self.loudness.get(), "fmt": self.fmt.get()}
        try:
            with open(SETTINGS, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        except OSError:
            pass

    # -- actions ----------------------------------------------------------
    def _extract(self):
        game_dir = self.game_dir.get().strip()
        if not game_files_ok(game_dir):
            messagebox.showerror("Carpeta no válida", "En esa carpeta no están audio\\CONFIG\\TrakLkup.dat "
                                                      "ni audio\\streams.")
            return
        self._save_settings()
        self._run(lambda progress, cancelled: ("library", build_library(game_dir, LIBRARY, progress, cancelled)))

    def _preview(self):
        opts = self._read_options()
        if opts:
            items = self._timeline(opts)
            self._show(tracklist_text(items, self._header(opts, items)))
            end = items[-1]["start"] + items[-1]["duration"]
            self.status.set(f"Vista previa: {len(items)} piezas, {stamp(end)}.")

    def _render(self):
        opts = self._read_options()
        if not opts:
            return
        self._save_settings()
        items = self._timeline(opts)
        header = self._header(opts, items)
        self._show(tracklist_text(items, header))
        fmt = self.fmt.get()
        name = f"{opts['station'].id}_semilla{opts['seed']}_{opts['minutes']:g}min{FORMATS[fmt]['ext']}"
        out_path = os.path.join(self.out_dir.get(), name)
        loudness = self.loudness.get()

        def job(progress, cancelled):
            render(items, LIBRARY, out_path, fmt=fmt, loudness=loudness, header=header,
                   progress=progress, cancelled=cancelled)
            return "rendered", out_path
        self._run(job)

    def _run(self, job):
        """Run job(progress, cancelled) in a thread; results arrive through self.events."""
        self.cancel.clear()
        self._set_busy(True)

        def worker():
            progress = lambda msg, frac: self.events.put(("progress", (msg, frac)))
            try:
                self.events.put(("done", job(progress, self.cancel.is_set)))
            except InterruptedError:
                self.events.put(("cancelled", None))
            except Exception as e:  # shown to the user, the worker must not die silently
                self.events.put(("error", e))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    self.status.set(payload[0])
                    self.progress["value"] = payload[1]
                    continue
                self._set_busy(False)
                self.progress["value"] = 0
                if kind == "done" and payload[0] == "library":
                    self.library = payload[1]
                    self._refresh_library()
                    self.status.set("Archivos extraídos.")
                elif kind == "done":
                    self.status.set(f"Guardado: {payload[1]}")
                    if messagebox.askyesno("Radio generada", f"Se ha guardado:\n{payload[1]}\n\n¿Abrir la carpeta?"):
                        os.startfile(os.path.dirname(payload[1]))
                elif kind == "cancelled":
                    self.status.set("Cancelado.")
                else:
                    self.status.set("Error.")
                    messagebox.showerror("Error", str(payload))
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _close(self):
        self._save_settings()
        self.root.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    # An ffmpeg.exe placed next to the app is used even if it is not on the PATH.
    os.environ["PATH"] = APP_DIR + os.pathsep + os.environ.get("PATH", "")
    root = tk.Tk()
    root.title("GTA San Andreas · Generador de radio")
    root.geometry("940x860")
    root.minsize(760, 600)
    if not ffmpeg_available():
        messagebox.showerror("Falta ffmpeg", "No se encuentra ffmpeg/ffprobe en el PATH. Instálalo para poder "
                                             "generar audio.")
    App(root)
    root.mainloop()
