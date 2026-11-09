# Contrato FFI y OpenGL — plugin Rust

Plugin en el mismo proceso que GSR, no sandbox. Referencia: cabecera 0.1 del
commit `f97d1e392816503282d20a0804c3ce3fd2943767`.

## ABI y propiedad

`abi.rs`: structs repr(C), dimensiones/versiones u32, enums entrantes c_int
validados antes de usarlos. No enums Rust construidos desde valores C sin validar.
Callbacks extern C y Option<fn> para NULL; nombre NUL-terminado de vida estática.
`rust_abi.c`/`abi-layout` comparan todos los offsets, tamaños y alineaciones, enums
C y tamaños de bool/callback contra el header real. Solo valida el target usado.
El build exige commit conocido y sin cambios en header/cargador/recorder. El
manifiesto liga GSR/plugin/header/lockfile por hash; el CLI de medición rechaza
otro binario. GSR no negocia por sí mismo compatibilidad de layouts.

**Obligaciones del host para los unsafe en lib.rs:** params alineados, legibles
e inicializados; ret válido, exclusivo y sin solaparse con params. NULL se rechaza;
no se puede detectar un puntero colgante/incorrecto con esa comprobación.
Init transfiere un único Box<State> a userdata. El host lo devuelve intacto,
serializa todos los callbacks, sin reentrancia, y llama deinit exactamente una
vez después del último callback. No usar userdata después del cierre. No se
guardan referencias a memoria params/ret del host.

## Panic

Release usa panic=unwind. Los dos exports y tres callbacks entran por
catch_unwind; errores esperados usan Result. En init, panic devuelve false sin
publicar userdata. En draw/damage/clear se marca la instancia como fallida antes
del trabajo; un unwind la deja desactivada. Deinit todavía consume el Box.
El payload capturado se olvida excepcionalmente para evitar que su Drop provoque
otro panic. No se instala hook global; el hook existente puede imprimir el panic
antes de capturarlo. Los errores al escribir diagnóstico se ignoran.

No se recuperan abort, OOM abortivo, doble panic de destructores, SIGSEGV, corrupción
o fallo nativo/driver. Compilar con panic=abort cambia la política validada.
La feature test-hooks inyecta panic en los cinco callbacks y comprueba que el
host C/ctypes continúa vivo y no quedan recursos GL del plugin tras deinit.
Se prueba además un payload cuyo Drop panica. Esa biblioteca vive en otro
directorio y nunca se copia como artefacto de producción.
En entrega 3 incluye además un reloj determinista para pruebas, con el mismo
contrato de userdata serializado y catch_unwind. El export no está en producción;
no es IPC ni control del reloj de una grabación real.

## OpenGL y unsafe en render.rs

Los únicos enlaces nativos propios son consultas de contexto/símbolos EGL/GLX.
glow carga funciones con contexto ya actual. Se requiere GLES3 o GL3 con sampler
objects (GL3.3/ARB_sampler_objects). La carga de símbolos depende de bibliotecas
del sistema que permanecen enlazadas mientras vive la cdylib.

**Obligaciones del host:** contexto vivo y actual, mismo hilo en init/draw/deinit,
sin destrucción/reutilización a espaldas del plugin. GSR inspeccionado llama
deinit antes de destruir su infraestructura gráfica. Renderer comprueba ThreadId
y handle de contexto; Rc hace que los objetos no sean Send/Sync. El host sigue
siendo responsable de no entrar concurrentemente con punteros raw.

Todo nombre GL se registra al crearlo y se borra una vez mediante un propietario
que comprueba contexto/hilo también en Drop por error/unwind. Si faltan, se
registran y abandonan los nombres en lugar de borrarlos en un contexto ajeno;
el driver los libera al destruir el contexto original. No se promete recuperar
un contexto ya destruido. Las llamadas unsafe GL se justifican con ese contexto,
objetos vivos, formatos/tamaños validados y ausencia de callbacks simultáneos.

Un guard captura/restaura programa, VAO, VBO, unidad activa, textura/sampler de
unidad 0, PBO de upload, unpack alignment/row length/skips, máscara de color,
blend/factores/ecuaciones, scissor/depth/stencil/cull/rasterizer discard. Framebuffer
y viewport del host no cambian; no se borra la captura. Solo se modifica el VAO
propio. El test instala deliberadamente estado adverso, sampler y PBO del host.

La textura guarda alfa premultiplicado una vez en init; mezcla ONE y
ONE_MINUS_SRC_ALPHA. El filtrado lineal evita interpolar RGB oculto con halos
oscuros. El alfa del escritorio opaco se conserva. No se vuelve a multiplicar
por SRC_ALPHA. Inicialmente SDR 8 bits; HDR se rechaza.

Upload con PBO desligado, unpack conocido, longitud RGBA validada y slice vivo
hasta retornar tex_image_2d/tex_sub_image_2d. Son píxeles del overlay: no hay lectura de pantalla
ni glReadPixels. Esta declaración no incluye el host de pruebas, que sí lee
el framebuffer fuera del plugin para comparar resultados.

## Archivos, buffers y draw

La ruta nueva `GSR_RUST_SCENE` acepta un manifiesto JSON interno de hasta 128 KiB
con tipos serde, campos desconocidos rechazados, hasta 16 capas y un avatar.
`scene.rs` valida también geometría/umbrales y suma los bytes RGBA (≤64 MiB
retenidos, incluyendo ocultos y ambos estados). No es techo RSS; durante rechazo
puede haber una capa adicional y temporales de decoder. PNG/JPG liberan CPU tras
upload; cada fuente mantiene su textura propia. No se deduplican archivos.
JPG usa zune-jpeg 0.4.21 sin features SIMD unsafe, con dimensiones/cabecera
validadas antes de decode, salida RGBA ≤16 MiB y máximo 64 scans. Memoria auxiliar
del decoder y driver no se incluye en el presupuesto de píxeles.

