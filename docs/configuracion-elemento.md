# Configuración de un elemento visual

Este comando configura posición, dimensiones y visibilidad **iniciales** de
un solo elemento Rust. Soporta PNG/JPG estáticos y GIF animado; APNG y texto
no están soportados. El loader identifica el contenido por firma, no por extensión.
El renderizador recibe RGBA y un rectángulo, sin conocer GIF ni PNGtuber.

Para múltiples capas y avatar usa la [TUI](tui.md) o los perfiles de la
[CLI de escenas](guia-cli.md). Este comando de elemento único no tiene watcher,
IPC ni cambios durante la grabación. Cambiar las opciones requiere iniciar otra captura.
Esto mantiene la configuración fuera del callback y evita introducir control en
vivo antes de necesitarlo.

## Uso por CLI

Ya construido como `build/overlay-rust.so`. Para recompilar/verificar, sin sudo:

```sh
bash scripts/check-rust-overlay.sh
```

Desde la raíz, primero validar sin grabar ni necesitar acceso a GPU:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --check
```

Como este GIF es cuadrado, informa 200×200 en 100/80, visible y proporcional.
`--check` valida fuente y configuración mediante el mismo código Rust que init;
no crea una captura. Aún exige el build y el GSR instalado/fingerprint conocido.

Para grabar 30 s con sonido del sistema, sin micrófono, desde la terminal gráfica:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --x 100 --y 80 --width 300 --height 200 --audio --seconds 30
```

Se detiene automáticamente. Graba el monitor completo por KMS, H.264 GPU, 30 FPS,
very_high y MKV. Conserva video/log/métricas en `build/recordings-element/<fecha-id>/`;
no sobrescribe grabaciones. Ctrl+C termina antes y conserva resultados parciales.
Sin `--audio` no graba sonido.

Para PNG estático y altura únicamente:

```sh
python3 scripts/record-element.py --media build/rust-fixtures/idle-static.png \
  --height 180 --seconds 30
```

El PNG de ejemplo se puede recrear con `python3 scripts/prepare-rust-example.py`.
Puede usarse cualquier otro PNG/GIF válido, no depende de esos nombres.

Ocultar **sin quitar la fuente**:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif --hidden --seconds 30
```

El archivo se valida, el GIF conserva su caché y la textura sigue cargada. El
callback no dibuja, no actualiza textura ni solicita daño propio mientras esté
oculto. Para una captura posterior, omite `--hidden` o usa `--visible`. No libera
RAM ni elimina el recurso; GSR sigue teniendo su ruta de plugins y captura.
No se afirma que ocultar ahorre todo el coste de GPU o memoria del conjunto.

Deformación solo cuando se pide explícitamente:

```sh
python3 scripts/record-element.py --media examples/assets/idle.gif \
  --width 300 --height 200 --stretch --seconds 30
```

## Semántica de geometría

Coordenadas en píxeles del **lienzo grabado**, desde arriba/izquierda. No son
coordenadas de una ventana o de los píxeles originales del archivo.

| Opciones | Resultado |
| --- | --- |
| Ninguna dimensión | Ancho 320, altura derivada de la proporción |
| Solo ancho | Altura derivada |
| Solo alto | Ancho derivado |
| Ancho y alto | Caja máxima: escala uniforme para caber dentro de ambas dimensiones |
| Ancho y alto con --stretch | Exactamente esas dimensiones; permite deformación |

La caja proporcional se alinea por su esquina superior izquierda en X/Y, sin
centrado automático, recorte interno ni ampliación para llenar la caja. Puede
quedar espacio a derecha/abajo. La posición por defecto sigue siendo 32/32.
Se permiten coordenadas negativas para colocar parcialmente fuera de pantalla;
OpenGL recorta contra el lienzo. Si queda completamente fuera, no aparece.

X/Y: enteros entre −16384 y 16384. Dimensiones explícitas: enteros 1..16384.
Dimensiones derivadas: mayores que cero y hasta 16384; pueden ser fraccionarias
para no deformar por redondeo. Un recurso de proporción extrema puede requerir
una caja menor para que ambas dimensiones finales respeten el límite.

## Variables de entorno y precedencia

El plugin directo también se configura sin el wrapper. Se leen una vez en init:

| Variable | Valor inicial / contrato |
| --- | --- |
| GSR_RUST_IMAGE | Ruta obligatoria PNG/JPG/GIF |
| GSR_OVERLAY_X, GSR_OVERLAY_Y | 32, 32; enteros con signo |
| GSR_OVERLAY_WIDTH | Opcional; 320 efectivo si tampoco se indica altura |
| GSR_OVERLAY_HEIGHT | Opcional |
| GSR_OVERLAY_KEEP_ASPECT | true; false exige ancho y alto efectivos explícitos |
| GSR_OVERLAY_VISIBLE | true |

Booleanos de entorno: exactamente `true` o `false`. Valores inválidos se rechazan,
no se corrigen silenciosamente. Oculto no permite una fuente o geometría inválida.
Los flags CLI sobrescriben únicamente las variables correspondientes; las otras
variables exportadas siguen vigentes. `--keep-aspect` y `--visible` permiten
revertir `false` exportados. Ancho heredado más alto CLI forman una caja; para
altura solamente, no exportar ancho. Cada proceso hijo recibe argumentos/env
estructurados, no comandos construidos para shell.

El informe guarda variables originales y geometría/visibilidad efectiva resuelta
por Rust. Los scripts anteriores GIF Rust también reconocen las variables nuevas.
La comparación con la referencia **C** rechaza altura, oculto, deformación o X/Y
negativos porque C no los implementa; no se deben comparar layouts distintos.
Los scripts del prototipo C no adquieren estas opciones y permanecen intactos.

## Diseño y garantías conservadas

`config.rs` valida un `ElementConfig` y resuelve `Placement` con dimensiones
intrínsecas de la fuente. No contiene OpenGL ni comportamiento de avatar. El
renderizador solo usa ese rectángulo; el loader conserva sus formatos reales.
Son tipos concretos, sin traits de motor, ECS ni sistema de plugins propio.
La cdylib actual es 0.4.0 / versión de plugin 4, con la ABI GSR conocida.

La configuración se resuelve antes de renderizar; no hay lecturas/parseo en draw.
Escalar cambia el quad GPU, **no** la resolución de las imágenes decodificadas:
poner un GIF pequeño en pantalla no reduce automáticamente el caché original.
PNG libera su RGBA CPU tras upload. GIF sigue precargado, cache ≤16 MiB, temporales
gestionados ≤8 MiB y entrada ≤8 MiB, con mismos tiempos/disposal/loops. Preserva
alfa premultiplicado, estado GL, contexto/hilo, deinit y barreras de panic.

## Verificación y límites

La suite comprueba ABI, geometría, transparencia, GIF y cierre en GL offscreen;
la CLI tiene pruebas de defaults, precedencia, tamaños y entradas inválidas.
Consulta [desarrollo](desarrollo.md) y [estado](estado.md) para repetir pruebas y
distinguirlas de una grabación real. No se prometen métricas de otra compilación.
