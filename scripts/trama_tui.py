#!/usr/bin/env python3
"""Trama: TUI local para perfiles del compositor GSR, sin previsualización."""
import argparse
import copy
import curses
from trama_i18n import tr, read_preference, select_language, save_preference, preference
import locale
from pathlib import Path
import queue
import re
import signal
import sys
import threading
import time
import textwrap

import compositor as backend
from compositor_devices import Devices
from compositor_profile import resolved
from trama_model import Model, CORNERS, browser_entries, initial_path, remember
from trama_view import View, FOCUS, clipped


class Terminate(BaseException):
    """External termination must unwind through curses.wrapper, not a dialog."""


class App:
    def __init__(self, screen, model, devices):
        self.screen, self.model, self.devices = screen, model, devices
        self.events = queue.Queue()
        self.worker = None
        self.discovery = None
        self.stop_event = threading.Event()
        self.active = False
        self.started = None
        self.seconds = None
        self.pending_output = None
        self.status = tr("Listo. r Grabar | t Prueba de 30 s")
        self.quit_after = False
        self.pending_wizard = model.is_new
        self.discovered = False
        self.device_errors = {}
        self.alive = True
        self.focus = "overview"
        self.row = 0
        self.view = View(screen,self.put)

    def put(self, y, x, value, attr=0, width=None):
        h,w = self.screen.getmaxyx()
        if 0<=y<h and 0<=x<w-1:
            columns=min(w-x-1,width) if width is not None else w-x-1
            value=clipped(value,max(0,columns))
            try:
                self.screen.addstr(y,x,value,attr)
            except curses.error:
                pass  # Resize or a terminal with different glyph widths.

    def key(self):
        try:
            return self.screen.get_wch()
        except curses.error:
            return None

    def frame(self, title, footer):
        self.screen.erase()
        self.put(0,1,"TRAMA / "+title,self.view.style("title"))
        _,width=self.screen.getmaxyx()
        self.put(1,1,"─"*(width-3),self.view.style("border"))
        h,_ = self.screen.getmaxyx()
        self.put(h-2,1,footer,self.view.style("muted"))

    def menu(self, title, items, selected=0, notes=(), footer=None):
        if not items:
            raise ValueError(tr("No hay opciones. u actualiza los dispositivos desde el inicio."))
        selected = min(selected,len(items)-1)
        while True:
            self.frame(title,footer or tr("↑↓ elegir  Enter aceptar  Esc volver"))
            h,_ = self.screen.getmaxyx()
            for i,note in enumerate(notes):
                self.put(2+i,2,note)
            start = 3+len(notes)
            rows = max(1,h-start-4)
            offset = max(0,min(selected-rows+1,len(items)-rows))
            for row,(_,label) in enumerate(items[offset:offset+rows],start):
                index = offset+row-start
                self.put(row,2,("› " if index==selected else "  ")+label,
                         self.view.style("selected") if index==selected else self.view.style("panel"))
            self.screen.refresh()
            key = self.key()
            if key in (curses.KEY_UP,'k'): selected=max(0,selected-1)
            elif key in (curses.KEY_DOWN,'j'): selected=min(len(items)-1,selected+1)
            elif key==curses.KEY_PPAGE: selected=max(0,selected-rows)
            elif key==curses.KEY_NPAGE: selected=min(len(items)-1,selected+rows)
            elif key==curses.KEY_HOME: selected=0
            elif key==curses.KEY_END: selected=len(items)-1
            elif key in ('\n','\r',curses.KEY_ENTER): return items[selected][0]
            elif key=='\x1b': return None

    def text(self, title, initial, validator=None, hint=""):
        value, cursor = str(initial),len(str(initial))
        error = ""
        try:
            curses.curs_set(1)
            while True:
                self.frame(title,tr("Enter aplicar  Esc cancelar  Ctrl+U borrar  ←→ cursor"))
                _,width=self.screen.getmaxyx()
                view=max(0,cursor-max(1,width-7))
                self.view.panel(2,1,3,width-2,tr("VALOR"),True)
                self.put(3,3,value[view:],self.view.style("panel"),width-6)
                self.put(5,2,hint)
                self.put(7,2,error,self.view.style("error"))
                try: self.screen.move(3,min(width-3,3+cursor-view))
                except curses.error: pass
                self.screen.refresh()
                key=self.key()
                if key=='\x1b': return None
                if key in ('\n','\r',curses.KEY_ENTER):
                    try:
                        return validator(value) if validator else value
                    except (ValueError,OSError) as exc:
                        error=str(exc)
                elif key in (curses.KEY_BACKSPACE,'\x7f','\b') and cursor:
                    value=value[:cursor-1]+value[cursor:]; cursor-=1
                elif key==curses.KEY_DC:
                    value=value[:cursor]+value[cursor+1:]
                elif key==curses.KEY_LEFT: cursor=max(0,cursor-1)
                elif key==curses.KEY_RIGHT: cursor=min(len(value),cursor+1)
                elif key in (curses.KEY_HOME,'\x01'): cursor=0
                elif key in (curses.KEY_END,'\x05'): cursor=len(value)
                elif key=='\x15': value,cursor="",0
                elif isinstance(key,str) and key.isprintable() and len(value)<8192:
                    value=value[:cursor]+key+value[cursor:]; cursor+=len(key)
        finally:
            curses.curs_set(0)

    def browse(self, title, initial, suffixes=None, directories=False):
        path=Path(initial).expanduser()
        selected_path=path
        folder=path if path.is_dir() else path.parent
        while not folder.is_dir() and folder!=folder.parent:
            folder=folder.parent
        selected=0
        error=""
        while True:
            try:
                entries=[folder.parent]+browser_entries(folder,suffixes,directories)
                if selected_path in entries:
                    selected=entries.index(selected_path); selected_path=None
                selected=min(selected,len(entries)-1)
            except OSError as exc:
                error=str(exc); entries=[folder.parent]; selected=0
            self.frame(title,tr("↑↓ elegir  Enter abrir/elegir  p Escribir ruta  Esc volver"))
            h,_=self.screen.getmaxyx()
            self.put(2,2,folder)
            if directories: self.put(3,2,tr("Espacio: usar esta carpeta. p: escribir también una carpeta nueva."))
            rows=max(1,h-9)
            offset=max(0,selected-rows+1)
            for row,path in enumerate(entries[offset:offset+rows],5):
                index=offset+row-5
                label="../" if index==0 else path.name+("/" if path.is_dir() else "")
                self.put(row,2,("› " if index==selected else "  ")+label,
                         self.view.style("selected") if index==selected else self.view.style("panel"))
            self.put(h-3,2,error,curses.A_BOLD)
            self.screen.refresh()
            key=self.key()
            if key=='\x1b': return None
            if key in (curses.KEY_UP,'k'): selected=max(0,selected-1)
            elif key in (curses.KEY_DOWN,'j'): selected=min(len(entries)-1,selected+1)
            elif key==curses.KEY_PPAGE: selected=max(0,selected-rows)
            elif key==curses.KEY_NPAGE: selected=min(len(entries)-1,selected+rows)
            elif key==' ' and directories: return folder
            elif key=='p':
                def check(value):
                    if not value: raise ValueError(tr("Ruta obligatoria"))
                    result=resolved(value,folder)
                    if directories:
                        if result.exists() and not result.is_dir(): raise ValueError(tr("No es una carpeta"))
                    elif not result.is_file(): raise ValueError(tr("No existe un archivo regular"))
                    return result
                chosen=self.text(tr("Ruta (relativa a la carpeta mostrada)"),str(folder)+"/",check)
                if chosen is not None: return chosen
            elif key in ('\n','\r',curses.KEY_ENTER):
                path=entries[selected]
                if path.is_dir(): folder=path; selected=0; error=""
                else: return path

    def attempt(self, field, action):
        before=copy.deepcopy(self.model.profile)
        selected=self.model.selected
        try:
            action()
            self.model.errors.pop(field,None)
            self.status=tr("Actualizado. s guarda el perfil.")
            return True
        except (ValueError,OSError,RuntimeError) as exc:
            self.model.profile=before
            self.model.selected=selected
            self.model.errors[field]=str(exc)
            self.status=str(exc)
            return False

    def remember_profile(self):
        try: remember(self.model.path,self.model.state_file)
        except OSError as exc: self.status=tr("Perfil disponible; no se pudo recordar la sesión: ")+str(exc)

    def save(self, save_as=False):
        path=self.model.path
        if save_as:
            def profile_path(value):
                if not value: raise ValueError(tr("Ruta obligatoria"))
                return Path(value).expanduser().resolve()
            entered=self.text(tr("Guardar perfil TOML como"),str(path),profile_path)
            if entered is None: return False
            path=entered
            if path.exists() and path!=self.model.path:
                if self.menu(tr("El perfil ya existe"),[(True,tr("Reemplazar este TOML")),(False,tr("Cancelar"))],1) is not True: return False
        try:
            self.model.save(path)
            self.remember_profile()
            self.status=tr("Perfil guardado: ")+str(path)
            self.model.errors.pop("profile",None)
            return True
        except (ValueError,OSError) as exc:
            self.model.errors["profile"]=str(exc); self.status=str(exc)
            return False

    def may_discard(self):
        if not self.model.dirty: return True
        choice=self.menu(tr("Cambios sin guardar"),[("save",tr("Guardar cambios")),("discard",tr("Descartar cambios")),("cancel",tr("Seguir editando"))],2)
        if choice=="save": return self.save()
        return choice=="discard"

    def choose_screen(self):
        items=[(name,f"{name} — {w}×{h}") for name,(w,h) in self.model.screens.items()]
        names=list(self.model.screens)
        current=self.model.profile["recording"]["screen"]
        chosen=self.menu(tr("Pantalla"),items,names.index(current) if current in names else 0)
        return chosen is not None and self.attempt("screen",lambda:self.model.set_recording("screen",chosen))

    def choose_mic(self):
        items=[("default_input",tr("Predeterminado del sistema")),("",tr("Sin micrófono (sin avatar)"))]
        items += [(name,f"{description} — {name}") for name,description in self.model.inputs.items()]
        current=self.model.profile["recording"]["microphone"]
        selected=next((i for i,(key,_) in enumerate(items) if key==current),0)
        chosen=self.menu(tr("Micrófono"),items,selected)
        return chosen is not None and self.attempt("microphone",lambda:self.model.set_recording("microphone",chosen))

    def add(self, avatar=False):
        if avatar and any(l["kind"]=="avatar" for l in self.model.profile["layers"]):
            self.status=tr("Ya hay un avatar: selecciónalo y pulsa e para editar sus campos.")
            return
        layer={"name":"Avatar" if avatar else tr("Gráfico"),"kind":"avatar" if avatar else "graphic"}
        for field,label in (("idle",tr("GIF de reposo")),("talking",tr("GIF de habla"))) if avatar else (("path",tr("PNG, JPG o GIF")),):
            initial=Path(layer["idle"]).parent if "idle" in layer else self.model.profile["_base"]
            chosen=self.browse(label,initial,{".gif"} if avatar else {".png",".jpg",".jpeg",".gif"})
            if chosen is None: return
            layer[field]=str(chosen)
        def apply():
            self.model.add_layer(layer)
            self.model.geometry(self.model.selected)
        if self.attempt("layer",apply): return self.place((3,300,20))
        return False

    def place(self,initial=None):
        if not self.model.profile["layers"]: return
        index=self.model.selected
        layer=self.model.profile["layers"][index]
        corner,size,margin=initial or self.model.placement_hint(index)
        while True:
            items=[(i,tr(CORNERS[i])) for i in range(4)]
            items += [("size",tr("Caja máxima: {size} px (conserva proporción)").format(size=size)),("margin",tr("Margen: {margin} px").format(margin=margin)),("manual",tr("X/Y manuales (avanzado)"))]
            error=self.model.errors.get("placement","")
            choice=self.menu(tr("Colocar ")+layer["name"],items,corner,
                (tr("Esquina + tamaño efectivo según la resolución del monitor."),error))
            if choice is None: return False
            if choice=="size":
                value=self.text(tr("Tamaño de la caja (px)"),size,lambda s:self.bounded_int(s,1,16384))
                if value is not None: size=value
            elif choice=="margin":
                value=self.text(tr("Margen (px)"),margin,lambda s:self.bounded_int(s,0,4096))
                if value is not None: margin=value
            elif choice=="manual":
                axis=self.menu(tr("Posición manual (avanzado)"),[("x",f"X: {layer['x']}"),("y",f"Y: {layer['y']}")])
                if axis is None: continue
                value=self.text(axis.upper()+tr(" en píxeles"),layer[axis],lambda s:self.bounded_int(s,-16384,16384))
                if value is not None:
                    return self.attempt(f"layer.{index}.{axis}",lambda:self.model.set_layer(index,axis,value))
            else:
                corner=choice
                if self.attempt("placement",lambda:self.model.place(index,corner,size,margin)):
                    self.status=tr("{corner}, caja {size}px, margen {margin}px. s guarda.").format(corner=tr(CORNERS[corner]),size=size,margin=margin)
                    return True

    @staticmethod
    def bounded_int(value, minimum, maximum):
        try: number=int(value)
        except ValueError: raise ValueError(tr("Escribe un entero de {minimum} a {maximum}").format(minimum=minimum,maximum=maximum)) from None
        if not minimum<=number<=maximum: raise ValueError(tr("Rango: {minimum}..{maximum}").format(minimum=minimum,maximum=maximum))
        return number

    def edit_layer(self,start_field=None):
        if not self.model.profile["layers"]: return
        index=self.model.selected
        selected=0
        while True:
            layer=self.model.profile["layers"][index]
            fields=[("name",tr("Nombre"))]
            fields += [("idle",tr("GIF reposo")),("talking",tr("GIF habla")),("threshold",tr("Umbral RMS")),("release_ms",tr("Espera (ms)"))] if layer["kind"]=="avatar" else [("path",tr("Archivo"))]
            fields += [("placement",tr("Esquina y tamaño")),("visible","Visible"),("width",tr("Ancho")),("height",tr("Alto")),("keep_aspect",tr("Conservar proporción")),("x",tr("X manual (avanzado)")),("y",tr("Y manual (avanzado)"))]
            if start_field:
                selected=next(i for i,(key,_) in enumerate(fields) if key==start_field); start_field=None
            items=[]
            for key,label in fields:
                value=layer.get(key,tr("automático")) if key!="placement" else tr("4 esquinas + caja")
                error=self.model.errors.get(f"layer.{index}.{key}","")
                items.append((key,f"{label}: {value}"+(f"  ! {error}" if error else "")))
            choice=self.menu(tr("Editar un campo / ")+layer["name"],items,selected)
            if choice is None: return
            selected=next(i for i,(key,_) in enumerate(fields) if key==choice)
            if choice=="placement": self.place(); continue
            if choice in ("visible","keep_aspect"):
                value=not layer[choice]
            elif choice in ("path","idle","talking"):
                value=self.browse(tr("Cambiar ")+choice,layer[choice],{".gif"} if choice!="path" else {".png",".jpg",".jpeg",".gif"})
                if value is None: continue
                value=str(value)
            else:
                def parse(text):
                    if choice in ("width","height") and text=="-": return "-"
                    if choice in ("x","y"): return self.bounded_int(text,-16384,16384)
                    if choice in ("width","height"): return self.bounded_int(text,1,16384)
                    if choice=="release_ms": return self.bounded_int(text,0,5000)
                    if choice=="threshold": return float(text)
                    return text
                value=self.text(dict(fields)[choice],layer.get(choice,"-"),parse,
                    tr("Solo cambia este campo. Ancho/alto: '-' deriva automáticamente."))
                if value is None: continue
                if choice in ("width","height") and value=="-": value=None
            def apply():
                self.model.set_layer(index,choice,value)
                if choice in ("path","idle","talking"): self.model.geometry(index)
            self.attempt(f"layer.{index}.{choice}",apply)

    def discover(self):
        if self.discovery and self.discovery.is_alive(): return
        def work():
            result={"screens":{},"inputs":{},"audio":{},"errors":{}}
            try: result["screens"]=self.devices.screens()
            except (ValueError,OSError) as exc: result["errors"]["screen"]=str(exc)
            try:
                result["audio"],result["inputs"]=self.devices.audio()
            except (ValueError,OSError) as exc: result["errors"]["microphone"]=str(exc)
            self.events.put(("devices",result))
        self.discovery=threading.Thread(target=work,name="trama-devices",daemon=True)
        self.discovery.start()
        self.status=tr("Consultando pantallas y micrófonos…")

    def start_recording(self,seconds=None):
        if self.active: return
        snapshot=copy.deepcopy(self.model.profile)
        self.stop_event=threading.Event()
        self.active=True; self.started=None; self.seconds=seconds
        self.pending_output=None
        self.status=tr("Validando pantalla, audio y recursos… x cancela")
        def work():
            try:
                prepared=backend.validate(snapshot,self.devices)
                self.events.put(("prepared",str(prepared["output"])))
                if self.stop_event.is_set():
                    self.events.put(("cancelled",None)); return
                result=backend.record(prepared,seconds,stop_event=self.stop_event,
                    on_started=lambda:self.events.put(("started",time.monotonic())),emit=lambda *args,**kw:None)
                self.events.put(("done",result))
            except Exception as exc:
                # The main thread is the ONLY curses owner. Failures are rendered
                # next to the corresponding field; worker never writes the tty.
                self.events.put(("error",str(exc)))
        self.worker=threading.Thread(target=work,name="trama-recording")
        self.worker.start()

    def poll(self):
        changed=False
        while True:
            try: event,data=self.events.get_nowait()
            except queue.Empty: break
            changed=True
            if event=="devices":
                self.model.screens,self.model.inputs,self.model.audio_devices=data["screens"],data["inputs"],data["audio"]
                self.device_errors=data["errors"]; self.discovered=True
                self.status=tr("Dispositivos actualizados.") if not data["errors"] else tr("Revisa pantalla/micrófono. u reintenta la consulta.")
            elif event=="prepared": self.pending_output=Path(data)
            elif event=="started":
                self.started=data; self.status=tr("GRABANDO — x o Ctrl+C detiene")
                self.model.last_video=self.pending_output; self.model.last_success=None
            elif event in ("done","error","cancelled"):
                self.active=False
                if self.worker: self.worker.join()
                if event=="done":
                    self.model.last_video=Path(data["output"]); self.model.last_success=True
                    self.model.errors.clear()
                    self.status=tr("Grabación guardada. o muestra el MKV.")
                elif event=="error":
                    if self.pending_output and self.pending_output.is_file():
                        self.model.last_video=self.pending_output; self.model.last_success=False
                    field="recording"
                    for name in ("screen","microphone","output","fps"):
                        if "recording."+name in data: field=name
                    if field=="output": field="folder" if "carpeta" in data.lower() else "name"
                    layer_error=re.search(r"layers\[(\d+)\]\.([a-z_]+)",data)
                    if layer_error:
                        index=int(layer_error[1])-1
                        self.model.selected=max(0,min(index,len(self.model.profile["layers"])-1))
                        field=f"layer.{index}.{layer_error[2]}"
                    elif "capa " in data or "layers[" in data: field="layer"
                    self.model.errors[field]=data; self.status=data
                else: self.status=tr("Grabación cancelada antes del inicio.")

        return changed

    def wizard(self):
        if not self.choose_screen() or not self.choose_mic(): return
        if not self.model.profile["recording"]["microphone"]:
            self.model.errors["microphone"]=tr("El avatar necesita una entrada de micrófono. m permite elegirla.")
            return
        avatar=next((i for i,l in enumerate(self.model.profile["layers"]) if l["kind"]=="avatar"),None)
        if avatar is None:
            if not self.add(True): return
        else:
            self.model.selected=avatar; self.place()
        action=self.menu(tr("Primera prueba"),[("test",tr("Guardar perfil y grabar 30 segundos")),("save",tr("Guardar y seguir editando")),("back",tr("Seguir editando sin guardar"))],0,
            (tr("La captura usa el monitor completo, audio del sistema y micrófono elegidos."),))
        if action in ("test","save") and self.save() and action=="test": self.start_recording(30)

    def home(self):
        self.view.home(self)

    def move_focus(self,delta):
        self.focus=FOCUS[(FOCUS.index(self.focus)+delta)%len(FOCUS)]
        self.row=0

    def move_row(self,delta):
        if self.focus=="layers":
            self.model.selected=max(0,min(max(0,len(self.model.profile["layers"])-1),self.model.selected+delta))
        else:
            count=3 if self.focus=="overview" else 2
            self.row=(self.row+delta)%count

    def activate(self):
        key={"capture":("p","f"),"audio":("m","g"),"output":("d","n"),
             "overview":("r","t","s")}.get(self.focus)
        if key is None: self.edit_layer()
        else: self.dispatch(key[self.row])

    def more_actions(self):
        groups={
            "capture":[("p",tr("Elegir pantalla")),("f",tr("Cambiar FPS")),("u",tr("Actualizar dispositivos"))],
            "audio":[("m",tr("Elegir micrófono")),("g",tr("Alternar audio del juego/sistema"))],
            "output":[("d",tr("Carpeta de grabaciones")),("n",tr("Nombre del video")),("o",tr("Ver último MKV"))],
            "overview":[("r",tr("Grabar")),("t",tr("Prueba de 30 segundos")),("s",tr("Guardar perfil")),
                       ("S",tr("Guardar como")),("l",tr("Cargar perfil")),("w",tr("Primeros pasos")),("!",tr("Diagnóstico")),("L",tr("Idioma / Language"))],
            "layers":[("e",tr("Editar un campo")),("c",tr("Esquina y tamaño")),("h",tr("Ocultar / mostrar")),
                      ("D",tr("Quitar capa")),("[",tr("Mover hacia el fondo")),("]",tr("Mover hacia delante")),
                      ("a",tr("Agregar gráfico")),("v",tr("Agregar avatar"))],
        }
        choice=self.menu(tr("Acciones / ")+self.focus,groups[self.focus])
        if choice is not None: self.dispatch(choice)

    def choose_language(self):
        choices=[('auto',tr('Automático (sistema)')),('es','Español'),('en','English')]
        selected=next(i for i,(key,_) in enumerate(choices) if key==preference())
        chosen=self.menu(tr('Idioma / Language'),choices,selected)
        if chosen is not None:
            save_preference(chosen)
            select_language(chosen)
            self.status=tr('Idioma guardado.')

    def help(self):
        self.details(tr("Ayuda"),[
            tr("NAVEGACIÓN"),
            tr("Tab           Siguiente sección"),
            tr("Shift+Tab     Sección anterior"),
            tr("↑ / ↓         Elegir campo, capa o acción"),
            tr("Enter         Editar o ejecutar la selección"),
            tr("Espacio       Acciones de la sección"),
            tr("? / F1        Abrir esta ayuda"),
            tr("L             Idioma / Language"),
            tr("q / Esc       Salir (avisa si hay cambios)"),
            "",
            tr("PERFIL Y GRABACIÓN"),
            tr("r             Grabar hasta detener manualmente"),
            tr("t             Grabar una prueba de 30 segundos"),
            tr("s             Guardar perfil"),
            tr("S             Guardar perfil como…"),
            tr("l             Cargar perfil"),
            tr("o             Ver la ruta completa del último MKV"),
            tr("w             Abrir primeros pasos"),
            tr("!             Ver diagnóstico"),
            "",
            tr("CAPTURA, AUDIO Y SALIDA"),
            tr("p             Elegir pantalla"),
            tr("f             Cambiar FPS"),
            tr("m             Elegir micrófono"),
            tr("g             Activar/desactivar audio del sistema"),
            tr("d             Elegir carpeta de grabaciones"),
            tr("n             Nombre del video; admite {timestamp}"),
            tr("u             Actualizar dispositivos"),
            "",
            tr("CAPAS"),
            tr("a             Agregar gráfico PNG, JPG o GIF"),
            tr("v             Agregar avatar con reposo y habla"),
            tr("e             Editar un campo de la capa seleccionada"),
            tr("c             Elegir esquina y tamaño"),
            tr("h             Ocultar/mostrar capa"),
            tr("Supr / D      Quitar capa sin borrar sus archivos"),
            tr("[             Mover capa hacia el fondo"),
            tr("]             Mover capa hacia delante"),
            "",
            tr("DURANTE LA GRABACIÓN"),
            tr("x / Ctrl+C    Detener y volver a Trama"),
            tr("q / Esc       Detener y salir"),
            tr("La vista permanece estática hasta cambiar de estado."),
            "",
            tr("EDICIÓN Y ARCHIVOS"),
            tr("Esc           Cancelar y volver"),
            tr("Ctrl+U        Borrar el campo de texto"),
            tr("← / →         Mover el cursor en un campo de texto"),
            tr("Enter         Aplicar valor o abrir/elegir archivo"),
            tr("p             Escribir ruta en el selector de archivos"),
            tr("Espacio       Usar carpeta actual en selector de carpetas"),
        ])

    def details(self,title,lines):
        _,width=self.screen.getmaxyx()
        wrapped=[]
        for line in lines:
            wrapped.extend(textwrap.wrap(str(line),width=max(10,width-8),replace_whitespace=False) or [""])
        return self.menu(title,[(None,line) for line in wrapped],footer=tr("↑↓ desplazar  Enter / Esc volver"))

    def result_view(self):
        if self.model.last_video is None:
            self.status=tr("Aún no hay una grabación en esta sesión."); return
        path=self.model.last_video
        label=tr("Guardada") if self.model.last_success else tr("Parcial o pendiente de comprobación")
        self.details(tr("Último MKV"),(label,str(path),tr("Carpeta: ")+str(path.parent),"Log: "+str(path)+".gsr.log",tr("Informe: ")+str(path)+".report.json"))

    def dispatch(self,key):
        if self.active:
            if key in ('x','\x03'):
                self.stop_event.set(); self.status=tr("Cerrando la grabación… espera al MKV.")
            elif key in ('q','\x1b'):
                self.stop_event.set(); self.quit_after=True; self.status=tr("Cerrando grabación antes de salir…")
            return
        shortcuts={"p":("capture",0),"f":("capture",1),"m":("audio",0),"g":("audio",1),
                   "d":("output",0),"n":("output",1),"r":("overview",0),"t":("overview",1),"s":("overview",2)}
        if key in shortcuts: self.focus,self.row=shortcuts[key]
        if key in ('a','v','e','c','h','D','[',']',curses.KEY_DC): self.focus="layers"
        if key in ('q','\x1b'):
            if self.may_discard(): self.alive=False
        elif key=='\t': self.move_focus(1)
        elif key==curses.KEY_BTAB: self.move_focus(-1)
        elif key in (curses.KEY_UP,'k'): self.move_row(-1)
        elif key in (curses.KEY_DOWN,'j'): self.move_row(1)
        elif key in (curses.KEY_LEFT,curses.KEY_RIGHT) and self.focus=="overview":
            self.move_row(-1 if key==curses.KEY_LEFT else 1)
        elif key in ('\n','\r',curses.KEY_ENTER): self.activate()
        elif key==' ': self.more_actions()
        elif key in ('?',curses.KEY_F1): self.help()
        elif key=='L': self.choose_language()
        elif key=='p': self.choose_screen()
        elif key=='m': self.choose_mic()
        elif key=='d':
            chosen=self.browse(tr("Carpeta de grabaciones"),self.model.output_folder,directories=True)
            if chosen is not None: self.attempt("folder",lambda:self.model.set_folder(chosen))
        elif key=='n':
            chosen=self.text(tr("Nombre del video — admite {timestamp}"),self.model.output_name,
                lambda s:self.checked_name(s),tr("Ejemplo: minecraft-{timestamp}.mkv. Sin carpetas."))
            if chosen is not None: self.attempt("name",lambda:self.model.set_name(chosen))
        elif key=='f':
            chosen=self.text("FPS",self.model.profile["recording"]["fps"],lambda s:self.bounded_int(s,1,120))
            if chosen is not None: self.attempt("fps",lambda:self.model.set_recording("fps",chosen))
        elif key=='g': self.attempt("audio",lambda:self.model.set_recording("game_audio",not self.model.profile["recording"]["game_audio"]))
        elif key=='a': self.add()
        elif key=='v': self.add(True)
        elif key=='e': self.edit_layer()
        elif key=='c': self.place()
        elif key=='h' and self.model.profile["layers"]:
            self.attempt("layer",lambda:self.model.set_layer(self.model.selected,"visible",not self.model.profile["layers"][self.model.selected]["visible"]))
        elif key in (curses.KEY_DC,'D') and self.model.profile["layers"]:
            name=self.model.profile["layers"][self.model.selected]["name"]
            if self.menu(tr("Quitar ")+name,[(False,tr("Cancelar")),(True,tr("Quitar capa (no borra el archivo)"))]) is True:
                self.attempt("layer",lambda:self.model.remove_layer(self.model.selected))
        elif key in ('[',']') and self.model.profile["layers"]:
            self.model.move_layer(self.model.selected,-1 if key=='[' else 1)
        elif key=='s': self.save()
        elif key=='S': self.save(True)
        elif key=='l':
            if not self.may_discard(): return
            chosen=self.browse(tr("Cargar perfil TOML"),self.model.path,{".toml"})
            if chosen is not None:
                self.model.load(chosen); self.remember_profile()
                self.pending_wizard=False; self.status=tr("Perfil cargado. r graba; e edita un solo campo.")
        elif key in ('r','t'): self.start_recording(30 if key=='t' else None)
        elif key=='o': self.result_view()
        elif key=='u': self.discover()
        elif key=='w': self.wizard()
        elif key=='!':
            notes=[f"{key}: {value}" for key,value in self.model.errors.items()]+[self.status]
            self.details(tr("Diagnóstico"),notes)

    def checked_name(self,value):
        before=copy.deepcopy(self.model.profile)
        try: self.model.set_name(value)
        finally: self.model.profile=before
        return value

    def run(self):
        self.screen.keypad(True); self.screen.timeout(250)
        self.view.setup()
        curses.curs_set(0)
        if hasattr(curses,"set_escdelay"): curses.set_escdelay(35)
        self.discover()
        if not self.model.is_new: self.remember_profile()
        repaint=True
        try:
            while self.alive:
                try:
                    if self.poll(): repaint=True
                    if self.quit_after and not self.active:
                        self.quit_after=False
                        if self.may_discard(): break
                        repaint=True
                    if self.pending_wizard and self.discovered:
                        self.pending_wizard=False
                        if self.model.screens: self.wizard()
                        repaint=True
                    if repaint:
                        self.home()
                        repaint=False
                    self.screen.timeout(1000 if self.active else 250)
                    key=self.key()
                    if key is not None:
                        repaint=True
                        try: self.dispatch(key)
                        except (ValueError,OSError,RuntimeError) as exc:
                            self.status=str(exc); self.model.errors["setting"]=str(exc)
                except KeyboardInterrupt:
                    repaint=True
                    if self.active: self.stop_event.set(); self.status=tr("Cerrando grabación…")
                    elif self.may_discard(): break
        finally:
            self.stop_event.set()
            if self.worker and self.worker.is_alive():
                self.worker.join()  # orderly GSR stop; wrapper restores tty next.


