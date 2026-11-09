# Trama: TUI del compositor GSR

Interfaz de pantalla completa para editar antes de grabar. Reutiliza el perfil
TOML, el plugin Rust 0.4.0 y la grabación GSR existentes. No añade previsualización,
edición en vivo ni empaquetado. No requiere nuevas dependencias de pip: usa
`curses` de Python, disponible en el entorno revisado.

## Abrir tu perfil

Desde una terminal de COSMIC, sin sudo:

```bash
cd "$HOME/project-gsr-compositor"
./trama perfil.toml
```

Para poder escribir solo `trama` en esa shell, sin instalar nada:

```bash
export PATH="$PWD:$PATH"
trama
```

El `PATH` anterior vale para esa shell. No se modifican tus archivos de inicio ni
se instala un comando global. También puedes lanzar:

```bash
python3 scripts/trama_tui.py perfil.toml
./trama --help
```

La terminal debe tener al menos **72 columnas × 20 filas** y un `TERM` válido.
Tema oscuro, selección teal/cian y coral para error/grabación; alternativa
monocroma cuando el terminal no ofrece color. No requiere bibliotecas de TUI externas.

Tab/Shift+Tab recorre las cinco secciones persistentes:

- **Overview**: resumen, grabar, prueba de 30 segundos y guardar.
- **Layers**: lista y propiedades de la capa seleccionada; en terminales amplios
  aparecen juntas, en terminales compactas las propiedades quedan debajo.
- **Capture**: pantalla, resolución conocida y FPS.
- **Audio**: micrófono y audio del juego/sistema.
- **Output**: carpeta y nombre del archivo por separado; último MKV.

Flechas o `j`/`k` seleccionan campo/capa/acción; Enter ejecuta o edita.
Espacio abre las acciones del contexto, incluyendo agregar/quitar/reordenar,
guardar como y cargar perfiles. `?` muestra todos los atajos. Los atajos directos
siguen disponibles desde cualquier sección. Esc vuelve o cancela; al salir con
cambios sin guardar se pide qué hacer. Ctrl+U borra un campo de texto.

La cabecera distingue LISTO, ERROR y CONFIGURACIÓN INCOMPLETA según los datos
consultados y los errores conocidos. LISTO no certifica que todos los recursos
sean válidos: la validación completa se conserva antes de iniciar GSR.
El nombre del perfil marca los cambios sin guardar. El pie muestra pocos atajos
relevantes para la sección actual; `!` permite leer errores largos.

Durante la grabación se conserva la vista mínima estática: PREPARANDO, GRABANDO
o CERRANDO, duración solicitada cuando existe y destino del archivo. No se añade
contador periódico, uso de hardware supuesto ni edición durante la captura.

## Idioma: automático, español e inglés

La primera vez, Trama consulta `LC_ALL`, después `LC_MESSAGES` y finalmente
`LANG`, usando la primera variable no vacía. Un idioma `es` (como `es_MX.UTF-8`)
activa español; inglés, cualquier otro idioma y `C`/`POSIX` usan inglés.
La detección es local: no necesita API, red ni servicios de traducción.

Pulsa **`L` mayúscula** desde cualquier sección para elegir:

- **Automático (sistema)**: seguir el idioma del entorno.
- **Español**: usar siempre español.
- **English**: usar siempre inglés.

Enter guarda y aplica el cambio inmediatamente; Esc lo cancela. También está en
Espacio → acciones de Overview. La cabecera muestra el idioma activo junto a `L`.
La ayuda (`?`/F1) conserva una acción por renglón en ambos idiomas.

La preferencia se guarda en `$XDG_CONFIG_HOME/trama/ui.toml`, o en
`~/.config/trama/ui.toml` si no se define esa variable:

```toml
language = "auto"
```

Valores admitidos: `auto`, `es`, `en`. No se añade ningún campo al perfil TOML de
la grabación. Si el archivo de preferencia falta o es inválido, se usa automático.
Los datos de sesión y los perfiles anteriores no se migran ni se eliminan.

Para cambiar el idioma **solo en esta ejecución**, incluso en `--help`:

```bash
./trama --lang en
./trama --lang es /ruta/a/perfil.toml
./trama --lang auto
./trama --lang en --help
```

