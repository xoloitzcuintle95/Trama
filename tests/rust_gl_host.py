"""C ABI via ctypes, offscreen GLES3; no KMS or hardware performance claims."""
import argparse
import ctypes as C
import os
import time
from pathlib import Path
import tempfile
from PIL import Image, ImageChops

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--plugin", default="build/overlay-rust.so")
parser.add_argument("--test-hooks", action="store_true")
args = parser.parse_args()
for key in ("GSR_RUST_SCENE", "GSR_OVERLAY_HEIGHT", "GSR_OVERLAY_KEEP_ASPECT", "GSR_OVERLAY_VISIBLE"):
    os.environ.pop(key, None)
os.environ["EGL_PLATFORM"] = "surfaceless"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
egl, gl = C.CDLL("libEGL.so.1"), C.CDLL("libGL.so.1")
P, I, U = C.c_void_p, C.c_int, C.c_uint


def fn(lib, name, result, *types):
    function = getattr(lib, name)
    function.restype, function.argtypes = result, list(types)
    return function


def attrs(*values):
    return (I * len(values))(*values)


display = fn(egl, "eglGetDisplay", P, P)(None)
assert fn(egl, "eglInitialize", I, P, P, P)(display, None, None)
assert fn(egl, "eglBindAPI", I, U)(0x30A0)
config, count = P(), I()
assert fn(egl, "eglChooseConfig", I, P, P, P, I, P)(display,
    attrs(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038),
    C.byref(config), 1, C.byref(count)) and count.value
W, H = 96, 80
surface = fn(egl, "eglCreatePbufferSurface", P, P, P, P)(display, config, attrs(0x3057, W, 0x3056, H, 0x3038))
context = fn(egl, "eglCreateContext", P, P, P, P, P)(display, config, None, attrs(0x3098, 3, 0x3038))
make_current = fn(egl, "eglMakeCurrent", I, P, P, P, P)
assert surface and context and make_current(display, surface, surface, context)
print("Renderer:", fn(gl, "glGetString", C.c_char_p, U)(0x1F01).decode())


class Init(C.Structure):
    _fields_ = [("width", U), ("height", U), ("fps", U), ("depth", I), ("api", I)]


class DrawParams(C.Structure):
    _fields_ = [("width", U), ("height", U)]


Draw = C.CFUNCTYPE(None, C.POINTER(DrawParams), P)
Damage = C.CFUNCTYPE(C.c_bool, P)
Clear = C.CFUNCTYPE(None, P)


class Return(C.Structure):
    _fields_ = [("name", C.c_char_p), ("version", U), ("userdata", P),
                ("draw", Draw), ("damage", Damage), ("clear", Clear)]


plugin = C.CDLL(str(Path(args.plugin).resolve()))
init = fn(plugin, "gsr_plugin_init", C.c_bool, C.POINTER(Init), C.POINTER(Return))
deinit = fn(plugin, "gsr_plugin_deinit", None, P)
get = fn(gl, "glGetIntegerv", None, U, P)
enabled = fn(gl, "glIsEnabled", C.c_bool, U)
enable, disable = fn(gl, "glEnable", None, U), fn(gl, "glDisable", None, U)
active = fn(gl, "glActiveTexture", None, U)
bind_texture = fn(gl, "glBindTexture", None, U, U)
bind_buffer = fn(gl, "glBindBuffer", None, U, U)
bind_vao = fn(gl, "glBindVertexArray", None, U)
bind_sampler = fn(gl, "glBindSampler", None, U, U)
pixel_store = fn(gl, "glPixelStorei", None, U, I)
mask = fn(gl, "glColorMask", None, C.c_bool, C.c_bool, C.c_bool, C.c_bool)
blend = fn(gl, "glBlendFuncSeparate", None, U, U, U, U)
equation = fn(gl, "glBlendEquationSeparate", None, U, U)
error = fn(gl, "glGetError", U)
clear_color = fn(gl, "glClearColor", None, C.c_float, C.c_float, C.c_float, C.c_float)
clear = fn(gl, "glClear", None, U)
scissor = fn(gl, "glScissor", None, I, I, I, I)
fn(gl, "glViewport", None, I, I, I, I)(0, 0, W, H)
CAPS = [0x0BE2, 0x0C11, 0x0B71, 0x0B90, 0x0B44, 0x8C89]