def main(argv=None):
    # Parse only the language first so --help and parser errors use it too.
    bootstrap=argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument('--lang')
    early,_=bootstrap.parse_known_args(argv)
    selected=early.lang if early.lang in ('auto','es','en') else read_preference()
    select_language(selected)
    parser=argparse.ArgumentParser(description=tr(__doc__))
    parser.add_argument('--lang',choices=('auto','es','en'),help=tr('Idioma de la interfaz (auto, es, en); solo esta ejecución'))
    parser.add_argument("profile",nargs="?",type=Path,help=tr("TOML; sin argumento recupera el último perfil o ./perfil.toml"))
    args=parser.parse_args(argv)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error(tr("La TUI necesita una terminal interactiva. Usa compositor.py record para grabar sin TUI."))
    try:
        try:
            locale.setlocale(locale.LC_ALL,"")
        except locale.Error:
            # An unavailable system locale must not prevent the English fallback.
            # Keep Python's initialized locale; do not change the user's environment.
            pass
        model=Model(initial_path(args.profile))
        devices=Devices()
        def terminate(signum,frame): raise Terminate
        previous=signal.signal(signal.SIGTERM,terminate)
        try: curses.wrapper(lambda screen:App(screen,model,devices).run())
        finally: signal.signal(signal.SIGTERM,previous)
        return 0
    except (ValueError,OSError,curses.error) as exc:
        print(f"Trama: {exc}",file=sys.stderr); return 2
    except KeyboardInterrupt:
        return 130
    except Terminate:
        return 143


if __name__=="__main__":
    sys.exit(main())