Prioridad: `--lang` → preferencia guardada → automático. Elegir un idioma con
`L` durante la sesión guarda una nueva preferencia. Los atajos no cambian al
traducir la interfaz. Los nombres de dispositivos, capas y archivos se mantienen
intactos. Los diagnósticos del motor, del loader y del sistema se muestran en su
idioma original; esta entrega traduce la TUI, no las otras CLI ni la documentación.

## Primera vez

Si abres un nombre de perfil que todavía no existe y se pudo consultar la
pantalla, se abre este recorrido. También puedes abrirlo con `w`:

1. Elige la pantalla por su nombre y resolución.
2. Elige el micrófono por nombre, o el predeterminado. Para un avatar necesitas
   una entrada; «sin micrófono» no basta.
3. Busca el GIF de reposo y el GIF de habla en el selector de archivos.
4. Elige una de las cuatro esquinas. La capa nueva propone caja de 300 px y
   margen de 20 px, que puedes cambiar en esa misma pantalla.
5. Selecciona **Guardar perfil y grabar 30 segundos**. También puedes guardar sin
   grabar, o volver a editar sin guardar.

El selector de archivos permite abrir carpetas con Enter y elegir un archivo con
Enter. `p` permite escribir o pegar una ruta completa; esa ruta relativa se basa
en la carpeta que muestra el selector. Esc cancela. Los filtros visuales muestran
GIF para avatar y PNG/JPG/GIF para gráficos; el decoder Rust valida el contenido.

Después de iniciar, cambia a Minecraft. La captura incluye todo el monitor; no
hay cuenta atrás ni atajo global de parada. Al terminar se vuelve a la TUI y se
muestra el nombre del MKV. Pulsa `o` para ver la ruta completa y los archivos
auxiliares, con desplazamiento si no caben en pantalla.

Puedes cancelar el recorrido en sus diálogos con Esc. Los ajustes ya aplicados
quedan en memoria: `s` los guarda, y salir avisa si hay cambios.

## Uso diario y último perfil

Sin argumento, Trama busca:

1. El último perfil abierto/guardado que conste en su estado de sesión.
2. Si no hay estado válido, `perfil.toml` en el directorio actual.

Un argumento explícito, como `./trama otro.toml`, tiene prioridad. La ruta del
último perfil se recuerda en:

```text
$XDG_STATE_HOME/xolo/session.json
```

Si no has definido `XDG_STATE_HOME`, usa `~/.local/state/xolo/session.json`.
Se conserva esta ubicación histórica para no mover datos personales; no es un
alias ni un comando anterior. Ese archivo contiene una ruta al perfil, no una copia de sus cambios sin guardar.
La TUI no modifica el perfil al abrirlo. Si el último archivo fue eliminado, se
prepara un perfil nuevo asociado a esa ruta: `l` permite abrir otro o `S` guardarlo
con otro nombre. Los errores al guardar el estado de sesión no sustituyen el TOML.

En el uso diario puedes pulsar **`r` desde el inicio** para grabar, o `t` para una
prueba de 30 segundos. No hace falta recorrer asistentes si la escena está lista.
La validación real de dispositivos y recursos sigue ejecutándose antes de grabar.

## Teclas de la pantalla principal

| Tecla | Acción |
| --- | --- |
| Tab / Shift+Tab | Cambiar sección enfocada |
| ↑/↓ o `j`/`k` | Elegir campo o capa de la sección actual |
| ←/→ en Overview | Elegir botón |
| Enter | Editar campo o ejecutar botón enfocado |
| Espacio | Abrir acciones de la sección enfocada |
| L | Elegir idioma y guardar la preferencia |
| `?` o F1 | Ayuda completa |
| `e` | Editar un campo de la capa seleccionada |
| `p` | Elegir pantalla |
| `m` | Elegir micrófono |
| `f` | Editar FPS (1..120) |
| `g` | Activar/desactivar audio del juego/sistema |
| `d` | Elegir carpeta de grabaciones |
| `n` | Editar nombre del video, incluido `{timestamp}` |
| `a` | Agregar gráfico PNG/JPG/GIF |
| `v` | Agregar avatar, si no hay uno |
| `c` | Colocar la capa seleccionada por esquina y tamaño |
| `h` | Ocultar/mostrar la capa sin quitarla |
| Supr o `D` | Quitar una capa, con confirmación; no borra el archivo |
| `[` / `]` | Mover la capa hacia el fondo / hacia delante en el listado |
| `s` | Guardar el perfil actual |
| `S` | Guardar como otro TOML |
| `l` | Cargar otro TOML |
| `r` | Grabar hasta detener |
| `t` | Grabar una prueba de 30 segundos |
| `o` | Mostrar el último MKV de esta sesión, su carpeta, log e informe |
| `u` | Volver a consultar pantallas y audio |
| `w` | Recorrido inicial |
| `!` | Ver el diagnóstico completo |
| `q` o Esc | Salir; avisa de cambios sin guardar |

