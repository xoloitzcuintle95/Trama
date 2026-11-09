# Investigación: presentación de la TUI y capacidades de GSR

La primera mejora visual sobre curses y la vista estática de grabación ya están
implementadas; véase la [guía actual de la TUI](tui.md). Las capacidades nuevas
de GSR siguen siendo propuestas, no funciones habilitadas. Wayland/COSMIC es el
objetivo de soporte; las restricciones X11 se documentan para no prometer modos
que no funcionan en esa plataforma.

Alcance: investigación y propuesta, sin migración de biblioteca, instalación de
paquetes ni cambios a captura. Referencia local: GSR 6.1.7, commit
`f97d1e392816503282d20a0804c3ce3fd2943767`, plugin Rust SDR actual.

## Diagnóstico visual original (antes del rediseño)

La pantalla anterior usaba posiciones fijas y texto casi monocromo. Su pie contiene
unas veinte acciones mezcladas en varias líneas, aunque muchas no tengan relación
con el campo seleccionado. Agregar más opciones ahí empeoraría la navegación.

Una presentación más clara no depende solo de colores:

- Separar Captura, Capas, Audio, Salida y Avanzado.
- Mantener estado y perfil en una cabecera breve.
- Dar a Grabar y Prueba 30 s una zona visible de acciones principales.
- Usar paneles con títulos, márgenes y valores alineados.
- Mostrar propiedades de la capa seleccionada junto al listado.
- Mantener un pie de cuatro o cinco atajos **contextuales**; mover el resto a
  Ayuda o a un menú de acciones.
- Tab/Shift+Tab para foco, flechas para listas y Enter para editar; no interceptar
  letras de un campo de texto como órdenes de grabación.
- Usar un acento de color, estados con texto y color, buen contraste y fallback
  monocromo. Los símbolos no deben ser el único indicador de un error.
- Reorganizar paneles en una columna cuando el terminal sea estrecho, con scroll.

Boceto conceptual, no una pantalla implementada:

```text
 COMPOSITOR                              Perfil: sesión · Listo
 Captura     Capas     Audio     Salida     Avanzado

 ┌ Captura ───────────────────┐ ┌ Video ──────────────────────┐
 │ Monitor seleccionado       │ │ H.264 · GPU · 30 FPS        │
 │ Resolución del lienzo      │ │ MKV · calidad alta          │
 └───────────────────────────┘ └────────────────────────────┘
 ┌ Capas ─────────────────────┐ ┌ Propiedades ────────────────┐
 │ ● Avatar                   │ │ Esquina inferior derecha   │
 │ ● Imagen                   │ │ Caja 300 px · margen 20    │
 └───────────────────────────┘ └────────────────────────────┘
 Carpeta: …                    Nombre: sesión-{timestamp}.mkv

 [ Grabar ]      [ Prueba 30 s ]      [ Guardar ]
 Tab Navegar     Enter Editar     ? Ayuda     q Salir
```

## Bibliotecas investigadas

| Opción | Ventaja | Coste o límite |
| --- | --- | --- |
| curses actual | Sin nuevas dependencias; se conserva el código y la integración de terminal probada | Layout, foco, widgets y estilos se mantienen manualmente |
| prompt_toolkit | Layouts, entradas, estilos y keybindings para aplicaciones completas | Nueva dependencia y adaptación de eventos; el diseño visual sigue siendo nuestro |
| Textual | CSS, paneles, tablas, árbol de archivos, foco y footer contextual; workers y pruebas headless | Más dependencias y migración de la capa visual; coste de memoria/CPU pendiente de medir |

En el entorno inspeccionado: curses disponible, Rich 13.7.1 instalado;
Textual y prompt_toolkit no instalados. No se instaló ninguna biblioteca. Una
versión global ya instalada no constituye una decisión de dependencia del proyecto.

Recomendación inmediata: **rediseñar curses primero** para resolver jerarquía,
foco y pie de acciones sin cambiar el grabador. Los problemas concretos de hoy
no requieren una migración. Si la expansión exige mantener demasiados widgets
propios, comparar un prototipo de Textual antes de comprometer el cambio.

