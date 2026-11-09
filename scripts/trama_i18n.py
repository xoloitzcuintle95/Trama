"""Local TUI translations and UI preference; no network or profile mutations.

Only explicit message literals pass through tr(). User paths, device names and
layer names are never translated. Native/backend diagnostics stay verbatim.
"""
import json
import os
from pathlib import Path
import tempfile
import tomllib

LANGUAGES = ('auto', 'es', 'en')
_language = 'es'  # Importing a view never reads the user's environment or disk.
_preference = 'auto'


def detect_language(environment=None):
    environment = os.environ if environment is None else environment
    value = next((environment.get(key) for key in ('LC_ALL', 'LC_MESSAGES', 'LANG')
                  if environment.get(key)), '')
    return 'es' if value.lower().split('_')[0].split('-')[0].split('.')[0].split('@')[0] == 'es' else 'en'


def preference_path():
    base = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
    return base/'trama/ui.toml'


def read_preference(path=None):
    try:
        value = tomllib.loads((path or preference_path()).read_text(encoding='utf-8')).get('language', 'auto')
        return value if value in LANGUAGES else 'auto'
    except (OSError, ValueError):
        return 'auto'


def select_language(preference, environment=None):
    global _language, _preference
    if preference not in LANGUAGES:
        raise ValueError('language must be auto, es or en')
    _preference = preference
    _language = detect_language(environment) if preference == 'auto' else preference


def language():
    return _language


def preference():
    return _preference


def save_preference(value, path=None):
    if value not in LANGUAGES:
        raise ValueError('language must be auto, es or en')
    target = path or preference_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write('language = '+json.dumps(value)+'\n')
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def tr(message):
    return EN.get(message, message) if _language == 'en' else message