Las letras distinguen mayúsculas: `d` es carpeta y `D` es quitar capa.
`o` muestra las rutas dentro de la TUI; no abre un reproductor ni el gestor de
archivos. La lista mantiene la semántica actual: la última capa se dibuja encima.

## Cambiar solo un campo

Selecciona una capa y pulsa `e`. Aparece una lista de campos con sus valores
actuales: nombre, archivo(s), sensibilidad del avatar, colocación, visibilidad,
ancho/alto, proporción y X/Y avanzadas. Selecciona **solo** el campo que quieras
cambiar. Después de aplicarlo vuelves a la lista; Esc vuelve al inicio.

No se recorre todo un formulario. Visible y conservar proporción se alternan al
seleccionarlos. Para ancho o alto escribe `-` si quieres dejar esa dimensión
sin especificar y que se derive según las reglas existentes. Desactivar proporción
requiere ambas dimensiones explícitas.

Los errores aparecen en el campo correspondiente o en su diálogo; los de
validación previa a la captura se marcan junto al ajuste y en el estado inferior.
`!` muestra el texto completo si está recortado. Una edición inválida conserva el
valor anterior. Las rutas nuevas se comprueban con el loader Rust sin arrancar
GSR ni crear un contexto gráfico.

## Esquinas y tamaño efectivo

En `c` se ofrecen:

- Superior izquierda.
- Superior derecha.
- Inferior izquierda.
- Inferior derecha.
- Caja máxima, en píxeles.
- Margen, en píxeles.
- X/Y manuales, como opción avanzada.

Primero puedes cambiar tamaño o margen; luego elige la esquina para aplicar.
La colocación rápida activa proporción y usa una caja cuadrada del tamaño elegido.
El ancho y alto **efectivos** los resuelve el mismo código Rust del plugin. Una
imagen de 2:1 dentro de una caja de 300 se coloca como 300×150, no como 300×300.
La fórmula resta el tamaño efectivo al lienzo del monitor, usando redondeo hacia
arriba para dimensiones fraccionarias. Se rechaza un tamaño que no cabe con el
margen indicado; puedes usar X/Y avanzadas para recortes deliberados.

Al abrir una capa existente se intenta reconocer su esquina y margen a partir
de la geometría efectiva; mover una capa que ya está en una esquina no obliga a
volver a introducir su tamaño. Para una capa nueva se propone inferior derecha,
caja de 300 y margen de 20. El avatar comparte la caja basada en reposo con el GIF
de habla, como en el plugin existente.

En 1920×1080, el avatar cuadrado a 300×300 con margen 20 queda en 1600/760. Para
moverlo arriba a la izquierda: selecciona el avatar en Layers, `c`, elige «Superior izquierda»
y Enter. No tienes que escribir X/Y.

El perfil guarda los X/Y calculados, no un nuevo tipo de anclaje. Si cambias de
resolución, actualiza los dispositivos con `u` y vuelve a colocar la capa. Las
posiciones manuales se siguen editando como píxeles desde arriba/izquierda.

## Carpeta y nombre del video

Los dos ajustes están en Output (también accesibles con `d` y `n`):

- `d`: navega a una carpeta y pulsa **Espacio** para usarla. `p` permite escribir
  una ruta, también de una carpeta nueva que se creará al grabar.
