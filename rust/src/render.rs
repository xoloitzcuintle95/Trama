//! Only this module calls OpenGL/EGL/GLX. No framebuffer readback.
//! Unsafe GL calls require a live context on its owning thread. Every public
//! operation checks that identity; GL objects are never moved between threads.
use crate::{boundary, config::Placement};
use glow::HasContext;
use std::{
    ffi::{CStr, c_char, c_void},
    rc::Rc,
    thread::{self, ThreadId},
};

#[link(name = "EGL")]
unsafe extern "C" {
    fn eglGetCurrentContext() -> *mut c_void;
    fn eglGetProcAddress(name: *const c_char) -> *const c_void;
}
#[link(name = "GL")]
unsafe extern "C" {
    fn glXGetCurrentContext() -> *mut c_void;
    fn glXGetProcAddressARB(name: *const u8) -> *const c_void;
}

#[derive(Clone, Copy)]
pub enum Api {
    EglEs,
    Glx,
}

impl Api {
    fn current(self) -> *mut c_void {
        // SAFETY: these context query functions take no pointers, work without
        // a current context, and are linked from the system EGL/GL libraries.
        unsafe {
            match self {
                Self::EglEs => eglGetCurrentContext(),
                Self::Glx => glXGetCurrentContext(),
            }
        }
    }
    fn symbol(self, name: &CStr) -> *const c_void {
        // SAFETY: name is a NUL-terminated GL symbol; addresses are used only
        // with this context/API and system library remains loaded for the cdylib.
        unsafe {
            match self {
                Self::EglEs => eglGetProcAddress(name.as_ptr()),
                Self::Glx => glXGetProcAddressARB(name.as_ptr().cast()),
            }
        }
    }
}

struct Context {
    gl: glow::Context,
    api: Api,
    native: *mut c_void,
    owner: ThreadId,
}
impl Context {
    fn current(&self) -> bool {
        self.owner == thread::current().id() && self.api.current() == self.native
    }
}

/// Resources are !Send/!Sync through Rc. Cleanup also checks thread/context: if
/// the host violates deinit's contract, leak GL names rather than delete in an
/// unrelated context. The driver releases them when the original context dies.
#[derive(Default)]
struct Objects {
    context: Option<Rc<Context>>,
    program: Option<glow::Program>,
    shaders: Vec<glow::Shader>,
    vao: Option<glow::VertexArray>,
    vbo: Option<glow::Buffer>,
    texture: Option<glow::Texture>,
}
impl Drop for Objects {
    fn drop(&mut self) {
        let Some(ctx) = &self.context else {
            return;
        };
        if !ctx.current() {
            boundary::log("deinit sin el contexto/hilo original; no se destruyen nombres GL");
            return;
        }
        // SAFETY: checked original current context/thread; all names were
        // allocated by that context, each tracked exactly once, no live draw.
        unsafe {
            for shader in self.shaders.drain(..) {
                ctx.gl.delete_shader(shader);
            }
            if let Some(name) = self.program.take() {
                ctx.gl.delete_program(name);
            }
            if let Some(name) = self.vao.take() {
                ctx.gl.delete_vertex_array(name);
            }
            if let Some(name) = self.vbo.take() {
                ctx.gl.delete_buffer(name);
            }
            if let Some(name) = self.texture.take() {
                ctx.gl.delete_texture(name);
            }
        }
    }
}

const CAPS: [u32; 6] = [
    glow::BLEND,
    glow::SCISSOR_TEST,
    glow::DEPTH_TEST,
    glow::STENCIL_TEST,
    glow::CULL_FACE,
    glow::RASTERIZER_DISCARD,
];
const UNPACK: [u32; 4] = [
    glow::UNPACK_ALIGNMENT,
    glow::UNPACK_ROW_LENGTH,
    glow::UNPACK_SKIP_ROWS,
    glow::UNPACK_SKIP_PIXELS,
];

