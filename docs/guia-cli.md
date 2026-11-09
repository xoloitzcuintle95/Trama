# Guía de usuario de la CLI del compositor GSR

> Para instalar el nuevo paquete de evaluación, consulta
> [Paquete preliminar](paquete-preliminar.md). Este manual conserva las rutas y
> órdenes de desarrollo desde fuentes; la instalación empaquetada incluye su
> propio motor GSR y se abre con `trama`.


Esta página documenta el **menú clásico y los comandos directos**. La nueva
[TUI Trama tiene su propia guía](tui.md), con edición por campo y colocación por
esquinas. La aplicación se llama Trama; los gráficos incluidos son muestras neutras.
Los perfiles y gráficos personales pueden residir fuera del proyecto.

Manual de referencia del compositor **0.4.0**, plugin `rust-media-overlay` versión
4, sobre **GPU Screen Recorder (GSR) 6.1.7**. Caso principal: Pop!_OS 24.04,
COSMIC/Wayland y codificación por GPU. Los nombres y opciones descritos proceden
del código y de la ayuda real de `scripts/compositor.py`.

El compositor prepara gráficos y un avatar; GSR captura el monitor, graba el
audio, codifica y escribe el video. Se edita antes de grabar, mediante un menú de
texto. No hace falta aprender los comandos internos de GSR para usar un perfil.

## Índice

