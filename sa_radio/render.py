"""Render a broadcast timeline to WAV, MP3 or Opus with its tracklist."""
import json
import os
import shutil
import subprocess
import tempfile

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RATE = "48000"  # every track of the game is 48 kHz

FORMATS = {
    "wav": {"label": "WAV (PCM 16 bits)", "ext": ".wav", "args": ["-c:a", "pcm_s16le", "-rf64", "auto"]},
    "mp3": {"label": "MP3 256 kbps VBR", "ext": ".mp3", "args": ["-c:a", "libmp3lame", "-abr", "1", "-b:a", "256k"]},
    "opus": {"label": "Opus 128 kbps VBR", "ext": ".opus", "args": ["-c:a", "libopus", "-b:a", "128k", "-vbr", "on"]},
}


def ffmpeg_available():
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def stamp(seconds):
    h, rest = divmod(int(seconds), 3600)
    return f"{h}:{rest // 60:02d}:{rest % 60:02d}" if h else f"{rest // 60:02d}:{rest % 60:02d}"


def tracklist_text(items, header):
    out = [header, ""]
    for it in items:
        indent = "  " if it["kind"] in ("intro", "song", "outro") else ""
        text = f"♪ {it['text']}" if it["kind"] == "song" else it["text"]
        out.append(f"[{stamp(it['start'])}] {it['hour']:02d}h  {indent}{text}  (pista {it['track']})")
    end = items[-1]["start"] + items[-1]["duration"]
    out += ["", f"Duración total: {stamp(end)}"]
    return "\n".join(out) + "\n"


def _ffmpeg(*args):
    # stdin and output are redirected explicitly: a windowed .exe has no console handles.
    proc = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, creationflags=NO_WINDOW)
    if proc.returncode:
        raise RuntimeError(f"ffmpeg falló: {proc.stderr.strip()[-500:]}")


def render(items, library_dir, out_path, fmt="opus", loudness="original", header="",
           progress=lambda msg, frac: None, cancelled=lambda: False):
    """Decode every piece to PCM, concatenate without gaps (intros run into the song)
    and encode once. Next to the audio it writes <name>.txt and <name>.timeline.json."""
    spec = FORMATS[fmt]
    # Normalising the whole broadcast at once keeps intro, song and outro joined seamlessly.
    level = ["-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] if loudness == "normalized" else []
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="saradio_") as tmp:
        decoded = {}
        unique = list(dict.fromkeys(it["file"] for it in items))
        for i, name in enumerate(unique):
            if cancelled():
                raise InterruptedError
            progress(f"Preparando pieza {i + 1}/{len(unique)}", 0.8 * i / len(unique))
            wav = os.path.join(tmp, f"{i:05d}.wav")
            _ffmpeg("-i", os.path.join(library_dir, name), "-ar", RATE, "-ac", "2", "-c:a", "pcm_s16le", wav)
            decoded[name] = wav

        listing = os.path.join(tmp, "list.txt")
        with open(listing, "w", encoding="utf-8") as f:
            for it in items:
                f.write(f"file '{decoded[it['file']]}'\n")
        progress("Codificando…", 0.82)
        _ffmpeg("-f", "concat", "-safe", "0", "-i", listing, *level, "-ar", RATE, *spec["args"], out_path)

    base = os.path.splitext(out_path)[0]
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(tracklist_text(items, header))
    with open(base + ".timeline.json", "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    progress("Terminado.", 1.0)