- `n`: escribe solo el nombre, por ejemplo `minecraft-{timestamp}.mkv`.
  No se permiten componentes de carpeta en este campo.

Se combinan y guardan en el campo existente, por ejemplo:

```toml
[recording]
output = "recordings/minecraft-{timestamp}.mkv"
```

Así sigue funcionando tu `perfil.toml` y la CLI directa. No se añade otro esquema
ni campos duplicados `folder`/`filename`. `{timestamp}` se sustituye en UTC al
preparar cada captura. El nombre debe terminar en `.mkv`; una salida fija ya usada
se rechaza para no sobrescribirla. En la selección nueva de carpeta no se permiten
plantillas; usa `{timestamp}` en el nombre.

El guardado conserva las reglas existentes de rutas relativas a la carpeta del
TOML, incluso al guardar como otro archivo. No copia gráficos ni mueve los videos.

## Grabar, detener y volver

La TUI ejecuta la validación y el grabador existentes en un hilo de trabajo;
solo el hilo principal usa curses. Durante la captura muestra una **vista mínima
estática** con estado, destino, duración solicitada de la prueba si corresponde
y tecla de parada. No hay contador animado ni redibujado periódico de paneles.
La edición queda bloqueada durante la validación/captura.

- **`x` o Ctrl+C:** pide detener y vuelve a la TUI cuando GSR cierra el archivo.
- **`q` o Esc durante la captura:** pide detener y después salir; si hay cambios
  de perfil, se ofrece guardarlos, descartarlos o seguir editando.
- **`t`:** detiene automáticamente después de aproximadamente 30 segundos.

La parada reutiliza SIGINT a GSR, espera de cierre y comprobaciones por ffprobe.
No mata primero el proceso `parec`, para que GSR y el plugin puedan cerrar sus
recursos ordenadamente. No hay cambios en los buffers, relojes o código Rust de
composición. El detector sigue siendo la segunda captura de la entrada elegida.

Si se detiene mientras valida, se espera a que termine la consulta en curso y se
cancela antes de lanzar GSR. Las consultas a dispositivos tienen sus propios
timeouts: no equivale a cancelar instantáneamente cada llamada nativa.

Cuando hay éxito se muestra el MKV y `o` permite consultar su ubicación completa.
Si falla una captura que llegó a crear archivo, se conserva y se señala como
parcial; si falla una validación antes de grabar, el resultado anterior no se
presenta como una captura nueva. No hay reproducción o previsualización integrada.

## Guardado y salida

`s` guarda en el TOML actual. `S` permite otro nombre y confirma si se reemplaza
un archivo distinto ya existente. El guardado mantiene la normalización existente
(esquema 2 y rutas relativas) y puede reescribir comentarios/formato del TOML.

Al salir o cargar otro perfil con cambios se ofrecen «Guardar cambios»,
«Descartar cambios» y «Seguir editando». Esc conserva la edición. No hay guardado
silencioso de cambios al abrir, cerrar o grabar desde el inicio. El recorrido
inicial sí tiene una acción explícita «Guardar perfil y grabar 30 segundos».

## Reposo de la interfaz y recursos

La pantalla se repinta al recibir entrada, redimensionamiento o un evento del
trabajador, no en cada vuelta del bucle. Durante la captura el hilo principal
espera una tecla con timeout de un segundo para comprobar el fin del trabajo;
las teclas siguen entrando inmediatamente. No consulta ni decodifica recursos
al pintar. Al cerrar GSR vuelve a los paneles y a la selección anterior.

Esto pausa la presentación, no destruye el proceso Python ni libera toda su
memoria. Evita añadir un proceso de control o tener que reconstruir una sesión
para poder volver a la TUI. No hay nuevas dependencias.

Comprobación local orientativa: en ventanas de unos 5 s, el proceso TUI estuvo
alrededor de 22 MiB de RSS y 0,20 % de un núcleo durante captura **simulada**.
La CPU de captura quedó prácticamente igual antes y después en ese muestreo;
el intervalo corto y la resolución del contador no permiten prometer un ahorro
numérico. Son cifras solo de la TUI, no de GSR, helper, detector ni del conjunto,
y no representan una medición de rendimiento en COSMIC con un juego real.

