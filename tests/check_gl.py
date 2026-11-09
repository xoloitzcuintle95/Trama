"""Offscreen software EGL test. Does not test KMS or hardware encoding."""
import ctypes as C
import os
from pathlib import Path
import time
from PIL import Image, ImageChops

os.environ["EGL_PLATFORM"] = "surfaceless"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
egl = C.CDLL("libEGL.so.1")
gl = C.CDLL("libGL.so.1")


def function(lib, name, restype, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = restype, list(args)
    return f


ptr, integer = C.c_void_p, C.c_int
get_display = function(egl, "eglGetDisplay", ptr, ptr)
initialize = function(egl, "eglInitialize", integer, ptr, ptr, ptr)
choose = function(egl, "eglChooseConfig", integer, ptr, ptr, ptr, integer, ptr)
create_surface = function(egl, "eglCreatePbufferSurface", ptr, ptr, ptr, ptr)
create_context = function(egl, "eglCreateContext", ptr, ptr, ptr, ptr, ptr)
make_current = function(egl, "eglMakeCurrent", integer, ptr, ptr, ptr, ptr)


def attrs(*values):
    return (integer * len(values))(*values)


display = get_display(None)
assert initialize(display, None, None), "No se pudo iniciar EGL surfaceless"
assert function(egl, "eglBindAPI", integer, C.c_uint)(0x30A0)
config, count = ptr(), integer()
assert choose(display, attrs(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8,
                             0x3022, 8, 0x3021, 8, 0x3038), C.byref(config), 1, C.byref(count))
assert count.value
size = 800
surface = create_surface(display, config, attrs(0x3057, size, 0x3056, size, 0x3038))
context = create_context(display, config, None, attrs(0x3098, 3, 0x3038))
assert surface and context and make_current(display, surface, surface, context)
print("Renderer:", function(gl, "glGetString", C.c_char_p, C.c_uint)(0x1F01).decode())


class Init(C.Structure):
    _fields_ = [("width", C.c_uint), ("height", C.c_uint), ("fps", C.c_uint),
                ("depth", integer), ("api", integer)]


class DrawParams(C.Structure):
    _fields_ = [("width", C.c_uint), ("height", C.c_uint)]


Draw = C.CFUNCTYPE(None, C.POINTER(DrawParams), ptr)


class Result(C.Structure):
    _fields_ = [("name", C.c_char_p), ("version", C.c_uint), ("userdata", ptr),
                ("draw", Draw), ("damaged", ptr), ("clear", ptr)]


viewport = function(gl, "glViewport", None, integer, integer, integer, integer)
read = function(gl, "glReadPixels", None, integer, integer, integer, integer,
                C.c_uint, C.c_uint, ptr)
error = function(gl, "glGetError", C.c_uint)
clear_color = function(gl, "glClearColor", None, C.c_float, C.c_float, C.c_float, C.c_float)
clear = function(gl, "glClear", None, C.c_uint)
enable = function(gl, "glEnable", None, C.c_uint)
disable = function(gl, "glDisable", None, C.c_uint)
is_enabled = function(gl, "glIsEnabled", C.c_bool, C.c_uint)
blend_func = function(gl, "glBlendFuncSeparate", None, C.c_uint, C.c_uint, C.c_uint, C.c_uint)
get_integer = function(gl, "glGetIntegerv", None, C.c_uint, ptr)


def blending_state():
    values = []
    for enum in (0x80C9, 0x80C8, 0x80CB, 0x80CA):
        value = integer()
        get_integer(enum, C.byref(value))
        values.append(value.value)
    return is_enabled(0x0BE2), values


viewport(0, 0, size, size)

alpha = Image.new("RGBA", (12, 12), (40, 80, 120, 128))
alpha.save("build/test-alpha.png")
for name, media in (("triangle", "examples/assets/idle.gif"), ("overlay", "examples/assets/idle.gif"),
                     ("overlay", "build/test-alpha.png")):
    os.environ["GSR_OVERLAY_FILE"] = str(Path(media).resolve())
    with Image.open(media) as source:
        os.environ["GSR_OVERLAY_WIDTH"] = str(source.width)
    plugin = C.CDLL(str(Path(f"build/{name}.so").resolve()))
    init = function(plugin, "gsr_plugin_init", C.c_bool, C.POINTER(Init), C.POINTER(Result))
    deinit = function(plugin, "gsr_plugin_deinit", None, ptr)
    ret = Result()
    assert init(C.byref(Init(size, size, 30, 0, 0)), C.byref(ret))
    for frame_index in range(2):
        if frame_index:
            time.sleep(0.18)
        # GSR captures into plugins.color_conversion BEFORE calling draw. Its
        # framebuffer is a populated desktop, not a separate transparent layer.
        background = (64, 128, 192, 255) if not frame_index else (192, 64, 255, 255)
        clear_color(*(value / 255 for value in background))
        clear(0x4000)
        (enable if frame_index else disable)(0x0BE2)
        blend_func(1, 0, 0x0302, 0x0303)
        before = blending_state()
        ret.draw(C.byref(DrawParams(size, size)), ret.userdata)
        pixels = (C.c_ubyte * (size * size * 4))()
        read(0, 0, size, size, 0x1908, 0x1401, pixels)
        assert error() == 0, f"OpenGL error in {name}"
        # Same row order as GSR's color_conversion_read_destination_texture:
        # its software encoder passes glReadPixels directly to AVFrame rows.
        image = Image.frombytes("RGBA", (size, size), bytes(pixels))
        if name == "overlay":
            with Image.open(media) as reference:
                reference.seek(frame_index if media.endswith(".gif") else 0)
                expected = Image.new("RGBA", (size, size), background)
                expected.alpha_composite(reference.convert("RGBA"), (32, 32))
                # GPU UNORM rounding may differ by one from Pillow.
                difference = ImageChops.difference(image, expected)
                assert all(high <= 1 for low, high in difference.getextrema()), \
                    f"Desktop/alpha/orientation/frame mismatch {frame_index}: {difference.getextrema()}"
                assert blending_state() == before, "Plugin leaked blend state"
            image.save(f"build/{Path(media).stem}-frame-{frame_index}.png")
    deinit(ret.userdata)
    print(f"OK {name} ({media}): init/draw/deinit y OpenGL sin errores")

assert make_current(display, None, None, None)
function(egl, "eglDestroyContext", integer, ptr, ptr)(display, context)
function(egl, "eglDestroySurface", integer, ptr, ptr)(display, surface)
function(egl, "eglTerminate", integer, ptr)(display)