1. [Inicio rápido: Minecraft con el avatar](#1-inicio-rápido-minecraft-con-el-trama)
2. [Instalación y requisitos](#2-instalación-y-requisitos)
3. [Referencia de comandos](#3-referencia-de-comandos)
4. [Referencia del menú interactivo](#4-referencia-del-menú-interactivo)
5. [Capas, geometría y avatar](#5-capas-geometría-y-avatar)
6. [Referencia de perfiles TOML](#6-referencia-de-perfiles-toml)
7. [Grabación, salida y audio](#7-grabación-salida-y-audio)
8. [Diagnóstico](#8-diagnóstico)
9. [Límites y alcance de las pruebas](#9-límites-y-alcance-de-las-pruebas)
10. [Archivos de referencia](#10-archivos-de-referencia)

## 1. Inicio rápido: Minecraft con el avatar

Este recorrido parte de una copia del proyecto con GSR nativo instalado y el
plugin compilado. Si es tu primera instalación, completa la
[sección de instalación](#2-instalación-y-requisitos) y vuelve aquí.

### 1.1 Abrir la terminal

Abre una terminal dentro de tu sesión COSMIC y entra en la carpeta del proyecto.
Adapta esta ruta a la ubicación de tu copia:

```bash
cd "$HOME/project-gsr-compositor"
```

Comprueba que están los GIF de ejemplo:

```bash
ls -l examples/assets/idle.gif examples/assets/talking.gif
```

Estos archivos sirven como avatar de ejemplo; puedes usar otros. El programa no
exige esos nombres ni ese personaje.

### 1.2 Crear un perfil

Ejecuta, sin `sudo`:

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
```

Si el archivo no existe, se abre un perfil nuevo en memoria. Al abrir el editor
se intentan listar pantallas y micrófonos. Debajo aparece este menú:

```text
1 pantalla | 2 micrófono/audio | 3 salida/FPS | 4 capas/avatar | 5 guardar | 6 cargar | 7 validar/resumen | 8 grabar | 0 salir:
```

Escribe cada tecla y pulsa **Enter**. No uses flechas ni atajos de una TUI.

1. Escribe `1`. Busca el monitor donde vas a jugar y escribe su número. Anota la
   resolución mostrada. El ejemplo de colocación de abajo supone **1920 × 1080**.
2. Escribe `2`. Selecciona `1` para usar el micrófono predeterminado, o el número
   de la entrada de tu micrófono, por ejemplo tu micrófono USB si aparece.
   En `Grabar juego/audio del sistema (s/n) [s]:`, pulsa Enter para mantener `s`.
3. Escribe `3`. En `Archivo MKV, admite {timestamp}`, escribe
   `recordings/{timestamp}.mkv`. En `FPS [30]:`, pulsa Enter.
4. Escribe `4` para entrar en capas y luego `v` para agregar el avatar.

Dentro del formulario del avatar, responde en este orden:

| Pregunta | Qué escribir |
| --- | --- |
| `GIF reposo` | `examples/assets/idle.gif` |
| `GIF habla` | `examples/assets/talking.gif` |
| `Umbral RMS 0..1 (menor = más sensible) [0.04]` | Enter |
| `Espera antes de reposo (ms) [250]` | Enter |
| `Nombre [Avatar]` | `Avatar` |
| `X [32]` | `1600` |
| `Y [32]` | `760` |
| `Ancho (- = automático) [-]` | `300` |
| `Alto (- = automático) [-]` | `300` |
| `Conservar proporción (s/n) [s]` | Enter |
| `Visible (s/n) [s]` | Enter |

En un video de 1920 × 1080, este avatar cuadrado queda abajo a la derecha con
20 píxeles de margen. Si tu resolución es otra, usa la
[fórmula de colocación](#54-avatar-abajo-a-la-derecha).

Escribe `0` para volver al menú principal. Escribe `5` y pulsa Enter en
`Guardar TOML [...]` para guardar en `perfil-minecraft.toml`. Debe aparecer
`Guardado:` con la ruta del perfil.

En las preguntas del menú escribe las rutas **sin comillas de shell**, incluso
si tienen espacios. Por ejemplo: `mis gráficos/idle.gif`. Las comillas sí se usan
en un comando de terminal para proteger un argumento con espacios.

### 1.3 Validar el perfil

Escribe `7`. El programa comprueba recursos y dispositivos y muestra pantalla,
micrófono resuelto, capas, tamaño, visibilidad y salida. Si aparece `Corregir:`,
atiende el valor indicado; una validación fallida no empieza a grabar.

Escribe `0` para salir del editor. También puedes validar desde la terminal:

```bash
python3 scripts/compositor.py check perfil-minecraft.toml
```

### 1.4 Grabar 30 segundos

Abre Minecraft y entra en el mundo que quieres grabar. Vuelve a la terminal y
lanza:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 30
```

Este comando valida, muestra el resumen y empieza sin otra confirmación. Cuando
aparezca `Grabando. Ctrl+C termina y cierra el archivo.`, cambia a Minecraft.
Muévete y habla para comprobar juego, audio y cambio del avatar. También deja un
momento de silencio para comprobar el regreso a reposo.

La captura incluye **todo el monitor seleccionado**, también la terminal mientras
esté visible. No hay cuenta atrás, selección automática de la ventana del juego
ni atajo global de inicio. La duración es aproximada: incluye arranque y se añade
el tiempo necesario para cerrar el archivo.

### 1.5 Encontrar y revisar el video

Al terminar, la terminal muestra:

```text
Guardado: /ruta/del/proyecto/recordings/FECHA.mkv
Log: /ruta/del/proyecto/recordings/FECHA.mkv.gsr.log
Informe: /ruta/del/proyecto/recordings/FECHA.mkv.report.json
```

Con este perfil, creado en la raíz del proyecto, puedes localizarlo con:

```bash
ls -lt recordings/
```

Abre el `.mkv` con tu reproductor. Comprueba imagen del juego, posición y animación
del avatar, sonido del juego, voz y sincronía. Que el CLI indique éxito no sustituye
esa revisión visual y auditiva.

La próxima vez puedes volver a editar el mismo perfil o grabar directamente:

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
python3 scripts/compositor.py record perfil-minecraft.toml
```

El segundo comando graba hasta que vuelvas a la terminal y pulses **Ctrl+C**.

## 2. Instalación y requisitos

### 2.1 Componentes y entorno

| Componente | Para qué se necesita |
| --- | --- |
| Copia del proyecto | Debe incluir `scripts/`, `rust/`, `rust/Cargo.lock`, pruebas y los recursos que vayas a usar |
| Python 3.11 o posterior | CLI y lectura TOML con `tomllib`; aquí se comprobó Python 3.12.3 |
| Rust y Cargo recientes | Compilar el plugin y verificadores; aquí se comprobó Rust 1.99.1. El proyecto no declara una versión mínima de Rust verificada |
| Compilador C, Git y herramientas de construcción | Construcción de GSR y comprobación de ABI C/Rust |
| GSR nativo compatible | Captura, audio, codificación y escritura; debe estar en `PATH` |
| EGL/OpenGL y controlador gráfico funcional | El plugin reutiliza el contexto de GSR; requiere GLES 3 o, en la ruta GLX, GL 3.3 o GL 3 con `ARB_sampler_objects` |
| GPU con H.264 admitido por GSR | El comando exige codificación GPU y no habilita respaldo por CPU |
| Sesión gráfica y acceso a DRM/KMS | Capturar el monitor en COSMIC/Wayland |
| PulseAudio o servicio compatible de PipeWire | Audio del juego y entrada de micrófono |
| `pactl` y `parec` | Consultar entradas y comprobar/capturar el micrófono |
| `ffprobe` | Comprobar los streams del archivo al finalizar |
| Pillow y FFmpeg | Necesarios para la suite completa de pruebas, no para dibujar cada cuadro del plugin |

El plugin usa Rust edición 2024 y APIs de la biblioteca estándar recientes. No
supongas que el Rust del repositorio de tu distribución es suficiente. Una versión
más antigua que la usada aquí requiere comprobar su compilación.

La referencia de GSR está fijada a este commit:

```text
f97d1e392816503282d20a0804c3ce3fd2943767
```

La versión numérica `6.1.7` por sí sola no basta: el CLI compara los hashes del
GSR instalado y del plugin con el manifiesto generado durante el build. Un GSR de
otra compilación puede rechazarse aunque muestre la misma versión.

La instalación descrita usa el código de GSR en `third_party/gpu-screen-recorder`,
separado del código del compositor. No hay un instalador propio del compositor,
un paquete de Python que instalar ni un comando `compositor` registrado globalmente.
Se ejecuta `python3 scripts/compositor.py` desde la copia del proyecto.

### 2.2 Paquetes de Pop!_OS 24.04

Si ya tienes el entorno preparado, comprueba los componentes antes de reinstalar.
Para una instalación nueva, estos comandos son para que los ejecute el usuario;
**modifican el sistema y requieren `sudo`**:

```bash
sudo apt-get update
sudo apt-get install build-essential git curl pkg-config meson ninja-build \
  python3 ffmpeg pulseaudio-utils libcap2-bin \
  libx11-dev libxcomposite-dev libxrandr-dev libxfixes-dev libxdamage-dev \
  libwayland-dev libva-dev libpulse-dev libdrm-dev libcap-dev libdbus-1-dev \
  libvulkan-dev linux-libc-dev libavcodec-dev libavformat-dev libavutil-dev \
  libswresample-dev libavfilter-dev libswscale-dev libglvnd-dev
```

Para las pruebas que usan Pillow:

```bash
sudo apt-get install python3-pil
```

La lista corresponde a las dependencias del código GSR inspeccionado y a los
paquetes de la base Ubuntu 24.04 de Pop!_OS. Las versiones y disponibilidad
concretas dependen de tus repositorios. `pulseaudio-utils` aporta las herramientas
de cliente; usarlo no requiere sustituir PipeWire por un servidor PulseAudio.
Véase la [ficha oficial del paquete](https://packages.ubuntu.com/noble/pulseaudio-utils).

El controlador de codificación depende de la GPU. En el equipo Intel de referencia
se encontró `intel-media-va-driver`; eso no prueba que funcione en otra máquina.
Comprueba primero `gpu-screen-recorder --info`. No hay una selección o instalación
automática de drivers en el compositor.

### 2.3 Preparar Rust

Comprueba:

```bash
rustc --version
cargo --version
```

Si falta Rust, el [instalador oficial mediante rustup](https://rust-lang.org/tools/install/)
ofrece este comando para Linux, ejecutado como usuario normal:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Después abre otra terminal o carga el entorno:

```bash
. "$HOME/.cargo/env"
rustc --version
cargo --version
```

Sigue las indicaciones del instalador. No se necesita `sudo` para instalar la
toolchain en tu cuenta. Esta guía no instala ni actualiza nada automáticamente.

### 2.4 Obtener y compilar GSR

Trabaja desde la raíz de tu copia del compositor. Si las fuentes de GSR **ya
están**, empieza comprobando el commit:

```bash
git -C third_party/gpu-screen-recorder rev-parse HEAD
```

Para una copia nueva que todavía no tenga esa carpeta:

```bash
mkdir -p third_party
git clone https://repo.dec05eba.com/gpu-screen-recorder third_party/gpu-screen-recorder
git -C third_party/gpu-screen-recorder checkout --detach f97d1e392816503282d20a0804c3ce3fd2943767
```

No cambies de commit en un árbol con trabajo propio sin revisarlo. El script Rust
rechaza otra referencia o modificaciones en la cabecera/cargador/recorder que
utiliza para verificar la ABI.

Para configurar y compilar GSR por primera vez, sin privilegios:

```bash
bash scripts/prepare-gsr.sh
```

Este script configura release con prefijo `/usr/local`, FFmpeg del sistema,
portal y audio por aplicación desactivados, sin ejemplos de plugins, servicio
systemd ni ajuste de suspensión de NVIDIA. Si aún no existe la carpeta de GSR,
el script la clonaría por su cuenta; para respetar el commit esperado, prepara
antes la copia fijada como se muestra arriba.

Si ya hay un build configurado, recompílalo sin volver a hacer el setup inicial:

```bash
meson compile -C third_party/gpu-screen-recorder/build
```

### 2.5 Instalar GSR nativo

Después de compilar, el paso de instalación requiere privilegios:

```bash
sudo meson install -C third_party/gpu-screen-recorder/build
```

Con el prefijo anterior instala GSR y su helper en `/usr/local/bin`. El script
oficial de posinstalación asigna `cap_sys_admin+ep` a `gsr-kms-server` para KMS.
Ese privilegio corresponde al helper de GSR, no al compositor. No ejecutes la
CLI Python con `sudo` ni asignes capacidades a nuestro plugin.

El `install.sh` antiguo de GSR está deprecado y recrea el build con otras opciones;
esta guía usa Meson directamente. No hace falta instalar Flatpak para este flujo:
el CLI actual busca un ejecutable nativo en `PATH` y carga nuestro `.so` local.

Comprueba:

```bash
command -v gpu-screen-recorder
gpu-screen-recorder --version
command -v gsr-kms-server
getcap "$(command -v gsr-kms-server)"
```

La capacidad esperada para el helper de esta instalación es `cap_sys_admin=ep`.
Si no aparece o el acceso KMS falla, revisa el resultado de la instalación de GSR.

### 2.6 Compilar el compositor

Desde la raíz del proyecto, descarga primero las dependencias Cargo si la cuenta
no tiene caché. Este paso requiere red, pero no `sudo`:

```bash
cargo fetch --manifest-path rust/Cargo.toml --locked
```

Después:

```bash
bash scripts/build-rust-overlay.sh
```

El script compila con `--offline --locked`, compara la ABI con la cabecera C y
genera, entre otros:

```text
build/overlay-rust.so
build/overlay-rust.build.json
build/rust-target/release/scene-check
build/rust-target/release/element-check
```

Necesita también el binario local
`third_party/gpu-screen-recorder/build/gpu-screen-recorder`: su hash se registra
en el manifiesto. El GSR instalado que encuentra la CLI debe coincidir con él.
Si recompilas GSR, normalmente tendrás que instalar ese build y regenerar el
manifiesto del plugin para mantener la correspondencia.

No hay que instalar el plugin en `/usr/lib`: la CLI carga
`build/overlay-rust.so` por su ruta conocida. Conserva el árbol del proyecto y
sus artefactos; copiar solo `compositor.py` a otra carpeta no prepara el programa.

### 2.7 Comprobaciones antes del primer uso

```bash
python3 --version
command -v pactl
command -v parec
command -v ffprobe
ls -l build/overlay-rust.so build/overlay-rust.build.json \
  build/rust-target/release/scene-check
python3 scripts/compositor.py --help
python3 scripts/compositor.py check examples/perfil.toml --assets-only
```

El último comando valida los GIF y la configuración del ejemplo, sin exigir una
pantalla elegida. Sigue necesitando GSR nativo y los artefactos de build correctos.

En una terminal de tu sesión COSMIC, comprueba también:

```bash
ls -l /dev/dri
gpu-screen-recorder --info
gpu-screen-recorder --list-capture-options
gpu-screen-recorder --list-audio-devices
pactl info
python3 scripts/compositor.py devices
```

La disponibilidad real depende del controlador, acceso a DRM/KMS, sesión Wayland,
servidor de audio y dispositivos conectados. Una sesión SSH, contenedor o terminal
sin acceso a la sesión gráfica puede compilar el proyecto y aun así no capturar.

## 3. Referencia de comandos

Todas las sintaxis siguientes se ejecutan desde la raíz del proyecto. Si estás
en otra carpeta, utiliza la ruta completa al script. Una ruta de perfil relativa
en el comando se interpreta desde el directorio actual de la terminal.

### 3.1 Ayuda

```text
python3 scripts/compositor.py [-h] {devices,edit,check,record} ...
```

`-h` y `--help` imprimen la ayuda y terminan. Están disponibles tanto en el
programa principal como en cada subcomando:

```bash
python3 scripts/compositor.py --help
python3 scripts/compositor.py devices --help
python3 scripts/compositor.py edit --help
python3 scripts/compositor.py check --help
python3 scripts/compositor.py record --help
```

No existe `--version` en esta CLI. La versión de GSR se consulta con
`gpu-screen-recorder --version`; la versión del compositor figura en
[`rust/Cargo.toml`](../rust/Cargo.toml).

### 3.2 Sin subcomando

```bash
python3 scripts/compositor.py
```

Abre el editor con un perfil **nuevo**, basado en el directorio actual. No carga
por sí solo `perfil.toml`, aunque ese archivo exista. Al guardar propondrá
`perfil.toml` en el directorio actual. No hay guardado automático.

### 3.3 `devices`

```text
python3 scripts/compositor.py devices [-h]
```

Lista monitores anunciados por GSR, micrófonos con identificador y descripción,
y disponibilidad de `default_output`. No tiene argumentos ni opciones de captura.

```bash
python3 scripts/compositor.py devices
```

Los nombres y el orden dependen de tu equipo. Que aparezca la opción
`default_input` no demuestra que el predeterminado actual sea válido; se resuelve
y comprueba antes de grabar. Este comando no necesita tener un perfil ni valida
el plugin como lo hace `check`.

### 3.4 `edit`

```text
python3 scripts/compositor.py edit [-h] [profile]
```

| Argumento | Obligatorio | Comportamiento |
| --- | --- | --- |
| `profile` | No | Si existe, carga el TOML. Si no existe, prepara uno nuevo asociado a esa ruta. Sin argumento, abre uno nuevo basado en el directorio actual |

```bash
python3 scripts/compositor.py edit perfil-minecraft.toml
python3 scripts/compositor.py edit "perfiles/desarrollo diario.toml"
python3 scripts/compositor.py edit
```

Un TOML existente inválido produce error; no se reemplaza silenciosamente por uno
nuevo. El editor permite guardar aunque no haya podido consultar dispositivos,
pero no omite la validación al iniciar una grabación.

### 3.5 `check`

```text
python3 scripts/compositor.py check [-h] [--assets-only] profile
```

| Argumento u opción | Predeterminado | Efecto |
| --- | --- | --- |
| `profile` | Sin valor; obligatorio | TOML existente que se quiere validar |
| `--assets-only` | Desactivado | Omite consulta de pantallas y audio; comprueba configuración, recursos, build y ruta de salida |

```bash
python3 scripts/compositor.py check perfil-minecraft.toml
python3 scripts/compositor.py check examples/perfil.toml --assets-only
```

El modo normal verifica compatibilidad del build, H.264 GPU/MKV anunciados por
GSR, monitor elegido, audio configurado, muestras del micrófono, decodificación
real de recursos, geometría, presupuesto de píxeles y destino de salida.
Comprobar el micrófono abre una captura breve para confirmar que entrega datos;
no guarda ese audio en un archivo.

`--assets-only` no comprueba hardware, permisos efectivos de captura ni audio.
Muestra `SOLO RECURSOS: pantallas, audio y captura no comprobados.`. No equivale a
una prueba completa de grabación ni a una previsualización.

`check` no crea un video ni la carpeta de salida. El timestamp de su resumen
corresponde a esa validación; un posterior `record` genera otro nombre.

### 3.6 `record`

```text
python3 scripts/compositor.py record [-h] [--seconds SECONDS] profile
```

| Argumento u opción | Predeterminado | Efecto |
| --- | --- | --- |
| `profile` | Sin valor; obligatorio | Carga y valida este TOML antes de grabar |
| `--seconds SECONDS` | Sin duración fija | Segundos aproximados desde el lanzamiento de GSR; acepta números entre 1 y 7200, incluidos decimales |

Prueba de 30 segundos:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 30
```

Diez minutos:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml --seconds 600
```

Sin parada automática:

```bash
python3 scripts/compositor.py record perfil-minecraft.toml
```

Después del resumen empieza directamente, sin menú ni pregunta de confirmación.
Para terminar antes del plazo, o cuando no hay plazo, vuelve a esa terminal y pulsa
**Ctrl+C**. Espera a que aparezca `Guardado:` o el diagnóstico de error. El cierre
normal envía SIGINT a GSR y espera hasta 15 segundos; si no termina, el programa
fuerza la salida y marca el resultado incompleto. No cierres la terminal ni uses
SIGKILL como forma habitual de detenerlo.

La opción de duración pertenece a este subcomando. El menú no tiene un campo
«duración». No existe pausa/reanudación ni tecla global para parar desde Minecraft.

### 3.7 Códigos de salida y alcance de las opciones

| Código | Significado habitual |
| --- | --- |
| `0` | Comando completado, o salida normal del menú |
| `2` | Error de argumentos, perfil, dispositivos, build o grabación detectado por la CLI |
| `130` | Interrupción/fin de entrada capturado en el nivel principal, por ejemplo Ctrl+C en el menú |

Ctrl+C durante `record` se maneja como una petición de cierre: puede acabar con
código `0` si el archivo cierra correctamente. En el menú, los errores de una
acción se muestran y el editor continúa; un posterior `0` no certifica que todas
las acciones previas hayan funcionado.

Los cuatro subcomandos anteriores son toda la CLI de escenas actual. No existen
opciones `--screen`, `--mic`, `--output`, `--fps`, `--preview`, `--scene` o
`--avatar` en `compositor.py`: esos valores se editan en el menú o en TOML.
Los scripts anteriores de elemento único tienen sus propias opciones y no deben
confundirse con esta interfaz; véase [configuración de un elemento](configuracion-elemento.md).

## 4. Referencia del menú interactivo

### 4.1 Reglas de entrada

El menú es un conjunto de preguntas de texto, no una pantalla navegable con
flechas. Después de cada respuesta pulsa Enter.

| Tipo de pregunta | Significado de Enter |
| --- | --- |
| Formulario con valor entre `[...]` | Conserva ese valor |
| Pregunta `(s/n)` | Conserva `s` o `n` mostrado entre corchetes |
| Selección numerada de pantalla, micrófono o capa | Debes escribir un número; Enter vacío no selecciona la primera opción |
| Acción del menú principal o de capas | Enter vacío no vuelve ni confirma: muestra opción desconocida o vuelve a pedir una acción |
| `TOML a cargar:` o `Nueva posición 1..N:` | Requiere escribir la ruta o el número; no tiene predeterminado |

En preguntas `(s/n)` se aceptan `s` y `n`, también en mayúscula. `sí`, `yes` y `y`
no son respuestas admitidas. Las letras de las acciones de capas se escriben en
minúscula. No hay una tecla general para cancelar un formulario a mitad: Ctrl+C
sale del editor completo y no guarda los cambios. Ctrl+D al pedir entrada también
cierra el programa sin guardar.

Los números son enteros salvo el umbral RMS, que admite decimales. Usa punto
(`0.04`), no coma (`0,04`). No escribas unidades, comillas ni el símbolo `%`.

### 4.2 Apertura y menú principal

Al iniciar se intentan consultar dispositivos. Si la consulta falla, se informa y
se permite continuar editando/guardando. La cabecera muestra perfil, pantalla,
micrófono y cantidad de capas, seguida del menú principal.

| Tecla | Acción |
| --- | --- |
| `1` | Pantalla |
| `2` | Micrófono y audio del sistema |
| `3` | Archivo de salida y FPS |
| `4` | Capas y avatar |
| `5` | Guardar perfil |
| `6` | Cargar otro perfil |
| `7` | Validar y mostrar resumen |
| `8` | Validar, mostrar resumen e iniciar una grabación si confirmas |
| `0` | Salir del programa |

Salir o cargar otro perfil no guarda automáticamente los cambios ni pregunta por
ellos. Guarda con `5` antes si quieres conservarlos. El menú no cambia escenas en
una grabación que ya esté en curso.

### 4.3 `1`: pantalla

Se consulta de nuevo la lista de GSR. Cada opción muestra nombre de monitor y
resolución, por ejemplo `MONITOR-1: 1920×1080`.

En `Pantalla (número):` escribe el número de la lista actual. No escribas ahí el
nombre del monitor. El perfil guarda el nombre, no su número de orden.

Vuelve al menú principal después de elegir. No hay un `0` para cancelar dentro
de esta selección; `0` es un número fuera de la lista. Solo se ofrecen monitores,
aunque GSR tenga otras modalidades como ventanas, regiones o portal.

### 4.4 `2`: micrófono y audio

La lista empieza con estas opciones:

```text
1. Predeterminado del sistema
2. Sin micrófono (requiere no tener avatar)
```

Después aparecen las entradas concretas consultadas en ese momento. En
`Micrófono (número):` escribe el número deseado. En esta selección, `2` significa
«sin micrófono»; no es la tecla del menú principal para entrar a audio.

Se pregunta a continuación:

```text
Grabar juego/audio del sistema (s/n) [s]:
```

El valor mostrado puede ser `[n]` si el perfil ya lo tenía desactivado. Responde
`s`, `n` o Enter para mantenerlo. Luego vuelve al menú principal.

Un avatar necesita micrófono incluso si está oculto. Para grabar sin micrófono,
quita la capa avatar; ocultarla no basta. Puedes tener micrófono grabado sin avatar.

### 4.5 `3`: salida y FPS

Las preguntas aparecen en este orden:

1. `Archivo MKV, admite {timestamp} [...]`: ruta del archivo, no solo una carpeta.
2. `FPS [...]`: entero entre `1` y `120`, predeterminado `30`.

Ejemplo de respuesta al archivo:

```text
recordings/minecraft-{timestamp}.mkv
```

La extensión debe ser `.mkv` en minúsculas. No se ofrece selección de contenedor.
La ruta relativa se interpreta desde la carpeta base del perfil. Las carpetas que
falten se crean al grabar. La opción no modifica la resolución del monitor ni el
límite de FPS de Minecraft.

### 4.6 `4`: capas y avatar

Primero se muestra:

```text
Capas (primera = fondo):
```

Cada fila incluye número, nombre, tipo (`graphic` o `avatar`) y visibilidad.
Después:

```text
a agregar gráfico | v agregar avatar | e editar/reemplazar | o ocultar/mostrar | q quitar | r reordenar | 0 volver:
```

| Tecla | Qué hace |
| --- | --- |
| `a` | Agrega una capa gráfica PNG/JPG/GIF al final, por encima de las anteriores |
| `v` | Agrega un avatar al final; solo puede haber uno |
| `e` | Pide un número de capa y abre su formulario para editarla o reemplazar archivos |
| `o` | Pide una capa y alterna visible/oculta inmediatamente en la configuración en memoria |
| `q` | Pide una capa y la elimina de la configuración; no borra el archivo gráfico del disco |
| `r` | Pide una capa y luego `Nueva posición 1..N:`; la mueve a ese lugar del listado |
| `0` | Vuelve al menú principal |

`q` significa **quitar**, no salir del submenú. Las selecciones de capa son
numeradas desde `1`. El orden del listado define el orden de dibujo; no hay otro
campo independiente de profundidad o `z-index`.

#### Formulario de gráfico: `a` o `e` sobre `graphic`

Las preguntas van en este orden:

1. `Ruta PNG/JPG/GIF [...]`.
2. `Nombre [...]`.
3. `X [...]`.
4. `Y [...]`.
5. `Ancho (- = automático) [...]`.
6. `Alto (- = automático) [...]`.
7. `Conservar proporción (s/n) [...]`.
8. `Visible (s/n) [...]`.

Para un gráfico nuevo el nombre inicial del menú es `Gráfico`, X/Y son `32`,
ancho y alto están sin especificar (`-`), proporción y visibilidad valen `s`.
Introduce una ruta real al agregar: Enter en una ruta vacía no elige un archivo.

En una capa existente, pulsa Enter para mantener su archivo. Para sustituirlo,
escribe la nueva ruta, que puede ser de otro de los formatos soportados. La capa
sigue siendo de tipo `graphic`; no se convierte en avatar desde ese formulario.

#### Formulario de avatar: `v` o `e` sobre `avatar`

Las preguntas van en este orden:

1. `GIF reposo [...]`.
2. `GIF habla [...]`.
3. `Umbral RMS 0..1 (menor = más sensible) [...]`.
4. `Espera antes de reposo (ms) [...]`.
5. `Nombre [...]`.
6. `X [...]`.
7. `Y [...]`.
8. `Ancho (- = automático) [...]`.
9. `Alto (- = automático) [...]`.
10. `Conservar proporción (s/n) [...]`.
11. `Visible (s/n) [...]`.

Los valores iniciales del menú son nombre `Avatar`, umbral `0.04`, espera `250`,
X/Y `32`, dimensiones automáticas, proporción y visibilidad activadas. Escribe
ambas rutas al agregar. Reposo y habla son archivos GIF, no capas separadas.

Después de terminar un formulario vuelve al submenú de capas. La configuración
se comprueba estructuralmente, pero el archivo se decodifica al validar/grabar;
que una ruta quede en el listado no significa que ya se haya podido cargar.

### 4.7 `5`: guardar

Pregunta:

```text
Guardar TOML [ruta/propuesta/perfil.toml]:
```

Enter conserva la ruta propuesta. Si no había un nombre asociado, propone
`perfil.toml` en el directorio actual. Puedes escribir otro archivo, también en
otra carpeta. Las rutas relativas del **archivo TOML a guardar** se interpretan
desde el directorio de la terminal.

Se crean las carpetas necesarias y se reemplaza el TOML mediante un archivo
temporal. Si el perfil ya existe, se sobrescribe sin otra confirmación. El
contenido se normaliza a esquema 2; se reescribe y no conserva los comentarios ni
la presentación original del archivo. Guardar no copia los recursos gráficos.

### 4.8 `6`: cargar

Pregunta:

```text
TOML a cargar:
```

Escribe una ruta a un TOML existente. No hay archivo predeterminado para Enter.
Una ruta relativa se busca desde el directorio actual de la terminal. Si carga
correctamente, sustituye la configuración en memoria y vuelve al menú principal.
Los cambios anteriores sin guardar se descartan sin confirmación.

### 4.9 `7`: validar y mostrar resumen

No pregunta más valores. Si todo se valida, muestra pantalla/resolución/FPS,
micrófono técnico resuelto, audio del sistema, capas en orden, archivos,
coordenadas, dimensiones efectivas, visibilidad, sensibilidad del avatar,
presupuesto RGBA y salida. Luego vuelve al menú principal.

No abre una previsualización ni empieza a grabar. Una ruta de salida con timestamp
puede cambiar al validar de nuevo. Un error se presenta como `Corregir:` y permite
volver a editar.

### 4.10 `8`: grabar y `0`: salir

`8` repite la validación completa y muestra el resumen. Después pregunta:

```text
Iniciar grabación (s/n) [n]:
```

Enter o `n` no empiezan; `s` inicia la captura. Esta grabación no tiene duración
fijada desde el menú: vuelve a la terminal y pulsa Ctrl+C para terminar. Cuando
acaba el cierre, regresa al menú principal. Para volver a grabar con ajustes,
edítalos antes de iniciar otra captura. Los cambios en memoria usados para grabar
no se guardan automáticamente en TOML.

`0` en el menú principal sale del programa. No confundirlo con `0` en capas, que
solo vuelve un nivel.

## 5. Capas, geometría y avatar

### 5.1 Agregar, reemplazar y ordenar

El conjunto de capas del perfil es la escena actual. Se admiten gráficos y un
avatar. No hay biblioteca de varias escenas, transiciones ni cambio de escena en
vivo.

Para agregar, entra en `4` y usa `a` o `v`. Para reemplazar un gráfico, usa `e`,
elige su número y cambia `Ruta PNG/JPG/GIF`; conserva con Enter los demás valores
que no quieras tocar. Para reemplazar los GIF del avatar, edita sus rutas dentro
de la misma capa.

Mover o escalar significa editar X/Y/ancho/alto mediante `e`. Ocultar significa
`o` o `Visible = n`. Quitar significa `q`. Reordenar significa `r`: la posición
`1` queda debajo de las demás y la última queda encima. Una imagen opaca grande
en una capa superior puede tapar otras.

No hay una opción para duplicar capas ni para cambiar el tipo de una capa. Puedes
agregar otra con el mismo archivo, o quitar y crear el tipo deseado. Las fuentes
repetidas no se deduplican en memoria.

### 5.2 Coordenadas y tamaño

El origen `(0, 0)` está en la **esquina superior izquierda del video**. X crece
hacia la derecha; Y crece hacia abajo. Son píxeles del lienzo grabado, no del
archivo original ni de la ventana de la terminal.

La CLI captura el monitor elegido a su resolución de captura; no expone una
resolución de salida independiente. Cambiar el monitor, su resolución o su
orientación puede exigir cambiar las posiciones. Un ancho de capa de `300` es el
tamaño del gráfico, no una petición de video de 300 píxeles.

| Dimensiones configuradas | Resultado con proporción activada |
| --- | --- |
| Ninguna | Ancho 320; altura derivada del archivo |
| Solo `width` | Deriva la altura |
| Solo `height` | Deriva el ancho |
| Ambas | Escala uniforme para caber dentro de esa caja |

La caja se alinea en X/Y por arriba/izquierda; no se centra automáticamente ni se
rellena recortando la imagen. Por ejemplo, un GIF cuadrado con ancho `300` y alto
`200` se dibuja a **200 × 200**. Puede sobrar espacio a derecha/abajo de la caja
solicitada.

En el menú, `-` elimina una dimensión explícita. No escribas `0`: es inválido.
Para deformar, responde `n` a conservar proporción y especifica ancho y alto.
Coordenadas permitidas: enteros de `-16384` a `16384`. Dimensiones explícitas:
enteros de `1` a `16384`. Las derivadas también deben ser positivas y no superar
16384; pueden ser fraccionarias.

Se permite colocar parte del gráfico fuera del cuadro con X/Y negativos.
OpenGL recorta lo que quede fuera; no mueve la capa automáticamente para hacerla
visible. Una capa completamente fuera puede validar correctamente y no aparecer.

### 5.3 Formatos, transparencia y animación

| Formato | Comportamiento |
| --- | --- |
| PNG | Imagen estática; admite transparencia y alfa parcial |
| JPG/JPEG | Imagen estática opaca; no admite transparencia |
| GIF | Animación con transparencia, tiempos por cuadro, disposal y repetición |

El formato se reconoce por el contenido, no solo por la extensión. APNG, video,
SVG y texto no están soportados. No hay selector de opacidad, chroma key,
filtros, rotación ni edición del recurso dentro del programa.

El alfa del recurso se mezcla sobre la captura. Eso no convierte el video MKV en
un video con fondo transparente. En GIF, la transparencia es la definida por su
paleta; para bordes con alfa parcial usa PNG.

Los GIF se precargan y se componen respetando cuadros parciales y disposal. Un
bucle infinito continúa; al terminar una repetición finita se mantiene el último
cuadro. Un GIF sin extensión de repetición se reproduce una vez. Si la demora de
un cuadro es cero o no está indicada, la política actual usa **100 ms**; las demás
se convierten desde las unidades de 10 ms del GIF. No hay control de velocidad o
bucle en el menú: se toma del archivo.

Una capa oculta sigue validándose y mantiene su caché y texturas. Ocultarla no
permite usar un archivo inexistente o malformado, ni evita el presupuesto de
memoria. Para dejar de cargarla, quítala del perfil.

### 5.4 Avatar abajo a la derecha

Para un lienzo `W × H`, un elemento efectivo de `w × h` y un margen `m`:

```text
X = W - w - m
Y = H - h - m
```

En **1920 × 1080**, con el avatar cuadrado de **300 × 300** y margen **20**:

```toml
x = 1600
y = 760
width = 300
height = 300
keep_aspect = true
```

Estas son coordenadas explícitas, no un anclaje. No existe `bottom-right`, un
porcentaje de posición o un ajuste automático al cambiar de resolución. Usa las
dimensiones efectivas mostradas en el resumen para hacer el cálculo. Si el propio
GIF contiene márgenes transparentes, el dibujo visible puede quedar más separado
del borde que su lienzo.

### 5.5 Reposo, habla, umbral y espera

El avatar ocupa una sola posición del listado y comparte X/Y, tamaño y visibilidad
entre `idle` y `talking`. Ambos archivos deben ser GIF, pero sus lienzos pueden
tener dimensiones diferentes. La geometría de reposo determina la caja común;
cada fuente cabe dentro de ella manteniendo su proporción. Si difieren las
proporciones, puede quedar espacio sin dibujar. Con proporción desactivada se
estiran a la caja explícita.

El detector mide amplitud RMS, no reconoce palabras:

- `threshold` es el nivel mínimo para activar habla: mayor que `0` y hasta `1`.
- El predeterminado es `0.04`. Bajarlo aumenta la sensibilidad; subirlo la reduce.
- `release_ms` es el tiempo desde el último bloque sobre el umbral antes de volver
  a reposo: entre `0` y `5000` ms, predeterminado `250`.
- El audio del detector es mono float32 a 16 kHz, evaluado en bloques de 20 ms.
  Esa frecuencia no fija la del audio grabado por GSR.
- Al cambiar de reposo a habla o viceversa, el GIF entrante reinicia su reloj.
  Mientras permanece seleccionado, sigue sus propios tiempos y bucle.

Para ajustar: graba una prueba corta con silencio, voz normal y teclado. Si no
activa, baja gradualmente el umbral; si se activa con ruido, súbelo. Si cambia de
estado demasiado rápido entre frases, aumenta la espera. No hay medidor de nivel,
calibración automática, reconocimiento de voz ni temblor en la versión actual.
Teclado, ventilador, música captada por el micrófono y ruido pueden activar habla.

## 6. Referencia de perfiles TOML

### 6.1 Ejemplo completo

Este perfil es sintáctica y estructuralmente válido. Para grabar debes elegir un
nombre real de pantalla y tener los archivos indicados. Guárdalo, por ejemplo,
como `perfil.toml` en la raíz del proyecto, utilizando los gráficos neutros
incluidos en `examples/assets/`:

```toml
schema_version = 2

[recording]
screen = "NOMBRE_DE_TU_MONITOR"
output = "recordings/minecraft-{timestamp}.mkv"
fps = 30
game_audio = true
microphone = "default_input"

# Primera capa: muestra geométrica debajo del avatar.
[[layers]]
name = "Marco"
kind = "graphic"
path = "examples/assets/overlay.png"
x = 20
y = 20
width = 400
height = 120
keep_aspect = true
visible = true

# Última capa: encima del marco.
[[layers]]
name = "Avatar"
kind = "avatar"
idle = "examples/assets/idle.gif"
talking = "examples/assets/talking.gif"
x = 1600
y = 760
width = 300
height = 300
keep_aspect = true
visible = true
threshold = 0.04
release_ms = 250
```

`NOMBRE_DE_TU_MONITOR` es un marcador, no un dispositivo válido. Elígelo desde el
menú o reemplázalo por un identificador de `devices`. Si solo quieres el avatar,
quita por completo el primer bloque `[[layers]]`; no dejes una capa oculta con un
archivo de ejemplo que no existe.

También está el [perfil de avatar incluido](../examples/perfil.toml). Su pantalla
está vacía a propósito para que la elijas en tu equipo; no pasa la validación de
dispositivos hasta configurarla.

### 6.2 Campos de nivel superior

| Campo | Obligatorio | Predeterminado y reglas |
| --- | --- | --- |
| `schema_version` | No, pero conviene escribirlo | Si se omite se interpreta como versión 1 y se importa; al guardar se escribe `2`. Se admiten enteros `1` y `2` |
| `[recording]` | No | Si se omite se usan los valores de la tabla siguiente; hay que elegir pantalla antes de grabar |
| `[[layers]]` | No | Cero o más tablas ordenadas; hasta 16 capas, con un máximo de un avatar |

No añadas claves inventadas. Se rechazan campos desconocidos. `_base` es un dato
interno del programa y no debe incluirse en un perfil de usuario.

### 6.3 Campos de `[recording]`

| Campo | Tipo | Predeterminado | Reglas |
| --- | --- | --- | --- |
| `screen` | Texto | `""` | Nombre de monitor anunciado por GSR; vacío requiere elegir uno antes de grabar |
| `output` | Texto | `"recordings/{timestamp}.mkv"` | Archivo con extensión `.mkv`, ruta absoluta o relativa al TOML |
| `fps` | Entero | `30` | De 1 a 120 |
| `game_audio` | Booleano | `true` | Captura la salida de audio predeterminada del sistema |
| `microphone` | Texto | `"default_input"` | Predeterminado, identificador explícito de entrada o `""` para desactivar |

El valor heredado `screen = "screen"` se convierte al monitor concreto cuando
solo hay uno disponible. Con varios se rechaza por ambigüedad y exige elegir.
No uses ese alias para indicar «la pantalla donde lancé la terminal».

### 6.4 Campos comunes de una capa

| Campo | Tipo | Predeterminado | Reglas |
| --- | --- | --- | --- |
| `name` | Texto | `"Capa N"`, N empieza en 1 | Entre 1 y 128 bytes UTF-8; es una etiqueta, no una ruta |
| `kind` | Texto | `"graphic"` | `"graphic"` o `"avatar"` |
| `x` | Entero | `32` | Entre -16384 y 16384 |
| `y` | Entero | `32` | Entre -16384 y 16384 |
| `width` | Entero, opcional | Sin dimensión explícita | De 1 a 16384; participa en las reglas de proporción |
| `height` | Entero, opcional | Sin dimensión explícita | De 1 a 16384 |
| `keep_aspect` | Booleano | `true` | Si es `false`, exige ancho y alto explícitos |
| `visible` | Booleano | `true` | `false` conserva la capa cargada sin dibujarla |

En TOML escribe `true`/`false`, no `s`/`n`. Para una dimensión automática omite la
línea correspondiente: `width = "-"`, `width = 0` y `width = null` no son válidos.
Si omites ambas, el ancho efectivo por defecto es 320. Los nombres iniciales del
menú (`Gráfico`, `Avatar`) pueden diferir del nombre generado al omitirlo en TOML.

### 6.5 Campos de gráfico y de avatar

Para `kind = "graphic"`:

| Campo | Obligatorio | Uso |
| --- | --- | --- |
| `path` | Sí | Ruta a un PNG, JPG o GIF cargable |

No incluyas `idle`, `talking`, `threshold` ni `release_ms` en un gráfico.

Para `kind = "avatar"`:

| Campo | Obligatorio | Predeterminado y uso |
| --- | --- | --- |
| `idle` | Sí | Ruta al GIF de reposo |
| `talking` | Sí | Ruta al GIF de habla |
| `threshold` | No | `0.04`; número finito mayor que cero y hasta uno |
| `release_ms` | No | `250`; entero de 0 a 5000 ms |

No incluyas `path` en un avatar. `recording.microphone` no puede estar vacío si hay
un avatar, incluso si `visible = false`. El orden de los bloques `[[layers]]`
determina el orden de dibujo; no existe un campo `order`.

### 6.6 Rutas y nombres de salida

Hay dos bases distintas:

| Dónde se introduce la ruta | Base de una ruta relativa |
| --- | --- |
| Argumento `profile` del comando | Directorio actual de la terminal |
| `Guardar TOML` y `TOML a cargar` del menú | Directorio actual de la terminal |
| `path`, `idle`, `talking`, `recording.output` dentro de un perfil | Carpeta del TOML |
| Rutas de recursos/salida introducidas en el editor | Carpeta base del perfil; sin nombre de perfil, empieza siendo el directorio actual |

Se aceptan rutas absolutas y expansión de `~`. No se expanden variables como
`$HOME` escritas dentro del TOML o de una respuesta del menú: usa `~` o la ruta
real. En un comando de shell, `$HOME` sí lo expande la shell cuando corresponde.

Ejemplo: si el perfil es `perfiles/minecraft.toml` y contiene
`idle = "assets/idle.gif"`, se busca `perfiles/assets/idle.gif`, no
`examples/assets/idle.gif` en la raíz del proyecto. Ejecutar el script desde otra carpeta no
cambia esa interpretación.

Al guardar, el programa escribe rutas relativas a la ubicación nueva del TOML,
conservando el destino real. «Guardar como» en otra carpeta puede introducir
`../`: no traslada las imágenes ni cambia automáticamente la carpeta efectiva
de videos. Después de guardar, las nuevas rutas relativas que introduzcas usan
la nueva carpeta del perfil como base.

`{timestamp}` se sustituye por fecha y hora UTC con microsegundos al preparar la
captura, con formato como `20261109T041847.260757Z`. No es una variable de shell.
Es la única plantilla admitida: no existen `{scene}`, `{game}` o `{counter}`.
Un nombre fijo funciona, pero la siguiente captura se rechaza si ya existe el
video o sus archivos de log/informe. No hay sobrescritura automática de videos.

### 6.7 Reutilizar y compartir

Para compartir un perfil con sus gráficos, conserva una estructura relativa:

```text
mi-perfil/
  perfil.toml
  assets/
    marco.png
    idle.gif
    talking.gif
  recordings/
```

En ese TOML usa `assets/marco.png`, `assets/idle.gif`, `assets/talking.gif` y
`recordings/{timestamp}.mkv`. Copia toda la carpeta. Las fuentes no se incrustan
en el TOML ni en un paquete del compositor.

En la otra máquina abre el editor, elige su pantalla y micrófono, guarda y valida.
Los identificadores de hardware de un equipo no son portables. Un perfil y sus
imágenes tampoco incluyen el programa, el GSR nativo ni sus drivers.

Para reutilizar sin cambiar archivos:

```bash
python3 scripts/compositor.py edit mi-perfil/perfil.toml
python3 scripts/compositor.py record mi-perfil/perfil.toml --seconds 30
```

### 6.8 Compatibilidad anterior

No se encontraron perfiles TOML anteriores en el árbol al implementar esta CLI.
La importación disponible admite esquema 1 con un elemento único:

```toml
schema_version = 1

[recording]
screen = "NOMBRE_DE_TU_MONITOR"
microphone = ""

[element]
media = "assets/idle.gif"
x = 32
y = 32
width = 300
visible = true
```

En `[element]` se acepta `path` en lugar de `media`. También se admite `media`
en la raíz; no mezcles el elemento antiguo con `layers`. La estructura actual
`recording`/`layers` con versión 1 también se normaliza a 2. Al guardar se escribe
el formato actual. No se garantiza importar otros formatos antiguos desconocidos.

Los scripts de elemento único y sus variables de entorno siguen siendo una vía
separada. `compositor.py record` utiliza el perfil y limpia las variables de
entorno `GSR_RUST_*` y `GSR_OVERLAY_*` del proceso hijo para que no alteren la
escena guardada.

## 7. Grabación, salida y audio

### 7.1 Pantalla y ajustes efectivos

El monitor se selecciona por su nombre guardado. No depende del monitor donde
abriste la terminal ni de cuál tenga el foco. La captura de monitor de este flujo
usa GSR/KMS; no se solicita captura mediante portal COSMIC.

Estos ajustes están expuestos:

- Monitor de captura.
- Ruta y nombre del archivo MKV.
- FPS, de 1 a 120.
- Audio del sistema activado/desactivado y elección de micrófono.
- Capas y avatar según el perfil.

Estos ajustes están fijados en la implementación actual:

| Ajuste | Valor enviado a GSR |
| --- | --- |
| Video | `-k h264` |
| Calidad | `-q very_high` |
| Codificador | `-encoder gpu` |
| Respaldo por CPU | `-fallback-cpu-encoding no` |
| Modo de cuadros | `-fm cfr` |
| Contenedor admitido por el perfil | MKV |

No hay opciones de bitrate, codec de audio, frecuencia de audio grabado, resolución
independiente, HDR, captura de ventana, selección de aplicación de audio, replay,
streaming ni pausa en esta CLI. Las opciones de GSR no expuestas no se pueden
pasar como argumentos adicionales a `compositor.py`.

### 7.2 Micrófono y audio del juego

El listado cruza las entradas que GSR conoce con las fuentes de `pactl`,
excluyendo monitores de salida. Puedes elegir:

- `default_input`: se resuelve al validar/iniciar a un identificador concreto.
- Una entrada explícita: se conserva su identificador, aunque cambie de orden.
- Ninguna entrada: `microphone = ""`; no es compatible con tener un avatar.

La misma entrada resuelta se usa para grabar voz y activar el avatar. No hay una
opción para escoger micrófonos distintos para esas funciones. Si una entrada
explícita desaparece, se informa antes de grabar y debes elegir otra; no se
sustituye silenciosamente por el predeterminado.

`game_audio = true` captura la salida predeterminada del sistema: puede incluir
Minecraft, música, notificaciones y otras aplicaciones. No aísla únicamente el
juego. Con voz y sistema activos, GSR recibe una fuente combinada:

```text
default_output|device:IDENTIFICADOR_DEL_MICROFONO
```

Se graba una pista mezclada; el menú no permite pistas separadas ni regular el
volumen individual. El umbral del avatar **no es un control de volumen** y no
modifica el audio guardado.

El detector abre una segunda captura de la misma entrada mediante `parec`.
GSR conserva sus propios relojes de audio/video. La frecuencia mono de 16 kHz del
detector no se aplica al audio del archivo; la CLI no fija sus parámetros mediante
`-ac`, `-ab` o una frecuencia de muestreo.

No cambies dispositivos durante una captura. No hay reconexión automática. Si se
cierra la tubería del detector, se desactiva el overlay, se escribe un diagnóstico
y el CLI marca el resultado incompleto al finalizar. No hay watchdog si el
servidor deja de entregar audio sin cerrar la tubería.

### 7.3 Iniciar y detener

| Forma de iniciar | Forma de terminar |
| --- | --- |
| Menú `8`, luego `s` | Ctrl+C en la terminal; después vuelve al menú |
| `record perfil.toml --seconds 30` | Parada automática o Ctrl+C antes |
| `record perfil.toml` | Ctrl+C; después vuelve a la shell |

Sin `--seconds`, la CLI no impone un plazo de 7200 segundos. Ese límite se aplica
al argumento de duración fija. El espacio en disco, los dispositivos y el sistema
siguen limitando la sesión.

No hay cuenta atrás ni inicio programado. Conserva la terminal accesible para
poder detener. Espera al cierre antes de abrir o mover el archivo.

### 7.4 Archivos y comprobación final

Para una salida `grabacion.mkv` se crean:

| Archivo | Contenido |
| --- | --- |
| `grabacion.mkv` | Video y audio configurado |
| `grabacion.mkv.gsr.log` | Salida y diagnósticos del proceso GSR/plugin |
| `grabacion.mkv.report.json` | Comando, hashes del build, escena efectiva, código de salida, tiempo, metadatos de ffprobe y estado `completed` |

El informe se escribe al finalizar el proceso y sus comprobaciones, no es un
registro de progreso en vivo ni una medición de CPU/RAM de la escena.

El CLI comprueba salida no vacía, retorno del proceso, carga/cierre del plugin y
streams de video/audio esperado. Si falla, conserva el archivo parcial e indica
qué log/informe revisar. Una interrupción muy temprana o un fallo al lanzar GSR
puede dejar un archivo vacío o no llegar a generar el informe.

Puedes inspeccionar un archivo manualmente:

```bash
ffprobe -v error -show_streams -show_format -of json "recordings/grabacion.mkv"
```

Sustituye la ruta por la impresa en `Guardado:`. La presencia de un stream de audio
no demuestra que se oiga voz; duración y FPS tampoco demuestran ausencia de
congelamientos, duplicados o desincronización. Reproduce el resultado.

## 8. Diagnóstico

Los errores de configuración suelen empezar por `Corregir:`. En el editor,
corrige el valor y repite `7`. En un comando sin menú, el programa termina con
error; abre `edit`, corrige y guarda antes de volver a grabar.

### 8.1 GSR o plugin no disponibles

**Síntoma:** `Falta gpu-screen-recorder en PATH`, `build: ejecuta bash
scripts/build-rust-overlay.sh` o error de hash/ABI.

**Comprueba:**

```bash
command -v gpu-screen-recorder
gpu-screen-recorder --version
ls -l build/overlay-rust.so build/overlay-rust.build.json \
  build/rust-target/release/scene-check
git -C third_party/gpu-screen-recorder rev-parse HEAD
```

Si faltan artefactos, compila con `bash scripts/build-rust-overlay.sh`. Si falla
por caché Cargo, usa `cargo fetch --manifest-path rust/Cargo.toml --locked` con
red y repite. Si GSR y el manifiesto no coinciden, revisa qué binario devuelve
`command -v`, el commit y el build local instalado. No edites hashes para saltarte
la comprobación: alinea las compilaciones y regenera el manifiesto.

### 8.2 Pantalla ausente o sesión gráfica inaccesible

**Síntoma:** `recording.screen: '...' no disponible`, GSR no anuncia monitores o
aparecen errores de conexión al servidor Wayland.

**Comprueba en una terminal de COSMIC, como usuario normal:**

```bash
printf 'Tipo de sesión: %s\nWayland: %s\n' "$XDG_SESSION_TYPE" "$WAYLAND_DISPLAY"
ls -l /dev/dri
gpu-screen-recorder --list-capture-options
python3 scripts/compositor.py devices
```

Si el monitor cambió de nombre o fue desconectado, entra en `1` y vuelve a
elegir. Si el perfil antiguo tiene `screen` y hay varios monitores, selecciona
uno concreto. Si falla la conexión gráfica o no hay acceso a DRM, un cambio de
X/Y o `--assets-only` no resuelve la captura. Revisa sesión, driver y helper KMS;
no ejecutes el compositor con `sudo` para intentar suplirlo.

### 8.3 Micrófono ausente o desconectado

**Síntoma:** `recording.microphone: '...' no está disponible como entrada` o no
se pudo capturar audio de esa fuente.

**Comprueba:**

```bash
gpu-screen-recorder --list-audio-devices
pactl --format=json list sources
pactl get-default-source
python3 scripts/compositor.py devices
```

Conecta el dispositivo y vuelve a consultar. En `edit`, opción `2`, selecciona
la entrada actual o el predeterminado y guarda. El nombre comercial mostrado no
es el identificador que se escribe manualmente en TOML. Si el predeterminado es
un monitor de salida, no se acepta como entrada de micrófono.

Si falta `pactl` o `parec`, revisa `pulseaudio-utils`. Si falla `pactl info`,
comprueba tu servicio de audio y la sesión de usuario antes de cambiar el perfil.

### 8.4 GIF inexistente, inválido o demasiado grande

**Síntoma:** `layers[N].path`, `idle` o `talking` indica archivo no regular, o el
verificador muestra un error de cabecera, GIF truncado, disposal o presupuesto.

**Comprueba:**

```bash
python3 scripts/compositor.py check perfil-minecraft.toml --assets-only
ls -l examples/assets/idle.gif examples/assets/talking.gif
```

Comprueba la base de las rutas: se leen desde la carpeta del TOML. Para una capa
gráfica puedes cambiar el archivo con `4`, `e`. Para el avatar cambia sus dos
rutas en ese formulario. No basta cambiar la extensión para convertir un archivo.
Ocultar no evita validarlo: reemplázalo por un recurso válido o quita la capa.

Si supera el presupuesto, reduce dimensiones o cuadros **en el archivo original**
con una herramienta externa o usa menos capas. Reducir solo `width`/`height` en
el perfil cambia el dibujo, no el coste de la precarga de la imagen fuente.

### 8.5 Avatar que no cambia, siempre habla o vuelve demasiado rápido

**Síntoma:** siempre se ve el mismo estado, o reacciona al teclado/ruido.

Comprueba en este orden:

1. La capa debe tener `kind = "avatar"`, no ser un gráfico apuntando solo a idle.
2. Debe ser visible y estar dentro del cuadro, sin otra capa opaca encima.
3. Comprueba el micrófono concreto mostrado por `check` y su silencio/ganancia en
   la configuración de audio del sistema.
4. Usa GIF de reposo y habla visualmente distintos; no apuntes ambos al mismo
   archivo si quieres distinguir el cambio.
5. Edita el umbral y la espera; guarda y prueba otra grabación corta.
6. Revisa el `.gsr.log` si aparece un diagnóstico `gsr-rust:` o de `parec`.

Baja el umbral si la voz no activa; súbelo si activa el ruido. Aumenta
`release_ms` si vuelve demasiado pronto a reposo. No hay un medidor ni una prueba
interactiva de nivel dentro del menú. Un GIF con cuadros muy largos puede parecer
quieto aunque el reloj y el estado funcionen.

### 8.6 Capa fuera del cuadro, deformada o con tamaño inesperado

**Síntoma:** no aparece, queda cortada, demasiado pequeña o no llena la caja.

Ejecuta `check` para ver las dimensiones efectivas. Compara X/Y con la resolución
del monitor elegido. Usa `4`, `e` para corregirlas; `4`, `o` si está oculta y `r`
si está detrás de otra capa. Para una prueba fácil, colócala en X/Y `32`/`32` y
ancho `300` con alto automático (`-`).

Con proporción activada no siempre se llenan ambas dimensiones. Si una dimensión
heredada te limita, bórrala con `-`. Para el avatar, reposo fija la caja común.
No hay anclaje automático a la esquina y no se valida que el elemento sea visible
dentro del lienzo.

### 8.7 Falta de audio o audio equivocado

**Síntoma:** falta la voz, el juego, ambos o se grabó otra aplicación.

Revisa el resumen y estos campos:

- `game_audio = true` para audio de la salida predeterminada.
- `microphone` no vacío para voz; el avatar no activa por sí mismo otra fuente.
- Predeterminado del sistema correcto, dispositivo sin silenciar y volumen útil.

Comprueba fuentes y el archivo:

```bash
pactl info
gpu-screen-recorder --list-audio-devices
ffprobe -v error -show_streams -of json "recordings/grabacion.mkv"
```

Si hay una pista pero se oye silencio, el éxito de ffprobe no descarta un problema
de selección, muteo o ganancia. Cambia la entrada desde `2` y revisa la salida
predeterminada del sistema. El juego no se captura de forma aislada: otras
aplicaciones también pueden sonar. No hay mezclador, ganancia ni pistas separadas
en esta CLI.

### 8.8 El archivo no aparece, está vacío o la grabación se marca incompleta

**Síntoma:** no aparece `Guardado:`, el comando termina con `Corregir:`, o el video
no está en la carpeta esperada.

Lee la línea `Salida:` y recuerda que el destino relativo depende del TOML. Un
perfil en `perfiles/` con salida `recordings/...` escribe bajo
`perfiles/recordings/`, salvo que la ruta se haya conservado mediante «guardar como».
El nombre del `check` anterior puede ser distinto por `{timestamp}`.

Comprueba la carpeta real, permisos, espacio y archivos auxiliares:

```bash
ls -lt recordings/
df -h .
cat "recordings/grabacion.mkv.gsr.log"
cat "recordings/grabacion.mkv.report.json"
```

Adapta las rutas. Si falló antes de lanzar GSR, puede no haber video ni log.
Si falló el lanzamiento, puede quedar un archivo de cero bytes. Si GSR llegó a
capturar, se conserva el archivo parcial y, cuando se completa el manejo del
resultado, se escribe el informe. Un nombre fijo ya usado se rechaza; elige otro
o usa `{timestamp}`. Si también existen log/informe con ese nombre se rechaza.

Para problemas de codificador:

```bash
gpu-screen-recorder --info
```

Se exige H.264 GPU. No hay respaldo automático a CPU. Si el sistema no anuncia
esa capacidad, hay que resolver el driver/compatibilidad o revisar el entorno;
el perfil no ofrece otra elección de codec. Una pantalla negra con gráficos
visibles tampoco demuestra captura correcta: conserva el log y comprueba GSR en
la sesión objetivo antes de atribuirlo al archivo GIF.

## 9. Límites y alcance de las pruebas

### 9.1 Límites actuales

| Recurso o función | Límite |
| --- | --- |
| Capas por perfil | 16, incluido el avatar |
| Avatares | Uno; dos fuentes GIF en una capa |
| TOML y manifiesto interno | Hasta 128 KiB cada uno |
| Archivo gráfico comprimido | Hasta 8 MiB por fuente |
| Dimensiones de fuente | De 1 a 4096 por eje, además de los presupuestos de bytes |
| Imagen RGBA / caché de un GIF | Hasta 16 MiB |
| Cuadros de un GIF | Hasta 1024 |
| Temporales gestionados del GIF | Hasta 8 MiB por decoder |
| Suma RGBA precargada de la escena | Hasta 64 MiB; cuenta ocultos y ambos GIF del avatar |
| JPEG | Hasta 64 scans; sin promesa de gestión ICC ni orientación EXIF automática |
| Composición | SDR de 8 bits; HDR rechazado |

El presupuesto RGBA no es un límite de RAM total. Hay texturas, buffers de GSR,
memoria del driver, allocator y temporales. Al rechazar una capa por exceder el
total, esa capa adicional puede haber sido decodificada temporalmente. Los
recursos repetidos se cargan por separado. No se garantiza una cifra de 150 MB
ni un consumo inferior a OBS para una escena que no se haya comparado.

Se carga y decodifica antes de dibujar. `draw` no lee archivos ni vuelve a
decodificar; el GIF solo actualiza su textura cuando cambia el cuadro. La
configuración queda fija durante la captura. Este menú clásico no es una TUI de
pantalla completa; para eso está la [interfaz Trama](tui.md). No hay GUI,
previsualización, edición en vivo, texto, streaming, temblor o gestión de múltiples
escenas. El JSON temporal de la escena es interno, no otro archivo que el usuario
tenga que administrar.

### 9.2 Qué se comprobó y qué queda pendiente

| Evidencia | Alcance |
| --- | --- |
| Ayuda real de la CLI | Sintaxis de los cuatro subcomandos y sus opciones |
| Pruebas de perfiles/CLI | Guardar/cargar, rutas relativas y Unicode, menú de capas, orden/visibilidad, importación v1, validación de recursos y presupuesto |
| Errores simulados de dispositivos | Micrófono explícito ausente sin fallback y parsing de respuestas de GSR/PulseAudio; no equivalen a desconectar un micrófono físico |
| Recursos inválidos | GIF inexistente y JPEG malformado, también estando oculto |
| Hosts EGL/OpenGL con llvmpipe | Píxeles, transparencia, orden, recorte, animación, estado GL, cierre y barreras de panic; no es Iris Xe |
| Avatar con PCM sintético | Umbral, espera y cambio de GIF, incluyendo fuentes con dimensiones distintas |
| Runner con proceso simulado | Guardar/cargar un TOML, generar un MKV real con color/audio sintéticos por FFmpeg, detenerlo por señal e inspeccionarlo; no es captura real por GSR |

Las pruebas automatizadas usan dispositivos simulados y GL por software; no
certifican acceso a KMS ni audio físico. Valida en la sesión COSMIC del equipo
objetivo: selección de monitor/entrada, video, audio del sistema y micrófono,
respuesta del avatar, estabilidad y recursos durante una sesión prolongada.
Una prueba de 30 s es el primer paso, no una certificación de rendimiento.

Para ejecutar las comprobaciones del proyecto desde su raíz:

```bash
bash scripts/check-rust-overlay.sh
CARGO_TARGET_DIR=build/rust-target cargo clippy --manifest-path rust/Cargo.toml \
  --offline --locked --all-targets --all-features -- -D warnings
```

La suite completa compila artefactos de prueba separados y usa Pillow, FFmpeg y
GL por software. `clippy` requiere ese componente de la toolchain. No graba tu
pantalla para sustituir la prueba manual en COSMIC.

La suite prepara la referencia C desde sus fuentes y genera su manifiesto; no
necesita recuperar un binario histórico. Las pruebas nuevas usan muestras neutras
y no abren perfiles locales del desarrollador. La aplicación utiliza el plugin
Rust; la referencia C es una herramienta de desarrollo.

## 10. Archivos de referencia

En caso de discrepancia, la implementación y su ayuda son la referencia para la
interfaz actual. Los resultados de una máquina o compilación no son promesas de comportamiento
universal.

- [CLI principal y menú](../scripts/compositor.py).
- [Esquema, defaults, rutas y guardado TOML](../scripts/compositor_profile.py).
- [Enumeración de dispositivos y comprobación del micrófono](../scripts/compositor_devices.py).
- [Perfil de ejemplo](../examples/perfil.toml).
- [Descripción técnica de CLI/escena](cli-escena.md).
- [Script de preparación de GSR](../scripts/prepare-gsr.sh).
- [Script de compilación del plugin](../scripts/build-rust-overlay.sh).
- [Suite del plugin Rust](../scripts/check-rust-overlay.sh).
- [Pruebas de perfiles y CLI](../tests/test_compositor.py).
- [Pruebas de la CLI anterior](../tests/test_element_cli.py).
- [Pruebas GL y avatar](../tests/rust_gl_host.py).
- [Oráculo de GIF](../tests/check_rust_gif.py).
- [Carga y límites de escenas](../rust/src/scene.rs).
- [Detector de amplitud](../rust/src/microphone.rs).
- [Contrato FFI/OpenGL](../rust/SAFETY.md).
- [GSR: documentación del código fijado](../third_party/gpu-screen-recorder/README.md).
- [GSR: opciones de construcción](../third_party/gpu-screen-recorder/meson_options.txt).
- [GSR: manual de argumentos](../third_party/gpu-screen-recorder/gpu-screen-recorder.1).
- [Estado y alcance de validación](estado.md).
