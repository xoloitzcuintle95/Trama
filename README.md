# Trama — compositor sobre GPU Screen Recorder

Compositor ligero para grabar videojuegos y sesiones de desarrollo en Linux.
La TUI permite editar capas y un avatar reactivo al micrófono; GSR se encarga de
capturar, grabar audio, codificar y escribir el video.

![Flujo audiovisual de Trama](assets/brand/hero.png)

La aplicación se llama **Trama** y se abre con `./trama` desde fuentes o `trama`
tras instalar el paquete preliminar. [Icono y mascota](assets/brand/README.md)
forman la identidad visual; los perfiles de ejemplo conservan recursos neutros.

## Empezar

Requiere GSR nativo compatible, el plugin compilado y una terminal de la sesión
gráfica. Plataforma objetivo: **Wayland**, con COSMIC en Pop!_OS 24.04 como caso
principal de validación. No se amplía soporte para modalidades exclusivas de X11.

```bash
./trama
```

La primera vez puedes elegir pantalla y micrófono, cargar tus GIF de reposo/habla,
colocar el avatar en una esquina y guardar una prueba de 30 segundos. Después se
recupera el último perfil. Desde el inicio: `e` edita un campo, `c` cambia esquina,
`d` cambia carpeta, `n` nombre del video, `s` guarda, `r` graba y `t` prueba 30 s.
`x` o Ctrl+C detiene; `o` muestra la ruta del MKV.

La interfaz organiza Overview, Layers, Capture, Audio y Output con foco por Tab
y atajos contextuales. Durante la captura
queda en una vista mínima estática; vuelve a los paneles al cerrar el archivo.

Español e inglés: detección automática del sistema (otros idiomas usan inglés).
Pulsa `L` para elegir y guardar el idioma, o usa `./trama --lang en` solo para
esa ejecución. Los perfiles de grabación no cambian.

También se puede usar un perfil explícito o grabar sin TUI:

```bash
./trama /ruta/a/mi-perfil.toml
python3 scripts/compositor.py record /ruta/a/mi-perfil.toml --seconds 30
```

Los perfiles y gráficos propios pueden vivir fuera de este directorio.
[El perfil de ejemplo](examples/perfil.toml) usa recursos neutros de pocos KiB;
selecciona tu pantalla antes de grabar.

## Funciones actuales

- Capas PNG/JPG/GIF con orden, visibilidad, posición y tamaño proporcional.
- Un avatar con GIF de reposo/habla, umbral de nivel y espera configurables.
- TUI con selector de archivos, cuatro esquinas y edición individual de campos.
- Perfiles TOML con rutas relativas, guardado/carga y comando directo.
- Grabación H.264 por GPU a MKV, audio del sistema y micrófono mediante GSR.

No hay previsualización en vivo, edición durante la captura, texto ni streaming.
No se garantiza un consumo inferior a OBS sin una comparación equivalente.

## Documentación

- [Paquete preliminar: contenido, instalación y límites](docs/paquete-preliminar.md).
- [TUI: recorrido, teclas y uso diario](docs/tui.md).
- [Manual completo de instalación, CLI y perfiles](docs/guia-cli.md).
- [Elemento único por CLI](docs/configuracion-elemento.md).
- [Arquitectura y límites](docs/cli-escena.md).
- [Construcción y pruebas](docs/desarrollo.md).
- [Medición reproducible](docs/mediciones.md).
- [Estado y validación](docs/estado.md).
- [Etapas futuras](docs/plan-rust.md).

## Desarrollo

GSR se mantiene separado en `third_party/gpu-screen-recorder`. La integración
actual se comprueba contra GSR 6.1.7, commit
`f97d1e392816503282d20a0804c3ce3fd2943767`. El motor instalado debe coincidir con
el build registrado; no se promete compatibilidad universal entre versiones.

```bash
bash scripts/build-rust-overlay.sh
bash scripts/check-rust-overlay.sh
python3 tests/test_trama.py
python3 tests/test_trama_pty.py
```

El paquete preliminar local se construye con `python3 scripts/build-deb.py`.
Incluye motor GSR y helper privados, sin GUI; usa bibliotecas del sistema y se
acompaña de un archivo separado de fuentes. No se instala automáticamente ni es
una publicación estable. Véase la [guía del paquete](docs/paquete-preliminar.md).

El usuario confirmó que la TUI funciona y se ve bien en su laptop, y que ya
realizó una grabación de 10 minutos. También confirmó una grabación con el
paquete instalado. Las pruebas automatizadas de ese runtime y del primer arranque
usan perfiles temporales y dispositivos simulados. No hay una prueba de 60 minutos ni una
comparación nueva de recursos con OBS. Una sesión larga es un criterio de
validación pendiente, no un requisito para que el programa comience a funcionar.

## Licencia

El código propio, el icono, la mascota y el hero de Trama usan **GPL-3.0-only**,
igual que GSR; véase [LICENSE](LICENSE). Las dependencias conservan sus licencias
originales. El arte fue generado con ChatGPT y entregado para Trama; su procedencia
y alcance se describen en [identidad visual](assets/brand/README.md).
Este paquete preliminar sigue siendo de evaluación local.
