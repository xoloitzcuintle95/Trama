# Arquitectura del compositor

## Componentes

- **Interfaz:** Python, TUI curses y CLI de texto. Configuración previa a grabar.
- **Perfil:** un esquema TOML compartido por TUI, menú y comando directo.
- **Composición:** plugin Rust `cdylib`, RGBA sobre el framebuffer de GSR.
- **Motor:** GPU Screen Recorder nativo para captura, audio, codificación y archivo.

```text
TOML → validación Python → manifiesto temporal → precarga Rust
                                               ↓
Monitor → GSR/KMS → composición de capas GL/GLES → codificación GPU → MKV
Micrófono → audio GSR ────────────────────────────────────────────────┘
          → parec → nivel RMS atómico → estado reposo/habla
```

La API usada es la cabecera de plugins 0.1 del commit GSR
`f97d1e392816503282d20a0804c3ce3fd2943767`, versión 6.1.7. No se modifica el núcleo
de GSR. El build compara layouts C/Rust y registra hashes del motor/plugin.
No basta con encontrar otro ejecutable que diga 6.1.7.

La TUI es el único hilo que llama curses. Las consultas y la grabación trabajan
fuera de él. El grabador compartido conserva parada SIGINT y espera de cierre;
la TUI lo controla con un evento, sin otra implementación de captura.

## Capas y avatar

Tipos concretos, sin framework genérico: gráfico PNG/JPG/GIF o avatar con dos GIF.
La configuración se resuelve en init; no hay lectura de archivos, decodificación
ni parseo en draw. El escalado cambia el quad GPU, no los píxeles precargados.

Se conserva transparencia y se mezcla con alfa premultiplicado. Los GIF usan
reloj monotónico, tiempos/disposal/bucles del archivo y caché completa acotada.
Una demora nula/ausente usa 100 ms; una animación finita mantiene su último cuadro.
Al cambiar de estado del avatar se reinicia el reloj del GIF entrante.

El detector mide amplitud, no reconoce voz. `parec` produce mono float32 a 16 kHz;
un hilo calcula RMS en bloques de 20 ms y publica booleanos atómicos. La misma
entrada resuelta se pasa a GSR y al detector, pero son **dos capturas**. GSR
mantiene los relojes del audio grabado; el detector no toca sus buffers.

Ocultar conserva recursos cargados y no dibuja. No libera toda la memoria ni
permite una fuente inválida. No hay cambios de escenas ni edición en vivo.

## Límites

| Recurso | Límite |
| --- | --- |
| Capas / avatar | 16 capas, hasta un avatar |
| Perfil / manifiesto | 128 KiB cada uno |
| Archivo comprimido | 8 MiB por fuente |
| Dimensión de fuente | 1..4096 por eje, sujeto al límite RGBA |
| Imagen / caché GIF | 16 MiB por fuente |
| GIF | Hasta 1024 cuadros, temporales gestionados hasta 8 MiB |
| Escena precargada | 64 MiB RGBA, incluidos ocultos y ambos GIF del avatar |
| Composición | SDR 8 bits |

Estos límites no son un techo de RSS: GSR, texturas, allocator, decoders y driver
consumen aparte. Un rechazo puede ocurrir tras decodificar una capa adicional.
No se deduplican fuentes repetidas. PNG/JPG liberan RGBA CPU tras el upload.

La fuente JPEG se convierte a RGB/Luma y después a RGBA opaco. No se promete
color ICC ni orientación EXIF automática. El renderizador conserva el contexto,
hilo y estado GL del host; un fallo desactiva la instancia y queda en el log.
No es un sandbox: plugin y GSR comparten proceso.

## Código y contratos

- [CLI y grabador compartido](../scripts/compositor.py).
- [TUI](../scripts/trama_tui.py) y [modelo](../scripts/trama_model.py).
- [Perfil](../scripts/compositor_profile.py) y [dispositivos](../scripts/compositor_devices.py).
- [Escena Rust](../rust/src/scene.rs), [media](../rust/src/media.rs) y [render](../rust/src/render.rs).
- [Contrato unsafe, ABI y OpenGL](../rust/SAFETY.md).
- [Desarrollo y pruebas](desarrollo.md).