def integer(key):
    value = I()
    get(key, C.byref(value))
    return value.value


def state():
    old = integer(0x84E0)
    active(0x84C0)
    unit0 = [integer(0x8069), integer(0x8919)]
    active(old)
    return [integer(k) for k in [0x8B8D, 0x85B5, 0x8894, 0x88EF, 0x84E0,
        0x8069, 0x0CF5, 0x0CF2, 0x0CF3, 0x0CF4, 0x80C9, 0x80C8, 0x80CB, 0x80CA,
        0x8009, 0x883D]] + unit0 + [enabled(k) for k in CAPS] + list(color_mask())


def color_mask():
    value = (C.c_ubyte * 4)()
    fn(gl, "glGetBooleanv", None, U, P)(0x0C23, value)
    return value


def names(kind):
    name = U()
    fn(gl, f"glGen{kind}", None, I, P)(1, C.byref(name))
    return name.value


host_texture, host_sampler = names("Textures"), names("Samplers")
host_buffer, host_pbo, host_vao = names("Buffers"), names("Buffers"), names("VertexArrays")
bind_buffer(0x88EC, host_pbo)
fn(gl, "glBufferData", None, U, C.c_ssize_t, P, U)(0x88EC, 4096, None, 0x88E4)
bind_buffer(0x88EC, 0)


def hostile_state():
    bind_vao(host_vao)
    bind_buffer(0x8892, host_buffer)
    bind_buffer(0x88EC, host_pbo)
    active(0x84C0)
    bind_texture(0x0DE1, host_texture)
    bind_sampler(0, host_sampler)
    active(0x84C3)
    bind_texture(0x0DE1, host_texture)
    for key, value in [(0x0CF5, 8), (0x0CF2, 31), (0x0CF3, 2), (0x0CF4, 1)]:
        pixel_store(key, value)
    for cap in CAPS:
        enable(cap)
    mask(False, True, False, True)
    blend(1, 0, 0x0302, 0x0303)
    equation(0x800A, 0x800B)  # subtract/reverse-subtract, must be restored


def background(index):
    for cap in CAPS:
        disable(cap)
    mask(True, True, True, True)
    color = (64, 128, 192, 255) if not index else (192, 64, 255, 255)
    clear_color(*(v / 255 for v in color))
    clear(0x4000)
    image = Image.new("RGBA", (W, H), color)
    # Asymmetric marker also detects any vertical flip or erased desktop.
    enable(0x0C11)
    scissor(0, 0, W, 3)
    clear_color(1, 0, 0, 1)
    clear(0x4000)
    image.paste((255, 0, 0, 255), (0, 0, W, 3))
    disable(0x0C11)
    return image


def read_image():
    data = (C.c_ubyte * (W * H * 4))()
    fn(gl, "glReadPixels", None, I, I, I, I, U, U, P)(0, 0, W, H, 0x1908, 0x1401, data)
    assert error() == 0
    return Image.frombytes("RGBA", (W, H), bytes(data))


def gl_names():
    # In this controlled fresh context names allocated so far are small. Track
    # actual liveness before/after init/deinit, including failed init/unwind.
    return {kind: {i for i in range(1, 128) if fn(gl, f"glIs{kind}", C.c_bool, U)(i)}
            for kind in ("Program", "Shader", "Texture", "Buffer", "VertexArray")}