struct SavedState<'a> {
    ctx: &'a Context,
    program: Option<glow::Program>,
    vao: Option<glow::VertexArray>,
    buffer: Option<glow::Buffer>,
    unpack_buffer: Option<glow::Buffer>,
    active: u32,
    texture: Option<glow::Texture>,
    sampler: Option<glow::Sampler>,
    caps: [bool; 6],
    unpack: [i32; 4],
    mask: [bool; 4],
    blend: [u32; 6],
}
impl<'a> SavedState<'a> {
    fn capture(ctx: &'a Context) -> Self {
        let gl = &ctx.gl;
        // SAFETY: called only after checking original current context. These
        // queries are valid in GL3/GLES3. Unit 0 is restored even on Rust unwind.
        unsafe {
            let active = gl.get_parameter_i32(glow::ACTIVE_TEXTURE) as u32;
            let program = gl.get_parameter_program(glow::CURRENT_PROGRAM);
            let vao = gl.get_parameter_vertex_array(glow::VERTEX_ARRAY_BINDING);
            let buffer = gl.get_parameter_buffer(glow::ARRAY_BUFFER_BINDING);
            let unpack_buffer = gl.get_parameter_buffer(glow::PIXEL_UNPACK_BUFFER_BINDING);
            let caps = CAPS.map(|cap| gl.is_enabled(cap));
            let unpack = UNPACK.map(|key| gl.get_parameter_i32(key));
            let mask = gl.get_parameter_bool_array::<4>(glow::COLOR_WRITEMASK);
            let blend = [
                glow::BLEND_SRC_RGB,
                glow::BLEND_DST_RGB,
                glow::BLEND_SRC_ALPHA,
                glow::BLEND_DST_ALPHA,
                glow::BLEND_EQUATION_RGB,
                glow::BLEND_EQUATION_ALPHA,
            ]
            .map(|key| gl.get_parameter_i32(key) as u32);
            gl.active_texture(glow::TEXTURE0);
            Self {
                ctx,
                program,
                vao,
                buffer,
                unpack_buffer,
                active,
                texture: gl.get_parameter_texture(glow::TEXTURE_BINDING_2D),
                sampler: gl.get_parameter_sampler(glow::SAMPLER_BINDING),
                caps,
                unpack,
                mask,
                blend,
            }
        }
    }
}
impl Drop for SavedState<'_> {
    fn drop(&mut self) {
        if !self.ctx.current() {
            return;
        }
        let gl = &self.ctx.gl;
        // SAFETY: original context remains current during callback/unwind;
        // saved host object names remain owned/live by the host throughout it.
        unsafe {
            gl.use_program(self.program);
            gl.bind_vertex_array(self.vao);
            gl.bind_buffer(glow::ARRAY_BUFFER, self.buffer);
            gl.bind_buffer(glow::PIXEL_UNPACK_BUFFER, self.unpack_buffer);
            gl.active_texture(glow::TEXTURE0);
            gl.bind_texture(glow::TEXTURE_2D, self.texture);
            gl.bind_sampler(0, self.sampler);
            gl.active_texture(self.active);
            for (key, value) in UNPACK.into_iter().zip(self.unpack) {
                gl.pixel_store_i32(key, value);
            }
            for (cap, enabled) in CAPS.into_iter().zip(self.caps) {
                if enabled {
                    gl.enable(cap);
                } else {
                    gl.disable(cap);
                }
            }
            gl.color_mask(self.mask[0], self.mask[1], self.mask[2], self.mask[3]);
            gl.blend_func_separate(self.blend[0], self.blend[1], self.blend[2], self.blend[3]);
            gl.blend_equation_separate(self.blend[4], self.blend[5]);
        }
    }
}

pub struct Renderer {
    objects: Objects,
    context: Rc<Context>,
    program: glow::Program,
    vao: glow::VertexArray,
    texture: glow::Texture,
    rect: glow::UniformLocation,
    placement: Placement,
    source_width: u32,
    source_height: u32,
}

impl Renderer {
    pub fn current(&self) -> bool {
        self.context.current()
    }