`microphone.rs` no usa FFI/unsafe ni GL: un hilo lee un buffer fijo de 1280 bytes
de un hijo parec; comunica dos booleanos atómicos relajados (no publican otros
datos). No hay mutex, I/O ni espera de audio en draw. Drop mata/espera al hijo y
une el hilo, fuera de draw; el hilo solo posee stdout y sus Arc. Si el hijo deja
de producir sin cerrar, puede quedar lectura bloqueada hasta deinit, que mata
el proceso. La pérdida de tubería desactiva el overlay y genera diagnóstico.
El CLI precomprueba la fuente y usa el mismo nombre resuelto para GSR y parec.
El detector no toca los relojes ni buffers del audio grabado. No se promete
sincronía visual con voz hasta probar en hardware. Las mismas barreras de panic,
propiedad de userdata y contexto/hilo cubren ahora la lista de renderizadores.

La configuración de un elemento se valida una vez en init, mediante código
seguro en `config.rs`. La geometría resuelta contiene dimensiones positivas
acotadas y coordenadas finitas; escalar modifica el quad, no los buffers del
recurso. No añade operaciones unsafe ni lecturas de configuración en draw.
La visibilidad también es inicial: oculto conserva caché y objetos GL, devuelve
sin dibujar/subir textura y no solicita daño propio. Deinit conserva las mismas
obligaciones de hilo/contexto incluso si nunca se dibujó. No es control en vivo.
Ver [configuración y límites](../docs/configuracion-elemento.md).

PNG estático o GIF precargado; APNG/malformados rechazados. Para PNG en init: entrada comprimida ≤8 MiB,
dimensiones 1..4096, RGBA ≤16 MiB, presupuesto del decoder 32 MiB, sin texto/ICC.
IHDR se comprueba antes de decodificar y GL_MAX_TEXTURE_SIZE antes de subir. Se
convierte a RGBA8; sin gestión ICC ni soporte HDR PNG; 16 bits se reducen a 8.
Son límites de buffers/decoder, no un techo absoluto de RSS: temporales, allocator,
metadatos y driver cuestan aparte. OOM puede abortar pese al manejo de reservas.

GIF añade un recorrido seguro de bloques antes de asignar/cachear o decodificar:
entrada ≤8 MiB, ≤1024 frames, cache RGBA ≤16 MiB y canvas/índices/snapshot de
restore-previous ≤8 MiB. Se rechazan rectángulos fuera de lienzo, disposal
reservado, Plain Text, trailer ausente y LZW incompleto. Decoder indexado con
memoria de salida por frame limitada y read_into_buffer reutilizado; su límite
no incluye toda la memoria auxiliar de LZW/allocator. Ver [entrega 3](../docs/cli-escena.md).

Tras init siempre se destruyen archivo, entrada comprimida, decoder y temporales.
PNG además libera RGBA CPU tras upload; GIF mantiene los frames finales en cache
de la instancia hasta deinit. Draw usa el reloj monotónico, selecciona índice,
sube un frame **ya decodificado** solo si cambia y dibuja. No lee archivos ni
configuración, no decodifica ni asigna buffers RGBA. El slice de upload pertenece
al cache vivo, con largo exacto validado antes de usarlo desde GL.
Los tests eliminan PNG/GIF después de init; la animación y la restauración GL,
incluido el PBO durante cambios de frame, siguen pasando. Damage se reconoce
solo al completar draw, no en clear_damage que GSR llama antes de dibujar.

## Dependencias y alcance de revisión

Actualización 0.4.0: se añaden serde 1.0.229 + derive, serde_json 1.0.154 y
zune-jpeg 0.4.21 (`std`, sin SIMD); zune-core 0.4.12 transitivo. Licencias leídas
en fuentes/manifiestos de cache: serde/serde_json MIT OR Apache-2.0;
zune-jpeg MIT OR Apache-2.0 OR Zlib, zune-core MIT OR Apache-2.0 OR Zlib.
Ver alcance y pruebas en [CLI/escena](../docs/cli-escena.md).

Directas fijadas: png 0.18.1 y gif 0.13.3 (MIT OR Apache-2.0), glow 0.17.0 (MIT OR Apache-2.0
OR Zlib), verificadas en manifiestos/fuentes locales. GIF usa std sin color_quant;
añade weezl 0.1.12 transitivo (MIT OR Apache-2.0). Cargo.lock conserva versiones
y checksums. No se usa wgpu/Tokio ni todos los codecs de image. Licencias transitivas
leídas: combinaciones alternativas MIT/Apache-2.0/0BSD/Zlib. La licencia de
distribución del producto aún no está elegida; GSR sigue siendo GPL-3.0-only.

La auditoría actualizada de vulnerabilidades del lockfile sigue pendiente antes
de distribuir. No se afirma ausencia de advisories. El build normal usa
`--offline --locked`; las versiones y checksums están fijados.

Fuentes oficiales, además del código local:

- [Rust FFI/unwind](https://doc.rust-lang.org/nomicon/ffi.html).
- [glow 0.17.0](https://docs.rs/glow/0.17.0/glow/struct.Context.html).
- [Manifiesto PNG](https://docs.rs/crate/png/0.18.1/source/Cargo.toml.orig).
- [Código GIF upstream](https://github.com/image-rs/image-gif).
- [RustSec](https://github.com/RustSec/advisory-db).
