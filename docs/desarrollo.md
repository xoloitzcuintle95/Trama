# Construcción y pruebas

La instalación nativa de GSR y los requisitos de Pop!_OS se describen en el
[manual](guia-cli.md#2-instalación-y-requisitos). El [paquete preliminar](paquete-preliminar.md) se construye localmente; aún requiere
validación instalado antes de publicarlo.

## Estructura

| Directorio | Uso |
| --- | --- |
| `rust/` | Plugin, decodificación, animación, ABI y render |
| `scripts/` | CLI/TUI, build, pruebas y mediciones |
| `tests/` | Pruebas y adaptadores simulados |
| `examples/` | Perfil y gráficos geométricos neutros |
| `assets/brand/` | Icono, mascota y hero entregados para Trama |
| `packaging/` | Entrada de aplicaciones, avisos y reconstrucción de fuentes |
| `src/` | Referencia C de desarrollo para contrastar comportamiento |
| `third_party/gpu-screen-recorder/` | Checkout oficial de GSR separado y fijado |
| `build/` | Artefactos generados; no es código fuente |

La referencia C es una herramienta de prueba, no el plugin que usa la TUI.
Conservarla cuesta unas decenas de KiB de fuente y permite pruebas independientes.
No se necesita una GUI de GSR.

## Compilar

El build exige el commit GSR esperado y su binario local. Las dependencias Cargo
quedan fijadas en el lockfile. La primera vez puede requerir acceso a red:

```bash
cargo fetch --manifest-path rust/Cargo.toml --locked
bash scripts/build-rust-overlay.sh
```

El script genera plugin, verificadores y manifiesto en `build/`. Remapea rutas
de fuente del build Rust para no incrustar el directorio personal de compilación.
El GSR instalado debe coincidir con el binario local registrado. No se instala
ni actualiza el motor automáticamente.

## Verificar desde fuentes

```bash
bash scripts/check-rust-overlay.sh
python3 tests/test_trama.py
python3 tests/test_trama_pty.py
python3 scripts/check-source.py
```

La primera orden prepara la referencia C y sus oráculos, compila Rust, compara
la ABI y ejecuta unidades, oráculos GIF, GL offscreen y CLI. El artefacto con
`test-hooks` se construye aparte y no reemplaza el plugin de producción. La suite
ya no depende de un binario C antiguo de una máquina concreta: su manifiesto
registra el binario y los hashes de las fuentes de esta compilación.

Las pruebas TUI usan una pseudoterminal real y un capturador simulado. El caso de
30 segundos espera ese tiempo y genera un MKV sintético; no captura el escritorio.
Los ejemplos no leen perfiles locales del desarrollador. Los recursos grandes
para comprobar presupuestos se generan dentro del directorio temporal del test.

Pillow y FFmpeg son necesarios para la suite. Para Clippy:

```bash
CARGO_TARGET_DIR=build/rust-target cargo clippy --manifest-path rust/Cargo.toml \
  --offline --locked --all-targets --all-features -- -D warnings
```

Si quieres regenerar los ejemplos geométricos:

```bash
python3 scripts/create-example-assets.py
```

## Archivos privados y generados

Mantén perfiles, gráficos personales y videos fuera del proyecto. Se admiten
rutas absolutas y perfiles con rutas relativas a su propia carpeta. La TUI guarda
solo el puntero al último perfil en el estado XDG del usuario.

El `.gitignore` excluye builds, grabaciones, perfiles locales, cachés, logs y
archivos de entorno. Eso ayuda a no incorporarlos a Git, pero no reemplaza una
revisión antes de publicar. Los avisos y licencias de dependencias oficiales no
son datos personales del desarrollador y deben conservarse.

Se pueden borrar las cachés `rust/target/`, los targets de compilación y registros
cuando no se usan. Para ejecutar sin recompilar, hacen falta al menos
`build/overlay-rust.so`, `build/overlay-rust.build.json` y los verificadores
`scene-check`/`element-check` en el target release. La suite vuelve a generar los
artefactos de prueba. No se borra el build local de GSR que necesita el manifiesto.

La copia local puede conservar solo los ejecutables de GSR y haber descartado
sus metadatos de Meson/Ninja. En ese caso usa `bash scripts/prepare-gsr.sh` para
configurar y compilar el motor de nuevo, antes de intentar `meson compile`.

## Paquete de evaluación local

```bash
python3 scripts/build-deb.py
```

Crea `.deb`, fuentes separadas y hashes en `build/packages/`. No hace instalación
ni copia archivos a `/usr`. La lista de módulos/artefactos es explícita: no se
empaqueta el árbol de trabajo entero. Incluye motor y helper GSR privados y una
copia de los avisos de Cargo. Las dependencias ELF se obtienen con
`dpkg-shlibdeps`; drivers y herramientas del sistema no se incluyen en el archivo.

El runtime conserva la disposición de rutas de los verificadores para reutilizar
el loader actual. `Devices` prioriza el motor privado solo si existe `engine/`;
desde fuentes conserva la búsqueda en PATH. El paquete verifica también helper
y validador. Los permisos KMS e instalación se explican en la
[guía específica](paquete-preliminar.md#helper-kms-y-permisos).

## Probar la versión instalada sin usar perfiles personales

Después de instalar el paquete por separado:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_installed.py
TRAMA_TEST_RUNTIME=/usr/lib/trama PYTHONDONTWRITEBYTECODE=1 python3 tests/test_trama_pty.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_package.py
```

`test_installed.py` comprueba que los módulos/binarios instalados coinciden con
el `.deb` local y ejecuta el lanzador/loader/modelo instalados con HOME, XDG y
perfiles temporales. Prueba formatos, capas y errores sin capturar dispositivos.
Necesita Pillow solo para crear un JPG de prueba, no para ejecutar Trama.

`TRAMA_TEST_RUNTIME` solo lo interpreta el adaptador de `tests/`: permite probar
la TUI instalada en pseudoterminal con pantalla/micrófono/capturador simulados.
No existe esa opción de sustitución del motor en el comando de producción.
Incluye primera ejecución sin argumentos ni estado previo, guardado y prueba de
30 segundos con MKV sintético. No acredita captura KMS, audio físico ni reacción
real del micrófono. Todos los ajustes se guardan en directorios temporales.

Estas pruebas no instalan, actualizan ni otorgan capacidades y no requieren sudo.
La coincidencia con el `.deb` local puede fallar si se instaló otra compilación;
ese resultado identifica una diferencia de versión, no autoriza a reinstalarla.