with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    fixture = Image.new("RGBA", (12, 10), (240, 30, 100, 0))
    for y in range(2, 9):
        for x in range(1, 10):
            fixture.putpixel((x, y), (40 + x * 12, 80, y * 15, 128 if x < 5 else 255))
    os.environ.update(GSR_OVERLAY_X="5", GSR_OVERLAY_Y="7", GSR_OVERLAY_WIDTH="12")
    path = folder / "static.png"
    fixture.save(path)
    os.environ["GSR_RUST_IMAGE"] = str(path)
    os.environ.pop("GSR_RUST_TEST_PANIC", None)
    hostile_state()
    original = state()
    live = gl_names()
    ret = Return()
    assert init(C.byref(Init(W, H, 30, 0, 0)), C.byref(ret))
    assert state() == original, "init altered GL state"
    assert ret.name == b"rust-media-overlay" and ret.version == 4 and ret.userdata
    assert ret.damage(ret.userdata)
    ret.clear(ret.userdata)
    assert ret.damage(ret.userdata)  # draw, not pre-draw clear_damage, acknowledges an update.
    path.unlink()  # draw must work with no source file left on disk.
    for index in range(2):
        expected = background(index)
        expected.alpha_composite(fixture, (5, 7))
        hostile_state()
        before = state()
        ret.draw(C.byref(DrawParams(W, H)), ret.userdata)
        assert not ret.damage(ret.userdata)
        assert state() == before, "draw leaked GL state"
        actual = read_image()
        diff = ImageChops.difference(actual, expected)
        assert all(high <= 1 for low, high in diff.getextrema()), diff.getextrema()
    deinit(ret.userdata)
    assert gl_names() == live, "GL resource leaked during normal deinit"
    assert state() == original
    print("OK PNG: composición/alfa/orientación, estado GL adverso, draw sin archivo y liberación GL")

    # Failure must not publish userdata or change host state/GL live objects.
    path.write_bytes(b"invalid png")
    cases = [Init(W, H, 30, 1, 0), Init(W, H, 30, 0, 99), Init(0, H, 30, 0, 0), Init(W, H, 30, 0, 0)]
    for params in cases:
        ret = Return()
        assert not init(C.byref(params), C.byref(ret))
        assert not ret.userdata and not ret.version and gl_names() == live
        assert state() == original
    assert not init(None, C.byref(Return()))
    assert not init(C.byref(Init(W, H, 30, 0, 0)), None)
    deinit(None)
    print("OK init inválido: HDR, API, dimensiones, PNG malformado y NULL")

    # APNG is deliberately rejected instead of silently presenting its first frame.
    fixture.save(path, save_all=True, append_images=[Image.new("RGBA", fixture.size, "red")], duration=100)
    ret = Return()
    assert not init(C.byref(Init(W, H, 30, 0, 0)), C.byref(ret))
    assert gl_names() == live and state() == original
    print("OK rechazo APNG")

    animated = []
    for color in ((220, 30, 10, 255), (20, 210, 80, 255), (30, 50, 240, 255)):
        frame = Image.new("RGBA", (12, 10))
        for yy in range(2, 8):
            for xx in range(1, 10):
                frame.putpixel((xx, yy), color)
        animated.append(frame)
    gif_path = folder / "animated.gif"
    animated[0].save(gif_path, save_all=True, append_images=animated[1:],
                     duration=[100, 2000, 100], loop=0, disposal=[2, 3, 1])
    with Image.open(gif_path) as gif:
        expected_frames = []
        for idx in range(gif.n_frames):
            gif.seek(idx)
            expected_frames.append(gif.convert("RGBA"))
    os.environ["GSR_RUST_IMAGE"] = str(gif_path)
    ret = Return()
    assert init(C.byref(Init(W, H, 30, 0, 0)), C.byref(ret))
    gif_path.unlink()  # all subsequent frame changes must come from the cache.
    last = None
    if args.test_hooks:
        set_time = fn(plugin, "gsr_test_set_time", None, P, C.c_uint64)
        times = [0, 99, 100, 2099, 2100, 2199, 2200, 2201, 220100, 600000]
    else:
        times = [0, 130]
    for idx, ms in enumerate(times):
        if args.test_hooks:
            set_time(ret.userdata, ms)
        elif idx:
            time.sleep(0.13)
        phase = ms % 2200
        frame_idx = 0 if phase < 100 else 1 if phase < 2100 else 2
        assert ret.damage(ret.userdata) == (last is None or frame_idx != last)
        ret.clear(ret.userdata)
        assert ret.damage(ret.userdata) == (last is None or frame_idx != last)
        expected = background(idx % 2)
        expected.alpha_composite(expected_frames[frame_idx], (5, 7))
        hostile_state()
        before = state()
        ret.draw(C.byref(DrawParams(W, H)), ret.userdata)
        assert state() == before
        diff = ImageChops.difference(read_image(), expected)
        assert all(high <= 1 for low, high in diff.getextrema()), (ms, diff.getextrema())
        assert not ret.damage(ret.userdata)
        last = frame_idx
    if args.test_hooks:
        names_before = gl_names()
        # Virtual timeline only: not a real 10-minute recording or GPU benchmark.
        for ms in range(0, 600001, 100):
            set_time(ret.userdata, ms)
            ret.draw(C.byref(DrawParams(W, H)), ret.userdata)
        assert gl_names() == names_before, "animation allocated GL objects per frame"
    deinit(ret.userdata)
    assert gl_names() == live and state() == original
    print("OK GIF GL: reloj, cambios de frame, alfa/disposal, caché sin archivo, damage y liberación")

    # Same element configuration for either source; all scaling/clipping references
    # are independent Pillow compositions with premultiplied bilinear resampling.
    config_keys = ("GSR_OVERLAY_X", "GSR_OVERLAY_Y", "GSR_OVERLAY_WIDTH", "GSR_OVERLAY_HEIGHT",
                   "GSR_OVERLAY_KEEP_ASPECT", "GSR_OVERLAY_VISIBLE")
    variants = [
        ({"GSR_OVERLAY_WIDTH":"24"}, (24,20), (5,7), True),
        ({"GSR_OVERLAY_HEIGHT":"20"}, (24,20), (5,7), True),
        ({"GSR_OVERLAY_WIDTH":"24", "GSR_OVERLAY_HEIGHT":"30"}, (24,20), (5,7), True),
        ({"GSR_OVERLAY_WIDTH":"24", "GSR_OVERLAY_HEIGHT":"10", "GSR_OVERLAY_KEEP_ASPECT":"false"}, (24,10), (5,7), True),
        ({"GSR_OVERLAY_X":"-3", "GSR_OVERLAY_Y":"-2", "GSR_OVERLAY_WIDTH":"12"}, (12,10), (-3,-2), True),
        ({"GSR_OVERLAY_X":"110", "GSR_OVERLAY_WIDTH":"12"}, (12,10), (110,7), True),
        ({"GSR_OVERLAY_WIDTH":"12", "GSR_OVERLAY_VISIBLE":"false"}, (12,10), (5,7), False),
    ]
    for kind in ("png", "gif"):
        for overrides, size, dest, visible in variants:
            for key in config_keys:
                os.environ.pop(key, None)
            os.environ.update({"GSR_OVERLAY_X":"5", "GSR_OVERLAY_Y":"7", **overrides})
            configured_path = folder / ("configured." + kind)
            if kind == "png":
                fixture.save(configured_path)
            else:
                animated[0].save(configured_path, save_all=True, append_images=animated[1:],
                                 duration=[100,2000,100], loop=0, disposal=[2,3,1])
            os.environ["GSR_RUST_IMAGE"] = str(configured_path)
            hostile_state()
            before = state()
            configured = Return()
            assert init(C.byref(Init(W,H,30,0,0)), C.byref(configured)), (kind, overrides)
            assert gl_names() != live, "hidden element must retain its resources too"
            assert state() == before
            configured_path.unlink()
            moments = (0,100,2100,600000) if args.test_hooks else (0,)
            for step, ms in enumerate(moments):
                if args.test_hooks:
                    set_time(configured.userdata, ms)
                phase = ms % 2200
                idx = 0 if phase < 100 else 1 if phase < 2100 else 2
                source = fixture if kind == "png" else expected_frames[idx]
                expected = background(step % 2)
                if visible:
                    layer = Image.new("RGBA", (W,H))
                    layer.paste(source.resize(size, Image.Resampling.BILINEAR), dest)
                    expected = Image.alpha_composite(expected,layer)
                hostile_state()
                before = state()
                if not visible:
                    assert not configured.damage(configured.userdata)
                configured.draw(C.byref(DrawParams(W,H)), configured.userdata)
                assert state() == before
                diff = ImageChops.difference(read_image(),expected)
                assert all(high <= 2 for low,high in diff.getextrema()), (kind,overrides,ms,diff.getextrema())
            deinit(configured.userdata)
            assert gl_names() == live and state() == before
    print("OK geometría PNG/GIF: ancho, alto, caja proporcional, deformación explícita, recorte y oculto retenido")

    # Bad configuration must fail before publishing userdata or touching GL.
    for key in config_keys:
        os.environ.pop(key,None)
    fixture.save(path)
    os.environ["GSR_RUST_IMAGE"] = str(path)
    for values in [{"GSR_OVERLAY_HEIGHT":"0"}, {"GSR_OVERLAY_WIDTH":"-2"},
                   {"GSR_OVERLAY_VISIBLE":"yes"}, {"GSR_OVERLAY_KEEP_ASPECT":"false"}]:
        os.environ.update(values)
        ret = Return()
        before = state()
        assert not init(C.byref(Init(W,H,30,0,0)),C.byref(ret))
        assert not ret.userdata and state() == before and gl_names() == live
        for key in values:
            os.environ.pop(key,None)
    os.environ.update(GSR_OVERLAY_X="5",GSR_OVERLAY_Y="7",GSR_OVERLAY_WIDTH="12")
    print("OK configuración inválida sin recursos ni estado GL alterados")

    if args.test_hooks:
        for location in ("init", "draw", "damage", "clear", "deinit"):
            fixture.save(path)
            os.environ["GSR_RUST_TEST_PANIC"] = location
            ret = Return()
            good = init(C.byref(Init(W, H, 30, 0, 0)), C.byref(ret))
            if location == "init":
                assert not good and not ret.userdata
            else:
                assert good
                if location == "draw":
                    ret.draw(C.byref(DrawParams(W, H)), ret.userdata)
                    assert not ret.damage(ret.userdata)
                elif location == "damage":
                    assert not ret.damage(ret.userdata)
                elif location == "clear":
                    ret.clear(ret.userdata)
                    assert not ret.damage(ret.userdata)
                deinit(ret.userdata)
            assert gl_names() == live and state() == original, location
        print("OK cinco callbacks: panics contenidos, limpieza GL, proceso C sigue vivo")

