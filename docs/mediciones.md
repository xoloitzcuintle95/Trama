# Medición reproducible por CLI

Herramientas de desarrollo; los resultados generados no forman parte del proyecto.
Prepara la referencia C con `bash scripts/build-overlay.sh` para la comparación
del prototipo. Para Rust/GIF, usa `scripts/measure-gif.py` con el mismo recurso.

## Ejecutar

Desde una terminal normal de COSMIC, sin sudo ni instalaciones adicionales:

```sh
cd "$HOME/project-gsr-compositor"
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Escritorio quieto, mismas ventanas"
```

Mantén las mismas ventanas y no interactúes durante los aproximadamente 70 s:
primero GSR solo, luego GSR con overlay. Cada prueba tiene 5 s de calentamiento
excluidos del resumen y 30 s solicitados de medición. No abras OBS u otro grabador.
Este primer escenario estático solo establece un caso básico; no representa juegos,
reproducción de video ni un benchmark de fluidez. Para una carga dinámica habrá
que reproducir la misma secuencia, desde el mismo punto, en cada prueba.

Ambas grabaciones usan KMS (`screen`), H.264 por GPU sin fallback a CPU,
30 FPS CFR, calidad `very_high` y sin audio. Solo la segunda carga el plugin.
Se conserva la posición/ancho configurada con `GSR_OVERLAY_X/Y/WIDTH` y se registra.
Un fallo interrumpe la comparación; no se presenta un resultado parcial como éxito.
Ctrl+C detiene la captura y conserva lo ya recogido. El programa envía SIGINT a
GSR al finalizar para guardar el MP4; si no termina en 15 s, fuerza el cierre y
marca la prueba como incompleta.

La carpeta impresa `build/measurements/<fecha-UTC-id>/` contiene:

- `baseline.mp4`, `overlay.mp4`: videos, sin sobrescribir grabaciones anteriores.
- `baseline.log`, `overlay.log`: salida completa de GSR, para verificar captura,
  driver, codificador y posibles errores.
- `*.jsonl`: muestras crudas, incluidas las de calentamiento, procesos y cobertura.
- `*.csv`: muestras del periodo medido de CPU y memoria.
- `summary.json`: medias ponderadas por duración de intervalo, máximos muestreados,
  comandos, hashes del plugin/imagen, kernel, versión GSR y datos de FFprobe.

El muestreo nominal es de 1 s. Un intervalo que cruza el fin del calentamiento
se excluye entero, por lo que el tiempo resumido puede ser menor de 30 s. El
tiempo real cubierto está en `sampled_seconds`, no se presupone exacto.

Para reducir sesgos de orden/temperatura, repetir más adelante invirtiendo el orden:

```sh
python3 scripts/measure.py --media examples/assets/idle.gif \
  --workload "Escritorio quieto, mismas ventanas" --order overlay-first
```

## Interpretar con cuidado

- **CPU:** suma de utime+stime de los procesos observados, sin sumar tiempos de
  hijos esperados para evitar duplicarlos. 100% equivale a un núcleo completo;
  puede superar 100%. No es porcentaje de toda la CPU.
- **Procesos:** se lanza GSR en sesión propia; se buscan procesos de esa sesión
  y sus descendientes, conservando identidad PID+tiempo de creación para seguir
  hijos que se separen. Los procesos que nacen y mueren entre muestras pueden
  escapar al muestreo; también los que se separan antes de observarlos. Se
  guardan nombres/PIDs y errores de acceso. No incluye servicios externos ya
  existentes (COSMIC, servidor de audio), ni un contador del sistema completo.
- **RSS:** suma de memoria residente del conjunto. Puede contar páginas
  compartidas más de una vez. Sus máximos son los observados a 1 s, no un máximo
  absoluto. MiB = 2^20 bytes.
- **PSS:** reparte páginas compartidas entre procesos; solo se publica PSS total
  cuando todos los procesos fueron legibles en todas las muestras. Un helper
  con capabilities puede impedir leer `smaps_rollup`; en ese caso se deja `null`,
  con subtotal legible y cobertura en los datos crudos. No interpretar ese subtotal
  como memoria total, ni sumar RSS y PSS.
- **GPU opcional:** se lee `/proc/<pid>/fdinfo` según la
  [especificación oficial DRM](https://docs.kernel.org/gpu/drm-usage-stats.html).
  Se deduplican descriptores compartidos por driver/dispositivo/client-id y se
  retiene el máximo previo si un contador retrocede temporalmente. Se calcula
  delta de nanosegundos ocupados / tiempo real por motor y dispositivo, sumando
  los clientes observados. `core_percent` representa equivalentes de un motor;
  puede superar 100% en grupos con varios motores y no se normaliza por capacidad.
  No mide frecuencia, potencia, carga total de la GPU ni memoria GPU. Los nuevos
  clientes necesitan dos observaciones; se indica cobertura en segundos. Si no
  hay permisos o contadores, se deja sin dato, nunca se supone consumo cero.
- **Observador:** su CPU está registrada por separado en `monitor_cpu_seconds`;
  no se añade a GSR. El coste de lectura de `/proc` influye en el equipo y debe
  considerarse al comparar. No es un muestreo sin impacto.
- **Video:** FFprobe registra duración/resolución; solo en archivos de hasta
  120 s intenta además contar frames por decodificación (timeout de 60 s).
  El conteo puede fallar sin invalidar los metadatos; se informa por separado.
  El número de frames CFR no demuestra ausencia de duplicados o tirones. Revisar
  ambos videos y los logs; la prueba de 35 s tampoco acredita estabilidad prolongada.

No concluir ventajas frente a OBS ni cumplimiento de 150 MB con esta primera
comparación. Antes de ampliar funcionalidades hay que revisar los datos reales,
validar cobertura y diseñar una carga y configuración equivalentes para OBS.

## Comprobaciones del instrumento

```sh
python3 tests/test_measure.py
```

Siete pruebas: lectura rápida de videos largos, conservación de metadatos ante
timeout de conteo, parseo de stat con nombres especiales, PID reutilizado, PSS ausente,
contadores DRM regresivos e identidad de cliente; más una prueba integrada con
un padre y un hijo que consume CPU, cierre SIGINT y video sintético analizado por
FFprobe. No graban el escritorio ni prueban GPU; no producen resultados de GSR.
