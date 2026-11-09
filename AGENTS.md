# Trabajo en este proyecto

## Objetivo
Construir un compositor ligero sobre GPU Screen Recorder (GSR). Prioridad: grabar juegos y sesiones de desarrollo con buen rendimiento y audio sincronizado en Linux. Base actual: capas PNG/JPG/GIF, avatar por micrófono, perfiles TOML y TUI. La aplicación se llama Trama; su identidad visual está en assets/brand/. Visión y etapas en [docs/plan-rust.md](docs/plan-rust.md); streaming sigue fuera del alcance actual; el paquete preliminar local se documenta en [docs/paquete-preliminar.md](docs/paquete-preliminar.md).

Debe consumir menos recursos que OBS con una escena y calidad equivalentes. Los 150 MB mencionados son una aspiración pendiente de medir, no un resultado ni un límite validado.

Objetivo de soporte y validación: Wayland/COSMIC. No ampliar modalidades exclusivas de X11; conservar sin cambios el código upstream de GSR que no sea necesario tocar.

## Criterio de diseño
- Diseña una base que permita incorporar imágenes, animaciones, escenas y otros overlays sin rehacer el compositor. Separa composición y comportamientos cuando aporte claridad; no construyas un framework para funciones hipotéticas.
- Prefiere soluciones simples, legibles y con pocas dependencias. Elige lenguaje, interfaces y mecanismos después de inspeccionar GSR; no fijes arquitectura por las propuestas de conversaciones anteriores.
- Comprueba API, licencia, versiones y compatibilidad en fuentes oficiales y código real. No presupongas que existe una interfaz de plugins adecuada.
- Reutiliza GSR para captura y codificación. Justifica cualquier cambio en su núcleo. Conserva recursos personales fuera del proyecto; usa las muestras neutras de examples/assets en pruebas. Verifica tiempos, bucle y transparencia de los GIF.

## Colaboración
- Trabaja en español. La IA implementa; el usuario evalúa producto y arquitectura. Explica brevemente decisiones importantes y flujo de datos.
- Inspecciona el proyecto y conserva cambios ajenos. Encadena tareas pequeñas autorizadas y correcciones sin pedir confirmación tras cada paso.
- Consulta cambios sustanciales de objetivo o compromisos difíciles de revertir. No hagas commits, publicaciones ni instalaciones del sistema sin autorización.

## Validación y continuidad
- Usa comandos y comprobaciones reales, proporcionales al cambio. Distingue lo probado aquí de lo pendiente en el equipo objetivo: Pop!_OS/COSMIC, Intel Iris Xe y 8 GB RAM.
- Mide el conjunto de procesos y el impacto en CPU, memoria, GPU, fluidez y estabilidad frente a GSR solo y OBS en condiciones comparables. No declares ventajas sin mediciones.
- Primero logra un flujo pequeño de extremo a extremo; amplía después. Si no cumple la ventaja de recursos, resuelve esa limitación antes de sumar funciones.
- Mantén este archivo breve. Registra estado y decisiones necesarias para retomar en documentación separada cuando haga falta; referencia solo archivos existentes.
- Entrega resultado, validación, límites y siguiente paso. No inventes pruebas, resultados ni compatibilidad.