La inicialización usa `curses.wrapper` para restaurar eco/modo de terminal al salir
o propagar un error. SIGTERM también pasa por el cierre de grabación y la
restauración. Referencias: [curses de Python](https://docs.python.org/3/library/curses.html)
y [patrón wrapper](https://docs.python.org/3/howto/curses.html#starting-and-ending-a-curses-application).

## Comando directo conservado

La TUI no sustituye estos comandos:

```bash
python3 scripts/compositor.py check perfil.toml
python3 scripts/compositor.py record perfil.toml --seconds 30
python3 scripts/compositor.py record perfil.toml
```

También sigue disponible el menú clásico `python3 scripts/compositor.py edit`.
Su [manual de referencia](guia-cli.md) describe TOML, requisitos, audio y diagnóstico.
El comando `trama` actual acepta el argumento opcional de perfil, `--lang {auto,es,en}` y `--help`;
no es un paquete publicado ni añade subcomandos de streaming.

## Verificación y límites

La captura real depende de la sesión gráfica, el controlador y el servidor de
audio. Las comprobaciones automatizadas no sustituyen una grabación en el equipo
objetivo.

Pruebas de esta entrega:

- Modelo: esquinas con fuente no cuadrada y tamaño efectivo Rust, avatar y perfil TOML de ejemplo, edición de un campo, carpeta/nombre, guardado/carga, orden,
  oculto, recursos inexistentes, recuperación de sesión y cambios sin guardar.
- Pseudoterminal real: recorrido inicial con selector de archivos, recuperación
  del último perfil, perfil de ejemplo, cambio de esquina sin X/Y,
  guardado, prueba de 30 s, consulta del MKV y retorno a la TUI.
- Pseudoterminal: cambio de nombre y carpeta por separado, error de nombre inválido,
  edición de un solo campo, aviso sin guardar, parada con `x`, SIGINT y SIGTERM.
- Restauración de ECHO/ICANON al salir de las pruebas de terminal.
- Secciones en 72×20, 80×24, 110×30 y 160×40; foco, acciones contextuales y resize.
- Bucle sin repintado al esperar, vista de captura sin paneles ni salida terminal
  periódica, parada y retorno a los paneles.
- Suite anterior conservada. Para ejecutarla completa se necesitan también los
  artefactos de desarrollo `media-dump` y referencia C compilada; no forman parte
  del runtime mínimo. Consulta el [estado de validación](estado.md#validación-automatizada-y-local).

Las pruebas de pseudoterminal usan **dispositivos y capturador simulados**, con
el modelo TOML, decoder Rust, proceso de grabación compartido y MKV sintético real.
El caso de 30 s espera ese tiempo y comprueba la duración del archivo. Los
adaptadores viven en `tests/`; no hay un flag de motor falso en el lanzador.
Las pruebas simuladas no sustituyen captura KMS, audio físico o Minecraft:
se requiere una sesión gráfica con acceso a DRM/KMS y al servidor de audio.

El usuario ya confirmó que la TUI funciona y se ve bien en su laptop, además de
una grabación de 10 minutos. Es confirmación de uso, no una medición instrumentada
ni una prueba del nuevo paquete instalado.

Comandos para repetir las pruebas:

```bash
python3 tests/test_trama.py
python3 tests/test_trama_view.py
python3 tests/test_trama_i18n.py
python3 tests/test_trama_pty.py
python3 tests/test_compositor.py
python3 tests/test_element_cli.py
```

Para repetir la prueba de aceptación en el equipo objetivo:

```bash
./trama perfil.toml
```

Tab a Layers, selecciona el avatar, `c`, otra esquina y Enter; `s` guarda, `t` graba 30 s, y `o`
muestra el archivo final. Comprueba el video, audio, reacción del avatar y retorno
a la TUI. No se publican nuevas cifras de rendimiento ni ventajas frente a OBS.

Código: [entrada trama](../trama), [TUI](../scripts/trama_tui.py),
[modelo y geometría](../scripts/trama_model.py), [grabador compartido](../scripts/compositor.py),
[pruebas de estado](../tests/test_trama.py), [pruebas PTY](../tests/test_trama_pty.py).
