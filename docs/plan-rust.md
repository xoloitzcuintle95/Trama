# Dirección técnica y siguientes etapas

Estado actual: plugin, GIFs, avatar, capas y TUI bilingüe implementados. El usuario
confirmó funcionamiento de la TUI y una grabación de 10 minutos en su laptop.
El trabajo actual es el [paquete preliminar local](paquete-preliminar.md), sin
streaming ni cambios al núcleo de GSR. El resto de este documento conserva el
plan técnico y sus criterios de validación; no implica pruebas ya realizadas.


Prioridad: grabar videojuegos y sesiones de desarrollo con buen rendimiento,
estabilidad y audio sincronizado. GSR mantiene captura/audio/codificación; Rust
compone y Python controla. Un cambio de lenguaje no garantiza ahorro de recursos.

Plataforma objetivo: Wayland, con COSMIC como referencia. No se desarrollan modos
exclusivos de X11; eso no requiere retirar sus rutas internas del motor upstream.

## Base actual

La [TUI](tui.md) y [CLI](guia-cli.md) comparten perfiles TOML y grabador. El plugin
Rust carga PNG/JPG/GIF, ordena capas y alterna reposo/habla por nivel del micrófono.
La composición y los comportamientos están separados sin ECS ni framework propio.
Los archivos se precargan con límites; no se decodifican cuadros de pantalla en CPU.

## Antes de distribuir

1. Validar el flujo TUI con GSR real y sesiones prolongadas comparables.
2. Elegir nombre y mascota propios; los ejemplos geométricos no son la mascota.
3. Preparar un build reproducible desde un árbol sin perfiles ni recursos privados.
4. Diseñar el paquete conjunto con una compilación conocida de GSR, helper KMS y
   plugin, sin reemplazar el GSR del sistema ni añadir su GUI.
5. Revisar dependencias, licencias y matriz de compatibilidad antes de publicar.

Cada punto requiere un encargo concreto. El empaquetado no está implementado.

## Actualizaciones de GSR

Fijar un commit por entrega y comprobar cambios de ABI, captura, render y audio
antes de actualizar. Comparar layouts, ejecutar pruebas automatizadas y grabar
realmente antes de cambiar la versión distribuida. No prometer compatibilidad con
cualquier ejecutable de igual número de versión ni saltarse hashes para admitirlo.

## Funciones futuras

Streaming requiere verificar los transportes y controles reales de GSR y de los
destinos; las credenciales deben quedar fuera del repositorio y los logs. Grabar
y emitir simultáneamente con una sola instancia no está validado. No se crea otro
motor de captura por anticipado. Texto, control en vivo y múltiples escenas quedan
para entregas posteriores basadas en necesidades y mediciones.
