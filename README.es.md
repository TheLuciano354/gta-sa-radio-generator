# Generador de radio de GTA San Andreas

*[Read in English](README.md)*

Recrea las emisoras de *Grand Theft Auto: San Andreas* a partir de tu propia copia del juego: canciones con su intro y outro del DJ, charlas, identificativos y anuncios, con la misma lógica de orden y anti-repetición del juego. Cada emisión se puede reproducir a partir de una semilla.

> **No incluye audio del juego.** La app lee los archivos de audio de una copia legal del juego para PC que tengas. No compartas la carpeta `library/` extraída ni las emisiones generadas.

## Requisitos

- Windows, con Python 3.10+ (con tkinter) o el `.exe` ya compilado
- [ffmpeg](https://ffmpeg.org/) y ffprobe en el `PATH` (o `ffmpeg.exe` / `ffprobe.exe` junto a la app)
- GTA San Andreas para PC instalado (archivos de audio de la versión 1.0)

## Uso

Doble clic en `SA Radio Generator.pyw`, o `python -m sa_radio`. Para crear `SA Radio Generator.exe`, ejecuta `build.bat` (crea un entorno virtual local y usa PyInstaller).

1. **Juego**: elige la carpeta de GTA San Andreas y pulsa *Extraer archivos del juego*. Descifra `audio/streams` y copia a `library/` las 11 emisoras y los anuncios (~920 MB, unos segundos, se hace una vez). La carpeta del juego solo se lee.
2. **Emisión**:
   - *Emisora*: Playback FM, K-Rose, K-DST, Bounce FM, SF-UR, Radio Los Santos, Radio X, CSR 103.9, K-Jah West, Master Sounds 98.3, WCTR.
   - *Semilla* y *Duración*.
   - *Anuncios*, *Identificativos*: quitar o poner.
   - *Charlas del DJ*: Ninguna / Pocas / Normal (juego: 60 % de las pausas tienen charla, el resto anuncio) / Muchas.
   - *Hora del juego al empezar* y *Clima*: el reloj avanza como en el juego (1 minuto del juego = 1 segundo), y el DJ usa sus charlas de mañana (6-8 h), tarde (18-20 h), noche (22-2 h), lluvia y niebla igual que el juego.
   - *Charlas de la historia*: las que el juego pone una sola vez tras ciertas misiones; aquí salen al azar, cada una una vez.
   - *Corregir bug de las charlas de sol*: el juego tiene charlas para días despejados que nunca suenan por un error en la comprobación de la hora; con esta opción suenan de 8 a 18 h (la hora pensada no se conoce).
   - *Máx. canciones seguidas* sin charla ni anuncio (2 en el juego).
   - *Evitar repeticiones*: historial del juego (canciones y charlas: hasta 20/15 menos las 2 últimas posibles; identificativos 8; anuncios 40).
   - *Volumen*: original o normalizado a -16 LUFS (sobre toda la emisión, sin cortes entre intro y canción).
   - *Formato*: WAV, MP3 256 kbps u Opus 128 kbps (un solo archivo).
3. *Vista previa* muestra la escaleta; *Generar radio* crea el audio con su escaleta `.txt` y un `.timeline.json`.

La misma semilla con las mismas opciones produce siempre la misma emisión. La emisión termina tras la primera canción que alcanza la duración pedida.

## Cómo funciona

El orden sigue el código del juego, desensamblado de `gta_sa.exe` 1.0 US (funciones de `CAERadioTrackManager` que [gta-reversed](https://github.com/gta-reversed/gta-reversed) aún no ha descompilado). Los detalles están en [docs/como-funciona.md](docs/como-funciona.md).

## Estructura

| Ruta | Contenido |
| --- | --- |
| `sa_radio/tables.py` | Tablas de pistas de la versión PC y listas de charlas del DJ leídas del exe |
| `sa_radio/extract.py` | Descifra los paquetes de audio del juego en `library/` |
| `sa_radio/stations.py` | Definición de las emisoras a partir de las tablas |
| `sa_radio/engine.py` | Lógica de emisión continua (qué suena tras cada canción) |
| `sa_radio/render.py` | Render con ffmpeg, escaleta y timeline |
| `sa_radio/gui.py` | Interfaz Tkinter |
| `scripts/` | Los primeros scripts sueltos (extractor, generador) y `RadioStreamsPC.h` de gta-reversed |
| `build.bat` | Compila el `.exe` de Windows con PyInstaller |

Se generan al usar la app y git no los sigue: `library/`, `output/`, `settings.json`, `build/`, el `.exe`.

## Créditos

- Tablas de pistas (`scripts/RadioStreamsPC.h`) del proyecto [gta-reversed](https://github.com/gta-reversed/gta-reversed).
- *Grand Theft Auto: San Andreas* y todo su audio son © Rockstar Games / Take-Two Interactive. Es un proyecto no oficial de fans, sin relación con ellos ni respaldado por ellos.

## Licencia

Código bajo [licencia MIT](LICENSE). La licencia no cubre ningún contenido del juego.
