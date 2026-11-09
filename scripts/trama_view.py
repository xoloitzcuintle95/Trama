"""Presentation only: section views, focus hints and a static capture view.
No device queries, decoders, filesystem reads or timers run while painting.
"""
import curses
from trama_i18n import tr, language
from pathlib import Path
import unicodedata

FOCUS = ('overview', 'layers', 'capture', 'audio', 'output')
TITLES = {'overview':'Overview', 'layers':'Layers', 'capture':'Capture', 'audio':'Audio', 'output':'Output'}


def clipped(text, columns):
    used=0
    out=[]
    for char in str(text):
        if not char.isprintable(): char=' '
        size=0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in ('W','F') else 1
        if used+size>columns: break
        out.append(char); used+=size
    return ''.join(out)


class View:
    def __init__(self,screen,put):
        self.screen,self.put=screen,put
        self.styles={
            'base':0,'panel':0,'accent':curses.A_BOLD,'title':curses.A_BOLD,
            'muted':curses.A_DIM,'selected':curses.A_REVERSE,'error':curses.A_BOLD,
            'ok':curses.A_BOLD,'button':curses.A_REVERSE,'border':curses.A_DIM,
        }

    def setup(self):
        if not curses.has_colors(): return
        try:
            curses.start_color()
            colors=(
                (252,234),(252,235),(81,235),(255,234),(247,235),
                (232,81),(203,235),(114,235),(232,81),(242,235),
            ) if curses.COLORS>=256 else (
                (7,0),(7,0),(6,0),(7,0),(7,0),(0,6),(1,0),(2,0),(0,6),(7,0),
            )
            for number,(name,pair) in enumerate(zip(self.styles,colors),1):
                curses.init_pair(number,*pair)
                self.styles[name]=curses.color_pair(number)
            for name in ('accent','title','error','ok','button'):
                self.styles[name]|=curses.A_BOLD
            self.screen.bkgd(' ',self.styles['base'])
        except curses.error:
            # A terminal may advertise fewer colors/pairs than its TERM entry.
            # Existing attributes continue to work without changing its palette.
            pass

    def style(self,name): return self.styles.get(name,0)

    def text(self,y,x,text,style='panel',width=None):
        self.put(y,x,text,self.style(style),width=width)

    def panel(self,y,x,height,width,title,focused=False):
        if height<3 or width<4: return
        for row in range(y,y+height):
            self.text(row,x,' '*width,width=width)
        style='accent' if focused else 'border'
        self.text(y,x,'┌'+'─'*(width-2)+'┐',style,width)
        for row in range(y+1,y+height-1):
            self.text(row,x,'│',style,1)
            self.text(row,x+width-1,'│',style,1)
        self.text(y+height-1,x,'└'+'─'*(width-2)+'┘',style,width)
        self.text(y,x+2,' '+title+' ','accent' if focused else 'muted',width-4)

    def field(self,y,x,width,label,value,selected=False,error=''):
        self.text(y,x,('› ' if selected else '  ')+label+': '+str(value),
                  'selected' if selected else 'panel',width)
        if error and width>=3: self.text(y,x+width-2,' !','error',2)

    def shortcuts(self,y,items):
        _,width=self.screen.getmaxyx()
        x=2
        for key,label in items:
            length=len(key)+len(label)+5
            if x+length>=width: break
            self.text(y,x,key,'accent',len(key));x+=len(key)
            self.text(y,x,' '+label,'muted',len(label)+1);x+=len(label)+3

    def chrome(self,app):
        h,w=self.screen.getmaxyx()
        rec=app.model.profile['recording']
        errors=app.model.errors or app.device_errors
        incomplete=not rec['screen'] or not app.discovered
        badge='ERROR' if errors else tr('CONFIGURACIÓN INCOMPLETA') if incomplete else tr('LISTO')
        self.text(0,2,'TRAMA','title')
        self.text(0,10,tr('Compositor GSR'),'muted',max(0,w-40))
        self.text(0,max(24,w-len(badge)-3),badge,'error' if errors or incomplete else 'ok')
        self.text(1,2,app.model.path.name+(tr('  · sin guardar') if app.model.dirty else ''),'muted',w-23)
        self.text(1,w-19,'L · '+('English' if language()=='en' else 'Español'),'accent',17)
        x=2
        for focus in FOCUS:
            label=' '+TITLES[focus]+' '
            self.text(3,x,label,'selected' if focus==app.focus else 'muted',len(label))
            x+=len(label)+1

    def home(self,app):
        self.screen.erase()
        h,w=self.screen.getmaxyx()
        if app.active:
            if h>=16 and w>=60: self.recording(app)
            else:
                self.text(0,0,tr('CERRANDO') if app.stop_event.is_set() else tr('GRABANDO') if app.started else tr('PREPARANDO'),'error')
                self.text(2,0,tr('x / Ctrl+C detener · q detener y salir'),'accent')
            self.screen.refresh();return
        if h<20 or w<72:
            self.text(0,0,tr('TRAMA: amplía la terminal a 72 columnas × 20 filas.'),'title')
            self.text(2,0,tr('q salir | x / Ctrl+C detener si se está grabando'),'muted')
            self.screen.refresh();return
        self.chrome(app)
        rec=app.model.profile['recording']; layers=app.model.profile['layers']
        mic=rec['microphone']
        micname=app.model.inputs.get(mic,tr('Predeterminado') if mic=='default_input' else mic or tr('Desactivado'))
        screen=rec['screen'] or tr('Elegir pantalla…')
        dimensions=app.model.screens.get(rec['screen'])
        resolution=f'{dimensions[0]} × {dimensions[1]} px' if dimensions else tr('Resolución por consultar')
        def field(y,index,label,value,error=''):
            self.field(y,3,w-7,label,value,app.row==index,error)
            if error: self.text(y+1,5,error,'error',w-10)
        focus=app.focus
        self.text(5,3,TITLES[focus],'title')
        if focus=='overview':
            self.text(7,3,tr('Captura    ')+screen+' · '+str(rec['fps'])+' FPS','panel',w-7)
            self.text(8,3,'Audio      '+micname,'panel',w-7)
            self.text(9,3,tr('Capas      ')+str(len(layers))+' · '+str(sum(l['visible'] for l in layers))+tr(' visibles'),'panel',w-7)
            self.text(10,3,app.model.output_folder,'muted',w-7)
            self.text(11,3,app.model.output_name,'accent',w-7)
            for i,label in enumerate((tr('r  GRABAR'),tr('t  Prueba de 30 segundos'),tr('s  Guardar perfil'))):
                self.text(h-8+i,3,('› ' if app.row==i else '  ')+label,'selected' if app.row==i else 'accent',w-7)
        elif focus=='capture':
            field(7,0,tr('Pantalla'),screen,app.model.errors.get('screen',app.device_errors.get('screen','')))
            self.text(9,5,resolution,'muted',w-10)
            field(11,1,'FPS',rec['fps'],app.model.errors.get('fps',''))
            self.text(14,5,tr('Monitor completo · H.264 · GPU · SDR'),'muted',w-10)
        elif focus=='audio':
            field(7,0,tr('Micrófono'),micname,app.model.errors.get('microphone',app.device_errors.get('microphone','')))
            self.text(9,5,tr('La misma entrada activa el avatar y se graba.'),'muted',w-10)
            field(11,1,tr('Juego / sistema'),tr('Activado') if rec['game_audio'] else tr('Desactivado'))
            self.text(14,5,tr('Enter cambia el ajuste seleccionado.'),'muted',w-10)
        elif focus=='output':
            field(7,0,tr('Carpeta'),app.model.output_folder,app.model.errors.get('folder',''))
            field(10,1,tr('Nombre'),app.model.output_name,app.model.errors.get('name',''))
            self.text(12,5,tr('MKV · {timestamp} se sustituye al grabar.'),'muted',w-10)
            if app.model.last_video:
                self.text(14,5,tr('Último MKV: ')+str(app.model.last_video),'accent',w-10)
        else:
            wide=w>=104
            split=w//2 if wide else w-3
            rows=max(1,h-13 if wide else h-17)
            offset=max(0,app.model.selected-rows+1)
            self.text(6,3,tr('VISIBILIDAD / CAPA · última encima'),'muted',split-5)
            for index,layer in enumerate(layers[offset:offset+rows],offset):
                label=('● ' if layer['visible'] else '○ ')+layer['name']+(tr(' · oculta') if not layer['visible'] else '')
                if any(key.startswith(f'layer.{index}.') for key in app.model.errors): label+=' !'
                self.text(8+index-offset,3,('› ' if index==app.model.selected else '  ')+label,
                          'selected' if index==app.model.selected else 'panel',split-5)
            if not layers: self.text(8,3,tr('Sin capas. a agrega un gráfico; v un avatar.'),'muted',w-7)
            if layers:
                layer=layers[app.model.selected]
                y,x=(7,split+2) if wide else (h-9,3)
                width=w-x-3
                self.text(y,x,tr('PROPIEDADES · ')+layer['name'],'title',width)
                self.text(y+1,x,tr("Posición  X {x}  Y {y}").format(x=layer["x"],y=layer["y"]),'panel',width)
                self.text(y+2,x,tr("Caja  {width} × {height} · ").format(width=layer.get("width","auto"),height=layer.get("height","auto"))+(tr('proporción conservada') if layer['keep_aspect'] else tr('libre')),'panel',width)
                if wide:
                    self.text(y+4,x,tr('Avatar reactivo') if layer['kind']=='avatar' else tr('Gráfico'),'accent',width)
                    self.text(y+6,x,tr('Enter edita un campo'),'muted',width)
                    self.text(y+7,x,tr('c elige esquina y tamaño'),'muted',width)
                    self.text(y+8,x,tr('[ / ] cambia el orden'),'muted',width)
        if app.model.last_video and focus=='overview' and h>=24:
            self.text(h-9,3,tr('Último MKV: ')+app.model.last_video.name+tr(' · o detalles'),'muted',w-7)
        self.text(h-4,3,app.status,'error' if app.model.errors or app.device_errors else 'muted',w-7)
        contexts={
            'overview':[('r',tr('Grabar')),('t',tr('Prueba 30 s')),('s',tr('Guardar'))],
            'layers':[('Enter',tr('Editar')),('a',tr('Agregar')),('c',tr('Colocar')),('h',tr('Mostrar/ocultar'))],
            'capture':[('Enter',tr('Elegir')),('u',tr('Actualizar'))],
            'audio':[('Enter',tr('Cambiar'))],
            'output':[('Enter',tr('Editar')),('o',tr('Último MKV'))],
        }
        self.shortcuts(h-3,contexts[focus])
        self.shortcuts(h-2,[('Tab',tr('Sección')),(tr('Espacio'),tr('Acciones')),('?',tr('Ayuda')),('q',tr('Salir'))])
        self.screen.refresh()

    def recording(self,app):
        h,w=self.screen.getmaxyx()
        stopping=app.stop_event.is_set()
        title=tr('CERRANDO') if stopping else tr('GRABANDO') if app.started else tr('PREPARANDO')
        self.text(0,2,'TRAMA  /  '+title,'error' if app.started else 'accent')
        self.text(2,2,tr('Interfaz en reposo · GSR conserva el control de la captura'),'muted',w-4)
        width=min(74,w-4); x=(w-width)//2; y=max(4,(h-9)//2)
        self.panel(y,x,9,width,title)
        message=tr('Esperando a que GSR cierre el archivo…') if stopping else tr('Pantalla mínima. Los paneles no se redibujan.') if app.started else tr('Validando pantalla, micrófono y recursos…')
        self.text(y+2,x+3,message,'panel',width-6)
        duration=tr("Parada automática: {seconds:g} s").format(seconds=app.seconds) if app.seconds else tr('Sin duración fija')
        self.text(y+3,x+3,duration,'muted',width-6)
        path=app.pending_output
        if path:
            self.text(y+4,x+3,Path(path).name,'accent',width-6)
            self.text(y+5,x+3,str(Path(path).parent),'muted',width-6)
        if not stopping: self.text(y+7,x+3,tr('[ x ] Detener y volver    [ Ctrl+C ] Detener'),'accent',width-6)
        self.shortcuts(h-2,[('q',tr('Detener y salir'))] if not stopping else [('',tr('Espera al cierre antes de cerrar la terminal'))])
