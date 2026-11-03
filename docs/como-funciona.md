# Cómo funciona

*[Read in English](how-it-works.md)*

## 1. Extracción del audio del juego (`sa_radio/extract.py`)

- `audio/CONFIG/StrmPaks.dat` lista los paquetes de audio (entradas de 16 bytes; la entrada 2 está vacía, así que los índices no coinciden con una lista simple).
- `audio/CONFIG/TrakLkup.dat` lista las 1922 pistas en registros de 12 bytes: paquete, posición y longitud.
- Cada paquete de `audio/streams` está cifrado con XOR con una clave de 16 bytes, alineada con el principio del archivo.
- Cada pista es una cabecera de 8068 bytes (datos de ritmo, longitud del Ogg, frecuencia) seguida de un Ogg Vorbis normal. La longitud de `TrakLkup.dat` no incluye esa cabecera.

El extractor escribe un archivo por pista en `library/<PAQUETE>/<id>.ogg` (id global de la pista) y sus duraciones en `library/library.json`. Solo se copian las 11 emisoras de música y el paquete de anuncios.

## 2. Datos de las emisoras (`sa_radio/tables.py`)

- Canciones, intros, outros, identificativos y los anuncios que cada emisora nunca pone salen de las tablas de pistas de la versión PC de gta-reversed (`scripts/RadioStreamsPC.h`).
- Las charlas del DJ se reparten por contexto (general, mañana, tarde, noche, lluvia, niebla, sol, historia) según las tablas de `gta_sa.exe` en `0x8C8BF0`-`0x8C8FAF`.

## 3. Orden de la emisión (`sa_radio/engine.py`)

La lógica es la de `CAERadioTrackManager` en `gta_sa.exe` 1.0 US (mismas direcciones que gta-reversed).

**Una canción** (`QueueUpTracksForStation`, `0x4EA670`) es siempre intro (1 de 3) + cuerpo + outro (1 de 3). Los cuerpos empiezan y acaban a pleno volumen, así que nunca suenan solos.

**Tras cada canción** (`CheckForTrackConcatenation`, `0x4EA930`):

1. Si van menos de 2 canciones seguidas, 50 % de pasar directamente a la siguiente, con identificativo antes la mitad de las veces.
2. Si no, identificativo (50 %) y después charla del DJ o, si no se elige charla, un anuncio.
3. Después de una charla o un anuncio viene directamente la siguiente canción, nunca un identificativo.

El contador de canciones seguidas se reinicia con charlas y anuncios, no con identificativos.

**Charlas del DJ** (`ChooseDJBanterIndex`, `0x4EA2D0`):

- El 40 % de las veces no se elige charla (suena un anuncio).
- Lluvia o niebla: 50 % de una charla de ese clima.
- Por hora del juego: 6-8 h mañana, 18-20 h tarde, 22-2 h noche, con un 30 %.
- Si no, una charla general.
- El juego también tiene charlas de "sol", pero su comprobación de la hora (`>= 8 y < 6`) nunca se cumple, así que nunca suenan. La opción *Corregir bug* las pone con cielo despejado de 8 a 18 h.

El reloj avanza a 1 minuto del juego por segundo real, así que una emisión larga recorre el día.

**Anti-repetición** (tamaños del historial del juego): canciones `min(20, n - 2)`, identificativos `min(8, n - 2)`, charlas `min(15, generales - 2)`, anuncios los últimos 40. Los anuncios vetados en una emisora no salen nunca en ella.

**Charlas de la historia**: en el juego cada una suena una vez tras una misión concreta. Con la opción activada, cada pausa tiene un 15 % de poner una de ellas al azar, y cada una suena una sola vez.

## 4. Render (`sa_radio/render.py`)

Todas las pistas son de 48 kHz. ffmpeg une la emisión en un solo archivo (WAV, MP3 u Opus), opcionalmente normalizado a -16 LUFS sobre toda la emisión. Cada render escribe además una escaleta `.txt` y un `.timeline.json` con el inicio, la duración y la pista del juego de cada elemento.