# Ordered multi-source scene, including JPEG, hidden retention and real detector
# worker driven by a synthetic parec executable. No sound device is accessed.
import json
with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    first = folder/"bottom.jpg"
    second = folder/"top.png"
    hidden = folder/"hidden.png"
    Image.new("RGB",(12,10),(180,40,20)).save(first)
    Image.new("RGBA",(12,10),(20,180,80,128)).save(second)
    Image.new("RGBA",(12,10),(255,255,255,255)).save(hidden)
    sources = [Image.open(first).convert("RGBA"),Image.open(second).copy()]
    entries = [{"name":"JPG","path":str(first),"x":5,"y":7,"width":12},
               {"name":"PNG","path":str(second),"x":9,"y":10,"width":12},
               {"name":"hidden","path":str(hidden),"x":5,"y":7,"width":12,"visible":False}]
    scene_path = folder/"scene.json"
    os.environ["GSR_RUST_SCENE"] = str(scene_path)
    os.environ.pop("GSR_RUST_TEST_PANIC",None)
    for order in ([0,1],[1,0]):
        scene_path.write_text(json.dumps({"layers":[entries[i] for i in order]+[entries[2]]}))
        hostile_state()
        before=state()
        ret=Return()
        assert init(C.byref(Init(W,H,30,0,0)),C.byref(ret))
        expected=background(0)
        for index in order:
            expected.alpha_composite(sources[index],(entries[index]["x"],entries[index]["y"]))
        hostile_state()
        ret.draw(C.byref(DrawParams(W,H)),ret.userdata)
        assert state()==before
        diff=ImageChops.difference(read_image(),expected)
        assert all(high<=3 for low,high in diff.getextrema()), diff.getextrema()
        deinit(ret.userdata)
        assert gl_names()==live
    print("OK escena: orden PNG/JPG, alfa, oculto, estado GL y cierre")
    # A scene that fails after successfully loading the first layer must clean up.
    scene_path.write_text(json.dumps({"layers":[entries[0],dict(entries[1],path=str(folder/"missing.gif"))]}))
    ret=Return()
    assert not init(C.byref(Init(W,H,30,0,0)),C.byref(ret))
    assert not ret.userdata and gl_names()==live
    scene_path.write_text(json.dumps({"layers":[entries[0]]*17}))
    assert not init(C.byref(Init(W,H,30,0,0)),C.byref(Return()))
    assert gl_names()==live
    idle,talking=folder/"idle.gif",folder/"talking.gif"
    Image.new("RGB",(12,10),"red").save(idle,duration=100,loop=0)
    Image.new("RGB",(6,10),"green").save(talking,duration=100,loop=0)
    level=folder/"level"
    level.write_text("0")
    fake=folder/"parec"
    fake.write_text("#!/usr/bin/env python3\nimport struct,sys,time\nfrom pathlib import Path\nlevel=Path("+repr(str(level))+")\nwhile True:\n sys.stdout.buffer.write(struct.pack('<f',float(level.read_text()))*320)\n sys.stdout.buffer.flush()\n time.sleep(0.02)\n")
    fake.chmod(0o700)
    oldpath=os.environ["PATH"]
    os.environ["PATH"]=str(folder)+os.pathsep+oldpath
    scene_path.write_text(json.dumps({"microphone":"synthetic","layers":[{"name":"Avatar","idle":str(idle),"talking":str(talking),"x":5,"y":7,"width":12,"threshold":0.1,"release_ms":120}]}))
    ret=Return()
    assert init(C.byref(Init(W,H,30,0,0)),C.byref(ret))
    idle.unlink(); talking.unlink(); scene_path.unlink()
    def assert_avatar(color):
        expected=background(0)
        expected.alpha_composite(Image.new("RGBA",(6 if color=="green" else 12,10),color),(5,7))
        hostile_state()
        before=state()
        ret.draw(C.byref(DrawParams(W,H)),ret.userdata)
        assert state()==before
        diff=ImageChops.difference(read_image(),expected)
        assert all(high<=1 for low,high in diff.getextrema()), diff.getextrema()
    try:
        time.sleep(0.08)
        assert_avatar("red")
        level.write_text("0.3")
        time.sleep(0.12)
        assert_avatar("green")
        level.write_text("0")
        time.sleep(0.06)
        assert_avatar("green")
        time.sleep(0.2)
        assert_avatar("red")
    finally:
        deinit(ret.userdata)
        os.environ["PATH"]=oldpath
        os.environ.pop("GSR_RUST_SCENE",None)
    assert gl_names()==live
    print("OK avatar: PCM sintético, umbral, espera, GIF sin archivos y cierre de parec")

assert make_current(display, None, None, None)
fn(egl, "eglDestroyContext", I, P, P)(display, context)
fn(egl, "eglDestroySurface", I, P, P)(display, surface)
fn(egl, "eglTerminate", I, P)(display)