    pub fn new(
        api: Api,
        source_width: u32,
        source_height: u32,
        pixels: &[u8],
        placement: Placement,
    ) -> Result<Self, String> {
        if pixels.len() != crate::image::rgba_size(source_width, source_height)? {
            return Err("longitud de textura inicial inválida".into());
        }
        let native = api.current();
        if native.is_null() {
            return Err("no hay contexto GL actual para la API solicitada".into());
        }
        // SAFETY: a current GL context was checked. Loader resolves symbols
        // from its matching API; the context must remain live until deinit.
        let gl = unsafe { glow::Context::from_loader_function_cstr(|name| api.symbol(name)) };
        if gl.version().major < 3 {
            return Err("se requiere GL/GLES 3 o superior".into());
        }
        // GSR uses sampler objects only with modern desktop contexts. Our state
        // isolation needs GL 3.3 or ARB_sampler_objects (GLES3 includes it).
        if matches!(api, Api::Glx)
            && gl.version().major == 3
            && gl.version().minor < 3
            && !gl.supported_extensions().contains("GL_ARB_sampler_objects")
        {
            return Err("GLX requiere GL 3.3 o ARB_sampler_objects".into());
        }
        let ctx = Rc::new(Context {
            gl,
            api,
            native,
            owner: thread::current().id(),
        });
        let gl = &ctx.gl;
        let _saved = SavedState::capture(&ctx);
        let mut objects = Objects {
            context: Some(ctx.clone()),
            program: None,
            shaders: Vec::new(),
            vao: None,
            vbo: None,
            texture: None,
        };
        // SAFETY: original GL3/GLES3 context is current. Every allocated GL name
        // is tracked immediately for cleanup on any error or unwind. Image size
        // and RGBA length were validated before this function; no PBO is bound.
        unsafe {
            let limit = gl.get_parameter_i32(glow::MAX_TEXTURE_SIZE);
            if source_width > limit as u32 || source_height > limit as u32 {
                return Err("imagen excede GL_MAX_TEXTURE_SIZE".into());
            }
            let prefix = match api {
                Api::EglEs => "#version 300 es\nprecision highp float;\n",
                Api::Glx => "#version 130\n",
            };
            for (kind, body) in [
                (
                    glow::VERTEX_SHADER,
                    "in vec2 position; out vec2 uv; uniform vec4 rect;\nvoid main(){uv=position;gl_Position=vec4(mix(rect.xy,rect.zw,position),0,1);}",
                ),
                (
                    glow::FRAGMENT_SHADER,
                    "in vec2 uv; out vec4 color; uniform sampler2D image;\nvoid main(){color=texture(image,uv);}",
                ),
            ] {
                let shader = gl.create_shader(kind)?;
                objects.shaders.push(shader);
                gl.shader_source(shader, &format!("{prefix}{body}"));
                gl.compile_shader(shader);
                if !gl.get_shader_compile_status(shader) {
                    return Err(gl.get_shader_info_log(shader));
                }
            }
            let program = gl.create_program()?;
            objects.program = Some(program);
            for shader in &objects.shaders {
                gl.attach_shader(program, *shader);
            }
            gl.bind_attrib_location(program, 0, "position");
            gl.link_program(program);
            if !gl.get_program_link_status(program) {
                return Err(gl.get_program_info_log(program));
            }
            for shader in objects.shaders.drain(..) {
                gl.detach_shader(program, shader);
                gl.delete_shader(shader);
            }
            let rect = gl
                .get_uniform_location(program, "rect")
                .ok_or("uniform rect ausente")?;
            gl.use_program(Some(program));
            gl.uniform_1_i32(gl.get_uniform_location(program, "image").as_ref(), 0);
            let vao = gl.create_vertex_array()?;
            objects.vao = Some(vao);
            gl.bind_vertex_array(Some(vao));
            let vbo = gl.create_buffer()?;
            objects.vbo = Some(vbo);
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(vbo));
            let vertices = [0.0f32, 0., 0., 1., 1., 0., 1., 1.];
            let bytes: Vec<u8> = vertices.into_iter().flat_map(f32::to_ne_bytes).collect();
            gl.buffer_data_u8_slice(glow::ARRAY_BUFFER, &bytes, glow::STATIC_DRAW);
            gl.enable_vertex_attrib_array(0);
            gl.vertex_attrib_pointer_f32(0, 2, glow::FLOAT, false, 8, 0);
            let texture = gl.create_texture()?;
            objects.texture = Some(texture);
            gl.bind_texture(glow::TEXTURE_2D, Some(texture));
            gl.bind_buffer(glow::PIXEL_UNPACK_BUFFER, None);
            for (key, value) in UNPACK.into_iter().zip([1, 0, 0, 0]) {
                gl.pixel_store_i32(key, value);
            }
            for key in [glow::TEXTURE_MIN_FILTER, glow::TEXTURE_MAG_FILTER] {
                gl.tex_parameter_i32(glow::TEXTURE_2D, key, glow::LINEAR as i32);
            }
            for key in [glow::TEXTURE_WRAP_S, glow::TEXTURE_WRAP_T] {
                gl.tex_parameter_i32(glow::TEXTURE_2D, key, glow::CLAMP_TO_EDGE as i32);
            }
            gl.tex_image_2d(
                glow::TEXTURE_2D,
                0,
                glow::RGBA8 as i32,
                source_width as i32,
                source_height as i32,
                0,
                glow::RGBA,
                glow::UNSIGNED_BYTE,
                glow::PixelUnpackData::Slice(Some(pixels)),
            );
            let error = gl.get_error();
            if error != glow::NO_ERROR {
                return Err(format!("error GL durante init: {error:#x}"));
            }
            Ok(Self {
                objects,
                context: ctx.clone(),
                program,
                vao,
                texture,
                rect,
                placement,
                source_width,
                source_height,
            })
        }
        // PNG CPU pixels are released by the caller; GIF frames remain cached.
    }

    pub fn draw(&self, width: u32, height: u32, upload: Option<&[u8]>) -> Result<(), &'static str> {
        if !self.current() {
            return Err("draw sin el contexto/hilo original");
        }
        if width == 0 || height == 0 || width > 16384 || height > 16384 {
            return Err("lienzo fuera de límites");
        }
        if upload.is_some_and(|p| {
            p.len() != self.source_width as usize * self.source_height as usize * 4
        }) {
            return Err("longitud de frame GIF inválida");
        }
        let _keep_objects_alive = &self.objects;
        let gl = &self.context.gl;
        let _saved = SavedState::capture(&self.context);
        // SAFETY: checked original current context; objects are owned by self,
        // no concurrent callbacks; shader/VAO and valid texture were initialized.
        // GSR owns framebuffer/viewport. Optional upload references an already
        // decoded bounded cache; its slice lives until tex_sub_image_2d returns.
        unsafe {
            gl.enable(glow::BLEND);
            for cap in &CAPS[1..] {
                gl.disable(*cap);
            }
            gl.color_mask(true, true, true, true);
            gl.blend_equation_separate(glow::FUNC_ADD, glow::FUNC_ADD);
            gl.blend_func_separate(
                glow::ONE,
                glow::ONE_MINUS_SRC_ALPHA,
                glow::ONE,
                glow::ONE_MINUS_SRC_ALPHA,
            );
            gl.active_texture(glow::TEXTURE0);
            gl.bind_sampler(0, None);
            gl.bind_texture(glow::TEXTURE_2D, Some(self.texture));
            if let Some(pixels) = upload {
                gl.bind_buffer(glow::PIXEL_UNPACK_BUFFER, None);
                for (key, value) in UNPACK.into_iter().zip([1, 0, 0, 0]) {
                    gl.pixel_store_i32(key, value);
                }
                gl.tex_sub_image_2d(
                    glow::TEXTURE_2D,
                    0,
                    0,
                    0,
                    self.source_width as i32,
                    self.source_height as i32,
                    glow::RGBA,
                    glow::UNSIGNED_BYTE,
                    glow::PixelUnpackData::Slice(Some(pixels)),
                );
                if gl.get_error() != glow::NO_ERROR {
                    return Err("error GL al actualizar frame GIF");
                }
            }
            gl.bind_vertex_array(Some(self.vao));
            gl.use_program(Some(self.program));
            // GSR encoded row 0 is GL texture row 0. Do not flip the image.
            let left = -1. + 2. * self.placement.x / width as f32;
            let top = -1. + 2. * self.placement.y / height as f32;
            gl.uniform_4_f32(
                Some(&self.rect),
                left,
                top,
                left + 2. * self.placement.width / width as f32,
                top + 2. * self.placement.height / height as f32,
            );
            gl.draw_arrays(glow::TRIANGLE_STRIP, 0, 4);
        }
        Ok(())
    }
}