Textual es una alternativa real para crecer, no una promesa de menor consumo.
El prototipo tendría que conservar TOML/backend/plugin y comparar arranque,
respuesta al teclado, memoria de la TUI, tamaño de dependencias y recursos del
conjunto al grabar. Una interfaz y un motor distintos no deben cambiar a la vez
si queremos atribuir una regresión.

Fuentes primarias:

- [curses: colores, ventanas y terminal](https://docs.python.org/3/library/curses.html).
- [prompt_toolkit: aplicaciones de pantalla completa](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/full_screen_apps.html).
- [Textual: layouts](https://textual.textualize.io/guide/layout/),
  [widgets](https://textual.textualize.io/widget_gallery/) y
  [footer ligado al foco](https://textual.textualize.io/widgets/footer/).
- [Textual: workers](https://textual.textualize.io/guide/workers/) y
  [pruebas de teclado, clic y tamaño de pantalla](https://textual.textualize.io/guide/testing/).

## Qué podemos exponer del motor fijado

La ayuda general no demuestra que una característica esté compilada o disponible
en una sesión. Se contrastaron manual y código local con las opciones de build
del proyecto. Las filas siguientes son viabilidad de integración, **no pruebas
nuevas de grabación con esos modos**.

| Capacidad | Evidencia y condición | Trabajo del compositor |
| --- | --- | --- |
| Monitor | Ya integrado | Conservar el flujo probado |
| Región | `-w region`/`-region`, backend de monitor; transforma coordenadas y escala de pantalla | Selección/configuración, validación y lienzo de salida correcto |
| Codec, calidad, bitrate y contenedor | El motor tiene opciones; `--info` anuncia codecs/containers del equipo | Quitar constantes H.264/very_high/MKV, filtrar combinaciones y conservar defaults |
| Resolución y cursor | `-s` limita resolución preservando proporción; `-cursor` controla el puntero | Recalcular lienzo y colocación; no asumir que `-s` fija exactamente W×H en todo modo |
| Pausa | SIGUSR2 o IPC para grabación normal; no aplicable como pausa de replay/streaming | Estado confirmado del motor y política para el reloj del GIF |
| Replay | `-r`, RAM/disco, guardar con señal o IPC | Duración/bitrate/presupuesto, múltiples archivos guardados y ruta devuelta por GSR |
| Streaming | GSR admite destino de red y muxer apropiado | Configuración específica, estado de conexión y protección de claves |
| Grabar durante replay/streaming | `-ro`, control SIGRTMIN o IPC y destinos del encoder compartidos | Integrar controles y recoger archivos; probar plugin/audio y consumo |
| Ventana y foco | Solo sesión X11 pura; código rechaza Wayland/Xwayland | Mostrar solo donde funciona; no prometerlo en COSMIC |
| Portal | Desactivado por `-Dportal=false` en nuestro build | Recompilar motor y validar el portal de COSMIC; no es una casilla de TUI suficiente |
| Audio por aplicación | Desactivado por `-Dapp_audio=false`; consulta es condicional en el código | Recompilar con dependencias correspondientes y probar PipeWire |
| Cámara V4L2 | Lista modos y acepta cámara como fuente, incluso combinada con otras | Permisos, formato, FPS, ocupación del dispositivo y layout de fuentes; distinto de una capa GIF |
| HDR/10 bits | GSR tiene modos; plugin actual rechaza color depth distinto de SDR 8 bits | Cambios/pruebas de color, formatos y mezcla del plugin; mantener desactivado por ahora |
| Solo audio | GSR lo admite sin fuente de video | Modo independiente, sin compositor/overlays de video; adaptar comprobación final |

Las capacidades de codec dependen también de GPU y driver. No se asume que
AV1/HEVC se puedan codificar porque exista la opción o el decodificador.
La combinación de monitores de distintas GPU tiene limitaciones explícitas en
el código del motor y no se declara soportada por nuestra integración.

### Hallazgos que condicionan la implementación

1. **Pausa y GIF:** nuestro reloj es monotónico de tiempo real y no recibe el estado
   de pausa de GSR. Al retomar podría avanzar de fase. Hay que elegir y probar
   «continúa en tiempo real» o «congelar animaciones»; no prometer lo segundo con
   solo enviar una señal al motor.
2. **Replay:** SIGINT termina sin guardar automáticamente el búfer. El grabador
   actual espera un solo MKV al acabar; esa política no sirve para replay. Deben
   aparecer acciones separadas «Guardar últimos N segundos» y «Detener búfer».
3. **Streaming con archivo local:** el soporte existe en este commit, tanto en
   documentación como en `recorder.c`. No hace falta inventar dos instancias por
   defecto. Compartir captura/encoder es una capacidad del motor; falta validarlo
   con nuestra integración y medirlo en el equipo objetivo.
4. **Protocolos:** FFmpeg local es 6.1.1. Su listado anuncia salida RTMP, RTMPS,
   SRT, HTTP y HTTPS; no anuncia muxer WHIP. El manual exige FFmpeg 8 o posterior
   para WHIP. Estos listados no prueban una conexión ni una cuenta de servicio.
5. **Claves:** el informe actual registra comando/destino completos para archivos.
   Antes de destinos de red debe ocultar claves/credenciales y evitar guardarlas
   en perfiles públicos. No usar el informe actual sin revisar para streaming.
6. **Coordenadas:** región o escalado modifican el video de salida; las esquinas
   deben usar ese lienzo, no siempre las dimensiones nativas del monitor.

La documentación oficial también describe las rutas de
[replay, streaming y grabación simultánea](https://git.dec05eba.com/gpu-screen-recorder/about/).
No se ha hecho una emisión ni una prueba nueva de dispositivos en esta investigación.

## Organización de opciones y entregas propuestas

Separar dos elecciones en la interfaz:

- **Fuente:** monitor, región, ventana donde se soporte, portal donde esté
  habilitado, cámara.
- **Modo de salida:** grabación normal, replay, transmisión; grabación local
  adicional solo en los modos del motor que lo permitan.

Capas, audio y calidad se configuran en secciones propias. Opciones no disponibles
se ocultan o muestran desactivadas con la razón (compilación, sesión, GPU o plugin).
La TUI obtiene capacidades del motor/build y del entorno; no mantiene un listado
optimista basado solo en la ayuda de GSR.

El TOML debe evolucionar con migración explícita y defaults compatibles: un perfil
actual con `screen` se conserva como captura de monitor y grabación normal.
No añadir un campo libre que envíe argumentos de shell sin validar al motor.

Orden recomendado:

1. Rediseño visual y navegación contextual, conservando funciones actuales.
2. Opciones de video/salida y captura de región, con pruebas del lienzo/overlays.
3. Pausa y replay, con control del motor y comprobación de resultados por modo.
4. Streaming y grabación simultánea, con credenciales seguras y prueba real.
5. Backend opcionales como cámara, X11/portal/audio por app según necesidad.
6. HDR únicamente tras resolver el recorrido de color del plugin.

No empaquetar ni cambiar de motor durante estas entregas. No desactivar las
comprobaciones de ABI/hash para facilitar pruebas con otro binario; una
recompilación del motor debe mantener el manifiesto y el plugin alineados.

## Archivos contrastados

- [TUI actual](../scripts/trama_tui.py).
- [Comando y validación actuales](../scripts/compositor.py).
- [Opciones del build de GSR](../scripts/prepare-gsr.sh).
- [Manual GSR del checkout fijado](../third_party/gpu-screen-recorder/gpu-screen-recorder.1).
- [Opciones Meson del motor](../third_party/gpu-screen-recorder/meson_options.txt).
- [Enumeración del motor](../third_party/gpu-screen-recorder/src/cli/commands.c).
- [Captura y restricciones de sesión](../third_party/gpu-screen-recorder/src/recorder/capture_setup.c).
- [Selección y regiones](../third_party/gpu-screen-recorder/src/recorder/capture_source.c).
- [Pausa, streaming y destinos](../third_party/gpu-screen-recorder/src/recorder/recorder.c).
- [Plugin y reloj](../rust/src/lib.rs).
