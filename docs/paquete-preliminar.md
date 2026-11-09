# Paquete preliminar de Trama

Estado: evaluación local para **Pop!_OS 24.04 / amd64 / Wayland-COSMIC**.
No es una publicación estable ni una promesa de compatibilidad con otras distros.
La versión de aplicación es `0.1.0~alpha1`; el plugin conserva su versión 0.4.0
porque son componentes con versionado independiente.

## Qué contiene

- Comando `trama`, TUI bilingüe y CLI compartida de grabación.
- Plugin Rust y validador de escenas del build verificado.
- GSR **6.1.7**, commit `f97d1e392816503282d20a0804c3ce3fd2943767`, y su
  `gsr-kms-server`, privados en `/usr/lib/trama/engine/`.
- Icono, entrada de aplicaciones con `Terminal=true`, perfil neutro de muestra,
  manual TUI y avisos de dependencias.

No contiene la GUI de GSR, `gsr-cli`, videos, perfiles personales, compiladores,
referencia C, tests, targets de desarrollo ni bibliotecas multimedia copiadas.
Las bibliotecas y herramientas del sistema se declaran como dependencias de APT.
El motor conserva sus capacidades internas: no se ha recortado ni reescrito GSR.
Aunque el objetivo sea Wayland, el binario upstream conserva dependencias X11.

Trama elige su motor privado cuando existe el directorio `engine/`. No instala
`gpu-screen-recorder` en el PATH global ni reemplaza el GSR nativo existente.
El manifiesto comprueba los hashes de motor, plugin, helper y validador. No
acepta sustituir solo una de esas piezas por otra versión.

## Construcción local sin sudo

Requiere el build existente y verificado de GSR/plugin, herramientas de Debian
(`dpkg-deb`, `dpkg-shlibdeps`), Cargo/Rust y las dependencias del lockfile
presentes en caché. Para los builds del motor/plugin, consulta
[desarrollo](desarrollo.md) y el [manual](guia-cli.md#2-instalación-y-requisitos).

```bash
python3 scripts/build-deb.py
```

El resultado queda en `build/packages/`:

```text
trama_0.1.0~alpha1_amd64.deb
trama_0.1.0~alpha1_amd64-sources.tar.xz
trama_0.1.0~alpha1_amd64.sha256
```

`--output /ruta/a/carpeta` cambia el directorio de salida. No hay instalaciones,
`setcap`, servicios ni cambios a `/usr` durante la construcción.

El archivo de fuentes va separado del runtime: incluye código propio, snapshot
upstream y dependencias Cargo vendorizadas con sus avisos. Desde su raíz,
`bash packaging/rebuild-from-source.sh` recompila sin instalar, con las
herramientas/dependencias nativas previamente disponibles. No se promete identidad
binaria entre compiladores o entornos diferentes. Los snapshots no incluyen Git.

## Inspección e instalación en la laptop

Primero revisa el archivo y los hashes, sin sudo:

```bash
cd build/packages
sha256sum -c trama_0.1.0~alpha1_amd64.sha256
dpkg-deb --info trama_0.1.0~alpha1_amd64.deb
dpkg-deb --contents trama_0.1.0~alpha1_amd64.deb
```

La siguiente orden **requiere sudo**. Ejecutarla instala el paquete y permite a
APT resolver sus dependencias; el agente no la ejecuta:

```bash
sudo apt install './trama_0.1.0~alpha1_amd64.deb'
```

Luego, desde una terminal de tu sesión gráfica, sin sudo:

```bash
trama --help
trama /ruta/a/tu/perfil.toml
```

La entrada de aplicaciones también solicita una terminal; no es una GUI. Su
integración con el lanzador COSMIC debe comprobarse tras instalar.

## Helper KMS y permisos

Solo el helper KMS requiere privilegios para la ruta de captura directa. Este
paquete no incluye scripts de instalación que otorguen capacidades. Sin ellas,
GSR utiliza su mecanismo upstream de autenticación con `pkexec`; debe existir
un agente Polkit funcional en la sesión. Las consultas de dispositivos tienen
un timeout: si la autenticación tarda demasiado, usa `u` para reintentarlas.

Si se decide usar el mismo mecanismo de capacidades del instalador upstream,
esta orden **requiere sudo** y debe ejecutarse explícitamente tras revisar el
paquete; no se aplica al Python, plugin ni motor principal:

```bash
sudo setcap cap_sys_admin+ep /usr/lib/trama/engine/gsr-kms-server
```

Comprobación sin sudo:

```bash
getcap /usr/lib/trama/engine/gsr-kms-server
```

La orden necesita `setcap` de `libcap2-bin`. Si falta, su instalación también
requiere sudo:

```bash
sudo apt install libcap2-bin
```

Una actualización puede reemplazar el helper y quitar su capacidad; vuelve a
revisarla. El `.deb` no incluye setuid ni capacidades persistentes. Para revocar
la capacidad manualmente:

```bash
sudo setcap -r /usr/lib/trama/engine/gsr-kms-server
```

## Configuración y desinstalación

Los TOML existentes se abren sin migración. La preferencia de idioma continúa en
`$XDG_CONFIG_HOME/trama/ui.toml` y el último perfil conserva su ubicación histórica
explicada en la [guía TUI](tui.md). No se escriben gráficos en perfiles personales.

Desinstalar requiere sudo y deja los perfiles/videos del usuario intactos:

```bash
sudo apt remove trama
```

## Verificar el paquete extraído sin instalar

```bash
python3 tests/test_package.py
```

La prueba extrae el `.deb` en una carpeta temporal y comprueba contenido/permisos,
selección del motor privado, manifiesto, rechazo de helper alterado, ayuda,
precarga con el decoder Rust, hashes y fuentes/avisos. No otorga permisos ni
captura la pantalla. Se comprobó además la resolución Cargo offline de las fuentes
vendorizadas y una simulación APT local que no instaló nada. El resolver de
dependencias del host avisó sobre diversiones usr-merge; hay que comprobar APT
también en el sistema objetivo antes de instalar. Para repetir la suite TUI:

```bash
python3 -m unittest discover -s tests -p 'test_trama*.py'
```

## Validación y pendientes

El usuario ya confirmó que instaló el `.deb` y pudo grabar en su laptop.
Además, las pruebas del runtime instalado y el recorrido inicial con estado
limpio pasaron usando dispositivos/captura simulados. No se tocó su perfil.
Los comandos están en [desarrollo](desarrollo.md#probar-la-versión-instalada-sin-usar-perfiles-personales).

Antes de llamar estable al paquete faltan la entrada del lanzador COSMIC, una
instalación limpia y más evidencia de estabilidad/rendimiento. Las pruebas
simuladas no sustituyen la captura KMS ni el audio físico.

El código propio, el icono, la mascota y el hero usan GPL-3.0-only por decisión
del propietario, igual que GSR. El arte fue generado con ChatGPT y entregado para
Trama; no se afirma autoría humana ni exclusividad.
Los avisos originales de GSR y las dependencias se incluyen.

Para actualizar GSR: revisar upstream y ABI, construir y probar motor/plugin,
actualizar el commit esperado y regenerar manifiesto y paquete como conjunto.
No descargar ni cambiar el motor automáticamente en la laptop del usuario.
