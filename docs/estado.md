# Estado de Trama

## Implementado

- Aplicación terminal `trama`: Overview, Layers, Capture, Audio y Output;
  edición por campo, selector de archivos, cuatro esquinas y pie contextual.
- Español e inglés: automático según el sistema, inglés como alternativa,
  selector `L`, preferencia independiente y override temporal `--lang`.
- Plugin Rust 0.4.0 / ABI de plugin 4: PNG/JPG/GIF, capas y un avatar reactivo al
  micrófono. Precarga acotada, tiempos/transparencia/bucle y posiciones existentes.
- Perfiles TOML compatibles, carga/guardado, carpeta/nombre separados y grabación
  directa sin TUI. Los datos personales se conservan fuera del proyecto.
- GSR CLI 6.1.7, commit `f97d1e392816503282d20a0804c3ce3fd2943767`, motor de
  captura, audio, codificación y escritura. No se usa su GUI ni se ha recortado
  o traducido su núcleo. Wayland/COSMIC es el objetivo de soporte.
- [Identidad visual](../assets/brand/README.md): icono, mascota y hero aportados
  por el usuario. Se mantienen los originales; no sustituyen GIFs personales.
- [Paquete preliminar local](paquete-preliminar.md): `.deb` amd64 con motor/helper
  privados y manifiesto, fuentes separadas y avisos de dependencias. Construcción
  sin sudo; no instala ni concede capacidades automáticamente.

El comando anterior no se conserva. El estado del último perfil mantiene su
ubicación histórica para evitar mover datos del usuario; el idioma se guarda
por separado. No hay migración automática de perfiles, gráficos ni videos.

## Validación confirmada por el usuario

El usuario confirmó que la **TUI funciona y se ve bien en su laptop**, y que ya
realizó **una grabación de 10 minutos**. Posteriormente confirmó que el `.deb`
instalado también pudo grabar. En validaciones previas confirmó fluidez
y coincidencia del sonido con el video. Son confirmaciones de uso en su entorno
Pop!_OS/COSMIC, no resultados instrumentados ni validación en instalaciones limpias.

No se realizó una prueba de 60 minutos. Esa duración era un criterio de validación
propuesto para buscar crecimiento de memoria, desfase acumulativo o fallos poco
frecuentes; no existe un cambio programado a los 10/15/40/60 minutos ni es un
requisito técnico para usar el programa. Una sesión normal más larga puede
aportar evidencia adicional antes de declarar una versión estable.

## Validación automatizada y local

- 37 pruebas de modelo/TUI/idiomas/PTY: perfiles, esquinas, edición, idioma,
  guardado/carga, recuperación de sesión, cambios sin guardar, parada y restauración
  ECHO/ICANON. Incluyen captura simulada de 30 segundos con MKV sintético.
- 5 pruebas del paquete aprobadas: contenido permitido, propietarios/permisos, ausencia de
  scripts privilegiados, motor privado tras extracción, ayuda bilingüe,
  validador de recursos real, rechazo de helper alterado y fuentes/hashes/avisos.
- Los hosts GL anteriores usan llvmpipe; el detector se prueba con PCM sintético.
  Estas pruebas no certifican audio físico, GPU ni captura KMS en esta sesión.
- La suite CLI ampliada mantiene dos comprobaciones pendientes por artefactos de
  desarrollo ausentes: `media-dump` y la referencia C compilada/manifiesto. No se
  alteró la referencia C ni se reconstruyó para preparar el runtime mínimo.

La simulación APT local resolvió el `.deb` sin instalarlo y sin reemplazar el
GSR del sistema. El snapshot de fuentes resolvió sus 43 crates vendorizados con
Cargo offline; los archivos del runtime no contienen la ruta personal del build.
El `.deb` ronda 1.5 MiB y el archivo separado de fuentes 5.3 MiB. Esto no mide
consumo durante grabación. El resolver ELF emitió avisos sobre las diversiones
usr-merge del host; la instalación en un entorno limpio sigue pendiente.

## Pendiente antes de publicar

- Probar el acceso desde el lanzador de aplicaciones COSMIC y la instalación en
  un equipo/usuario limpio. La instalación y grabación en la laptop ya fueron
  confirmadas por el usuario; no hace falta repetirlas solo para marcar esa casilla.
- Código propio e identidad visual licenciados como GPL-3.0-only por decisión
  del propietario, igual que GSR. El arte se generó con ChatGPT. Avisos y fuentes
  se conservan; el paquete sigue siendo de evaluación local, sin publicación.
- Medición equivalente con GSR solo y OBS, y prueba más prolongada de estabilidad.
  No se declaran ventajas de recursos ni se garantiza la aspiración de 150 MB.
- Validación en instalaciones limpias: dependencias APT, drivers, Polkit/KMS y
  permisos. El paquete construido localmente no es un binario universal Linux.

No hay preview, edición en vivo, texto, timeline ni streaming. Las grabaciones,
logs e informes personales no forman parte de las fuentes ni del paquete.

Consulta [desarrollo](desarrollo.md), [TUI](tui.md),
[arquitectura](cli-escena.md), [paquete](paquete-preliminar.md) y [plan](plan-rust.md).

## Aceptación sobre el runtime instalado

Se ejecutaron **19 pruebas contra la versión instalada**: 8 de integridad,
lanzador/modelo/decoder/errores y 11 de pseudoterminal. Todas pasaron, además de
las 5 comprobaciones del paquete. Los módulos y binarios de `/usr/lib/trama` y el
lanzador coinciden byte por byte con el `.deb` preliminar local.

El caso de primera ejecución abre sin argumento en una carpeta temporal vacía,
con estado/configuración nuevos: pantalla, micrófono, recursos neutros, esquina,
guardado y retorno. También pasan guardar/cargar, PNG/JPG/GIF, ocultar/reordenar/
quitar capas, esquinas y los errores de GIF inexistente/inválido y micrófono
explícito ausente. El recorrido de 30 segundos genera un MKV sintético y verifica
parada, retorno y restauración de terminal. Se conservan los perfiles del usuario.

No se cambió el runtime instalado ni se regeneró/reinstaló el paquete para estas
pruebas. La pantalla, el audio y el capturador de las pruebas PTY son simulados;
la prueba KMS/audio física del `.deb` sigue siendo la confirmación del usuario.
Comandos y aislamiento: [desarrollo](desarrollo.md#probar-la-versión-instalada-sin-usar-perfiles-personales).