EN = {'Listo. r Grabar | t Prueba de 30 s': 'Ready. r Record | t 30-second test',
 'No hay opciones. u actualiza los dispositivos desde el inicio.': 'No options available. Press u to refresh '
                                                                   'devices.',
 '↑↓ elegir  Enter aceptar  Esc volver': '↑↓ select  Enter accept  Esc back',
 'Enter aplicar  Esc cancelar  Ctrl+U borrar  ←→ cursor': 'Enter apply  Esc cancel  Ctrl+U clear  ←→ cursor',
 'VALOR': 'VALUE',
 '↑↓ elegir  Enter abrir/elegir  p Escribir ruta  Esc volver': '↑↓ select  Enter open/select  p Type path  '
                                                               'Esc back',
 'Espacio: usar esta carpeta. p: escribir también una carpeta nueva.': 'Space: use this folder. p: type a '
                                                                       'path, including a new folder.',
 'Ruta obligatoria': 'Path required',
 'No es una carpeta': 'Not a folder',
 'No existe un archivo regular': 'No regular file exists at this path',
 'Ruta (relativa a la carpeta mostrada)': 'Path (relative to the displayed folder)',
 'Actualizado. s guarda el perfil.': 'Updated. Press s to save the profile.',
 'Perfil disponible; no se pudo recordar la sesión: ': 'Profile available; could not remember the session: ',
 'Guardar perfil TOML como': 'Save TOML profile as',
 'El perfil ya existe': 'Profile already exists',
 'Reemplazar este TOML': 'Replace this TOML',
 'Cancelar': 'Cancel',
 'Perfil guardado: ': 'Profile saved: ',
 'Cambios sin guardar': 'Unsaved changes',
 'Guardar cambios': 'Save changes',
 'Descartar cambios': 'Discard changes',
 'Seguir editando': 'Keep editing',
 'Pantalla': 'Display',
 'Predeterminado del sistema': 'System default',
 'Sin micrófono (sin avatar)': 'No microphone (no avatar)',
 'Micrófono': 'Microphone',
 'Ya hay un avatar: selecciónalo y pulsa e para editar sus campos.': 'An avatar already exists: select it '
                                                                     'and press e to edit its fields.',
 'Gráfico': 'Graphic',
 'GIF de reposo': 'Idle GIF',
 'GIF de habla': 'Talking GIF',
 'PNG, JPG o GIF': 'PNG, JPG or GIF',
 'Superior izquierda': 'Top-left',
 'Superior derecha': 'Top-right',
 'Inferior izquierda': 'Bottom-left',
 'Inferior derecha': 'Bottom-right',
 'Caja máxima: {size} px (conserva proporción)': 'Maximum box: {size} px (keep aspect ratio)',
 'Margen: {margin} px': 'Margin: {margin} px',
 'X/Y manuales (avanzado)': 'Manual X/Y (advanced)',
 'Colocar ': 'Place ',
 'Esquina + tamaño efectivo según la resolución del monitor.': 'Corner + effective size based on the display '
                                                               'resolution.',
 'Tamaño de la caja (px)': 'Box size (px)',
 'Margen (px)': 'Margin (px)',
 'Posición manual (avanzado)': 'Manual position (advanced)',
 ' en píxeles': ' in pixels',
 '{corner}, caja {size}px, margen {margin}px. s guarda.': '{corner}, box {size}px, margin {margin}px. Press '
                                                          's to save.',
 'Escribe un entero de {minimum} a {maximum}': 'Enter an integer from {minimum} to {maximum}',
 'Rango: {minimum}..{maximum}': 'Range: {minimum}..{maximum}',
 'Nombre': 'Name',
 'GIF reposo': 'Idle GIF',
 'GIF habla': 'Talking GIF',
 'Umbral RMS': 'RMS threshold',
 'Espera (ms)': 'Release (ms)',
 'Archivo': 'File',
 'Esquina y tamaño': 'Corner and size',
 'Ancho': 'Width',
 'Alto': 'Height',
 'Conservar proporción': 'Keep aspect ratio',
 'X manual (avanzado)': 'Manual X (advanced)',
 'Y manual (avanzado)': 'Manual Y (advanced)',
 'automático': 'automatic',
 '4 esquinas + caja': '4 corners + box',
 'Editar un campo / ': 'Edit one field / ',
 'Cambiar ': 'Change ',
 "Solo cambia este campo. Ancho/alto: '-' deriva automáticamente.": 'Only this field changes. Width/height: '
                                                                    "'-' derives automatically.",
 'Consultando pantallas y micrófonos…': 'Querying displays and microphones…',
 'Validando pantalla, audio y recursos… x cancela': 'Validating display, audio and assets… x cancels',
 'Dispositivos actualizados.': 'Devices updated.',
 'Revisa pantalla/micrófono. u reintenta la consulta.': 'Check display/microphone. Press u to query again.',
 'GRABANDO — x o Ctrl+C detiene': 'RECORDING — x or Ctrl+C stops',
 'Grabación guardada. o muestra el MKV.': 'Recording saved. Press o to view the MKV.',
 'Grabación cancelada antes del inicio.': 'Recording cancelled before starting.',
 'El avatar necesita una entrada de micrófono. m permite elegirla.': 'The avatar needs a microphone input. '
                                                                     'Press m to choose one.',
 'Primera prueba': 'First test',
 'Guardar perfil y grabar 30 segundos': 'Save profile and record for 30 seconds',
 'Guardar y seguir editando': 'Save and keep editing',
 'Seguir editando sin guardar': 'Keep editing without saving',
 'La captura usa el monitor completo, audio del sistema y micrófono elegidos.': 'Capture uses the full '
                                                                                'display, system audio and '
                                                                                'selected microphone.',
 'Elegir pantalla': 'Choose display',
 'Cambiar FPS': 'Change FPS',
 'Actualizar dispositivos': 'Refresh devices',
 'Elegir micrófono': 'Choose microphone',
 'Alternar audio del juego/sistema': 'Toggle game/system audio',
 'Carpeta de grabaciones': 'Recordings folder',
 'Nombre del video': 'Video filename',
 'Ver último MKV': 'View last MKV',
 'Grabar': 'Record',
 'Prueba de 30 segundos': '30-second test',
 'Guardar perfil': 'Save profile',
 'Guardar como': 'Save as',
 'Cargar perfil': 'Load profile',
 'Primeros pasos': 'Getting started',
 'Diagnóstico': 'Diagnostics',
 'Editar un campo': 'Edit one field',
 'Ocultar / mostrar': 'Hide / show',
 'Quitar capa': 'Remove layer',
 'Mover hacia el fondo': 'Move toward the back',
 'Mover hacia delante': 'Move toward the front',
 'Agregar gráfico': 'Add graphic',
 'Agregar avatar': 'Add avatar',
 'Acciones / ': 'Actions / ',
 'Ayuda': 'Help',
 'NAVEGACIÓN': 'NAVIGATION',
 'Tab           Siguiente sección': 'Tab           Next section',
 'Shift+Tab     Sección anterior': 'Shift+Tab     Previous section',
 '↑ / ↓         Elegir campo, capa o acción': '↑ / ↓         Select field, layer or action',
 'Enter         Editar o ejecutar la selección': 'Enter         Edit or activate selection',
 'Espacio       Acciones de la sección': 'Space         Section actions',
 '? / F1        Abrir esta ayuda': '? / F1        Open this help',
 'q / Esc       Salir (avisa si hay cambios)': 'q / Esc       Quit (warns about unsaved changes)',
 'PERFIL Y GRABACIÓN': 'PROFILE AND RECORDING',
 'r             Grabar hasta detener manualmente': 'r             Record until stopped manually',
 't             Grabar una prueba de 30 segundos': 't             Record a 30-second test',
 's             Guardar perfil': 's             Save profile',
 'S             Guardar perfil como…': 'S             Save profile as…',
 'l             Cargar perfil': 'l             Load profile',
 'o             Ver la ruta completa del último MKV': 'o             View the full path of the last MKV',
 'w             Abrir primeros pasos': 'w             Open getting started',
 '!             Ver diagnóstico': '!             View diagnostics',
 'CAPTURA, AUDIO Y SALIDA': 'CAPTURE, AUDIO AND OUTPUT',
 'p             Elegir pantalla': 'p             Choose display',
 'f             Cambiar FPS': 'f             Change FPS',
 'm             Elegir micrófono': 'm             Choose microphone',
 'g             Activar/desactivar audio del sistema': 'g             Toggle system audio',
 'd             Elegir carpeta de grabaciones': 'd             Choose recordings folder',
 'n             Nombre del video; admite {timestamp}': 'n             Video filename; supports {timestamp}',
 'u             Actualizar dispositivos': 'u             Refresh devices',
 'CAPAS': 'LAYERS',
 'a             Agregar gráfico PNG, JPG o GIF': 'a             Add PNG, JPG or GIF graphic',
 'v             Agregar avatar con reposo y habla': 'v             Add avatar with idle and talking GIFs',
 'e             Editar un campo de la capa seleccionada': 'e             Edit one field of the selected '
                                                          'layer',
 'c             Elegir esquina y tamaño': 'c             Choose corner and size',
 'h             Ocultar/mostrar capa': 'h             Hide/show layer',
 'Supr / D      Quitar capa sin borrar sus archivos': 'Del / D       Remove layer without deleting files',
 '[             Mover capa hacia el fondo': '[             Move layer toward the back',
 ']             Mover capa hacia delante': ']             Move layer toward the front',
 'DURANTE LA GRABACIÓN': 'DURING RECORDING',
 'x / Ctrl+C    Detener y volver a Trama': 'x / Ctrl+C    Stop and return to Trama',
 'q / Esc       Detener y salir': 'q / Esc       Stop and quit',
 'La vista permanece estática hasta cambiar de estado.': 'The view stays static until its state changes.',
 'EDICIÓN Y ARCHIVOS': 'EDITING AND FILES',
 'Esc           Cancelar y volver': 'Esc           Cancel and go back',
 'Ctrl+U        Borrar el campo de texto': 'Ctrl+U        Clear text field',
 '← / →         Mover el cursor en un campo de texto': '← / →         Move the cursor in a text field',
 'Enter         Aplicar valor o abrir/elegir archivo': 'Enter         Apply value or open/select file',
 'p             Escribir ruta en el selector de archivos': 'p             Type path in the file picker',
 'Espacio       Usar carpeta actual en selector de carpetas': 'Space         Use current folder in folder '
                                                              'picker',
 '↑↓ desplazar  Enter / Esc volver': '↑↓ scroll  Enter / Esc back',
 'Aún no hay una grabación en esta sesión.': 'No recording in this session yet.',
 'Guardada': 'Saved',
 'Parcial o pendiente de comprobación': 'Partial or not yet verified',
 'Último MKV': 'Last MKV',
 'Carpeta: ': 'Folder: ',
 'Informe: ': 'Report: ',
 'Cerrando la grabación… espera al MKV.': 'Closing recording… wait for the MKV.',
 'Cerrando grabación antes de salir…': 'Closing recording before quitting…',
 'Nombre del video — admite {timestamp}': 'Video filename — supports {timestamp}',
 'Ejemplo: minecraft-{timestamp}.mkv. Sin carpetas.': 'Example: minecraft-{timestamp}.mkv. No folders.',
 'Quitar ': 'Remove ',
 'Quitar capa (no borra el archivo)': 'Remove layer (keeps the file)',
 'Cargar perfil TOML': 'Load TOML profile',
 'Perfil cargado. r graba; e edita un solo campo.': 'Profile loaded. r records; e edits one field.',
 'Cerrando grabación…': 'Closing recording…',
 'TOML; sin argumento recupera el último perfil o ./perfil.toml': 'TOML; without an argument, reopen the '
                                                                  'last profile or ./perfil.toml',
 'La TUI necesita una terminal interactiva. Usa compositor.py record para grabar sin TUI.': 'The TUI needs '
                                                                                            'an interactive '
                                                                                            'terminal. Use '
                                                                                            'compositor.py '
                                                                                            'record without '
                                                                                            'a TUI.',
 'Trama: TUI local para perfiles del compositor GSR, sin previsualización.': 'Trama: local TUI for GSR '
                                                                             'compositor profiles, without '
                                                                             'preview.',
 'CONFIGURACIÓN INCOMPLETA': 'SETUP INCOMPLETE',
 'LISTO': 'READY',
 'Compositor GSR': 'GSR compositor',
 '  · sin guardar': '  · unsaved',
 'CERRANDO': 'CLOSING',
 'GRABANDO': 'RECORDING',
 'PREPARANDO': 'PREPARING',
 'x / Ctrl+C detener · q detener y salir': 'x / Ctrl+C stop · q stop and quit',
 'TRAMA: amplía la terminal a 72 columnas × 20 filas.': 'TRAMA: enlarge the terminal to 72 columns × 20 '
                                                        'rows.',
 'q salir | x / Ctrl+C detener si se está grabando': 'q quit | x / Ctrl+C stop while recording',
 'Predeterminado': 'Default',
 'Desactivado': 'Disabled',
 'Elegir pantalla…': 'Choose display…',
 'Resolución por consultar': 'Resolution not queried',
 'Captura    ': 'Capture    ',
 'Capas      ': 'Layers     ',
 ' visibles': ' visible',
 'r  GRABAR': 'r  RECORD',
 't  Prueba de 30 segundos': 't  30-second test',
 's  Guardar perfil': 's  Save profile',
 'Monitor completo · H.264 · GPU · SDR': 'Full display · H.264 · GPU · SDR',
 'La misma entrada activa el avatar y se graba.': 'The same input drives the avatar and is recorded.',
 'Juego / sistema': 'Game / system',
 'Activado': 'Enabled',
 'Enter cambia el ajuste seleccionado.': 'Enter changes the selected setting.',
 'Carpeta': 'Folder',
 'MKV · {timestamp} se sustituye al grabar.': 'MKV · {timestamp} is replaced when recording starts.',
 'Último MKV: ': 'Last MKV: ',
 'VISIBILIDAD / CAPA · última encima': 'VISIBILITY / LAYER · last on top',
 ' · oculta': ' · hidden',
 'Sin capas. a agrega un gráfico; v un avatar.': 'No layers. a adds a graphic; v an avatar.',
 'PROPIEDADES · ': 'PROPERTIES · ',
 'Posición  X {x}  Y {y}': 'Position  X {x}  Y {y}',
 'Caja  {width} × {height} · ': 'Box  {width} × {height} · ',
 'proporción conservada': 'aspect ratio preserved',
 'libre': 'free',
 'Avatar reactivo': 'Reactive avatar',
 'Enter edita un campo': 'Enter edits one field',
 'c elige esquina y tamaño': 'c chooses corner and size',
 '[ / ] cambia el orden': '[ / ] changes the order',
 ' · o detalles': ' · o details',
 'Prueba 30 s': '30 s test',
 'Guardar': 'Save',
 'Editar': 'Edit',
 'Agregar': 'Add',
 'Colocar': 'Place',
 'Mostrar/ocultar': 'Show/hide',
 'Elegir': 'Select',
 'Actualizar': 'Refresh',
 'Cambiar': 'Change',
 'Sección': 'Section',
 'Espacio': 'Space',
 'Acciones': 'Actions',
 'Salir': 'Quit',
 'Interfaz en reposo · GSR conserva el control de la captura': 'Interface idle · GSR controls capture',
 'Esperando a que GSR cierre el archivo…': 'Waiting for GSR to close the file…',
 'Pantalla mínima. Los paneles no se redibujan.': 'Minimal view. Panels are not redrawn.',
 'Validando pantalla, micrófono y recursos…': 'Validating display, microphone and assets…',
 'Parada automática: {seconds:g} s': 'Automatic stop: {seconds:g} s',
 'Sin duración fija': 'No fixed duration',
 '[ x ] Detener y volver    [ Ctrl+C ] Detener': '[ x ] Stop and return    [ Ctrl+C ] Stop',
 'Detener y salir': 'Stop and quit',
 'Espera al cierre antes de cerrar la terminal': 'Wait for recording to finish before closing the terminal',
 'Idioma / Language': 'Language / Idioma',
 'Automático (sistema)': 'Automatic (system)',
 'Idioma guardado.': 'Language saved.',
 'L             Idioma / Language': 'L             Language / Idioma',
 'Idioma de la interfaz (auto, es, en); solo esta ejecución': 'Interface language (auto, es, en); this run '
                                                              'only'}
