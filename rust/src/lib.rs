//! GSR 6.1.7 plugin, ordered PNG/JPG/GIF layers with bounded preload. See rust/SAFETY.md.
pub mod abi;
pub mod animation;
mod boundary;
pub mod config;
pub mod image;
pub mod media;
mod microphone;
mod render;
pub mod scene;

use abi::{DrawParams, InitParams, InitReturn};
use std::{
    ffi::c_void,
    thread::{self, ThreadId},
    time::{Duration, Instant},
};

struct Visual {
    renderer: render::Renderer,
    animation: Option<animation::Animation>,
    started: Option<Instant>,
    last_frame: usize,
}
impl Visual {
    fn frame_index(&self, time: Option<u64>) -> usize {
        let elapsed = time
            .map(Duration::from_millis)
            .unwrap_or_else(|| self.started.map(|t| t.elapsed()).unwrap_or(Duration::ZERO));
        self.animation.as_ref().map_or(0, |a| a.index_at(elapsed))
    }
    fn new(
        api: render::Api,
        media: media::Media,
        placement: config::Placement,
    ) -> Result<Self, String> {
        let renderer = render::Renderer::new(
            api,
            media.width(),
            media.height(),
            media.first_pixels(),
            placement,
        )?;
        let animation = match media {
            media::Media::Animated(a) => Some(a),
            media::Media::Still(_) => None,
        };
        Ok(Self {
            renderer,
            animation,
            started: None,
            last_frame: 0,
        })
    }
    fn draw(&mut self, params: &DrawParams, time: Option<u64>) -> Result<(), &'static str> {
        self.started.get_or_insert_with(Instant::now);
        let index = self.frame_index(time);
        let upload = if index != self.last_frame {
            self.animation
                .as_ref()
                .map(|a| a.frames[index].rgba.as_slice())
        } else {
            None
        };
        self.renderer.draw(params.width, params.height, upload)?;
        self.last_frame = index;
        Ok(())
    }
}
struct Layer {
    visuals: Vec<Visual>,
    visible: bool,
    selected: usize,
}
struct State {
    layers: Vec<Layer>,
    microphone: Option<microphone::Microphone>,
    owner: ThreadId,
    failed: bool,
    #[cfg(feature = "test-hooks")]
    panic_at: String,
    #[cfg(feature = "test-hooks")]
    elapsed_ms: Option<u64>,
}
impl State {
    fn time(&self) -> Option<u64> {
        #[cfg(feature = "test-hooks")]
        {
            self.elapsed_ms
        }
        #[cfg(not(feature = "test-hooks"))]
        {
            None
        }
    }
    fn talking(&self) -> bool {
        self.microphone.as_ref().is_some_and(|m| m.talking())
    }
}
fn initialize(params: &InitParams) -> Result<State, String> {
    if params.color_depth != 0 {
        return Err("solo SDR de 8 bits".into());
    }
    if params.width == 0 || params.height == 0 || params.width > 16384 || params.height > 16384 {
        return Err("dimensiones de lienzo inválidas".into());
    }
    let api = match params.graphics_api {
        0 => render::Api::EglEs,
        1 => render::Api::Glx,
        _ => return Err("API gráfica desconocida".into()),
    };
    let mut layers = Vec::new();
    let mut microphone = None;
    if let Some(path) = std::env::var_os("GSR_RUST_SCENE") {
        let loaded = scene::LoadedScene::from_path(std::path::Path::new(&path))?;
        for layer in loaded.layers {
            if layer.sources.len() == 2 {
                microphone = Some(microphone::Microphone::start(
                    loaded.microphone.as_deref().ok_or("falta micrófono")?,
                    layer.spec.threshold,
                    layer.spec.release_ms,
                )?);
            }
            let visuals = layer
                .sources
                .into_iter()
                .map(|m| {
                    // Idle resolves the common avatar box. Fit each source into
                    // that same box; different source aspect ratios never move
                    // the element or silently distort it.
                    let mut placement = layer.placement;
                    if layer.spec.keep_aspect {
                        let scale = (placement.width / m.width() as f32)
                            .min(placement.height / m.height() as f32);
                        placement.width = m.width() as f32 * scale;
                        placement.height = m.height() as f32 * scale;
                    }
                    Visual::new(api, m, placement)
                })
                .collect::<Result<Vec<_>, _>>()?;
            layers.push(Layer {
                visuals,
                visible: layer.spec.visible,
                selected: 0,
            });
        }
    } else {
        let path = std::env::var_os("GSR_RUST_IMAGE")
            .ok_or("falta GSR_RUST_IMAGE con ruta a PNG, JPG o GIF")?;
        let config = config::ElementConfig::from_env()?;
        let media = media::Media::load(std::path::Path::new(&path))?;
        let placement = config.resolve(media.width(), media.height())?;
        layers.push(Layer {
            visuals: vec![Visual::new(api, media, placement)?],
            visible: config.visible,
            selected: 0,
        });
    }
    let state = State {
        layers,
        microphone,
        owner: thread::current().id(),
        failed: false,
        #[cfg(feature = "test-hooks")]
        panic_at: std::env::var("GSR_RUST_TEST_PANIC").unwrap_or_default(),
        #[cfg(feature = "test-hooks")]
        elapsed_ms: None,
    };
    #[cfg(feature = "test-hooks")]
    if state.panic_at == "init" {
        panic!("test init");
    }
    Ok(state)
}

/// # Safety
/// Host provides aligned/readable params and unique writable ret. The original
/// GL context must be current on this thread and live until deinit. See SAFETY.md.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn gsr_plugin_init(params: *const InitParams, ret: *mut InitReturn) -> bool {
    boundary::guard(false, || {
        if params.is_null() || ret.is_null() {
            return false;
        }
        // SAFETY: caller guarantees valid distinct parameter/output memory.
        unsafe {
            ret.write(InitReturn::default());
        }
        // SAFETY: params points to the host's initialized C struct for this call.
        let state = match initialize(unsafe { &*params }) {
            Ok(state) => state,
            Err(error) => {
                boundary::log(&error);
                return false;
            }
        };
        let data = Box::into_raw(Box::new(state));
        // SAFETY: transfer one Box to the host; it must return userdata unchanged
        // and exactly once to deinit. No fallible operation follows this transfer.
        unsafe {
            ret.write(InitReturn {
                name: c"rust-media-overlay".as_ptr(),
                version: 4,
                userdata: data.cast(),
                draw: Some(draw),
                is_damaged: Some(is_damaged),
                clear_damage: Some(clear_damage),
            });
        }
        true
    })
}

unsafe extern "C" fn draw(params: *const DrawParams, userdata: *mut c_void) {
    boundary::guard((), || {
        if params.is_null() || userdata.is_null() {
            return;
        }
        // SAFETY: host serializes callbacks and returns the live Box pointer from
        // init unchanged, with initialized C parameters, until deinit consumes it.
        let (state, params) = unsafe { (&mut *userdata.cast::<State>(), &*params) };
        if state.failed || state.owner != thread::current().id() {
            return;
        }
        state.failed = true; // Remains disabled if draw unwinds.
        #[cfg(feature = "test-hooks")]
        if state.panic_at == "draw" {
            panic!("test draw");
        }
        if state.microphone.as_ref().is_some_and(|m| m.failed()) {
            boundary::log(
                "se perdió el detector del micrófono; overlay desactivado, revisar fuente/parec",
            );
            return;
        }
        let talking = state.talking();
        let time = state.time();
        for layer in &mut state.layers {
            if !layer.visible {
                continue;
            }
            let selected = usize::from(layer.visuals.len() == 2 && talking);
            if selected != layer.selected {
                layer.visuals[selected].started = None;
                layer.selected = selected;
            }
            if let Err(error) = layer.visuals[selected].draw(params, time) {
                boundary::log(error);
                return;
            }
        }
        state.failed = false;
    });
}

unsafe extern "C" fn is_damaged(userdata: *mut c_void) -> bool {
    boundary::guard(false, || {
        if userdata.is_null() {
            return false;
        }
        // SAFETY: same live, serialized host-owned userdata contract as draw.
        let state = unsafe { &mut *userdata.cast::<State>() };
        if state.owner != thread::current().id() || state.failed {
            return false;
        }
        state.failed = true;
        #[cfg(feature = "test-hooks")]
        if state.panic_at == "damage" {
            panic!("test damage");
        }
        state.failed = false;
        {
            let talking = state.talking();
            let time = state.time();
            state.microphone.as_ref().is_some_and(|m| m.failed())
                || state.layers.iter().any(|layer| {
                    if !layer.visible {
                        return false;
                    }
                    let selected = usize::from(layer.visuals.len() == 2 && talking);
                    let visual = &layer.visuals[selected];
                    selected != layer.selected
                        || visual.started.is_none()
                        || visual.frame_index(time) != visual.last_frame
                })
        }
    })
}

unsafe extern "C" fn clear_damage(userdata: *mut c_void) {
    boundary::guard((), || {
        if userdata.is_null() {
            return;
        }
        // SAFETY: same live, serialized host-owned userdata contract as draw.
        let state = unsafe { &mut *userdata.cast::<State>() };
        if state.owner != thread::current().id() || state.failed {
            return;
        }
        state.failed = true;
        #[cfg(feature = "test-hooks")]
        if state.panic_at == "clear" {
            panic!("test clear");
        }
        // GSR clears damage before draw. Only a successful draw acknowledges
        // the uploaded index; clearing it here would lose animation updates.
        state.failed = false;
    });
}

/// Deterministic clock injection only in the isolated test build; never shipped.
/// # Safety
/// Same live, serialized userdata contract as the plugin callbacks.
#[cfg(feature = "test-hooks")]
#[unsafe(no_mangle)]
pub unsafe extern "C" fn gsr_test_set_time(userdata: *mut c_void, ms: u64) {
    boundary::guard((), || {
        if userdata.is_null() {
            return;
        }
        // SAFETY: test host owns a live userdata and serializes all callbacks.
        let state = unsafe { &mut *userdata.cast::<State>() };
        if state.owner == thread::current().id() {
            state.elapsed_ms = Some(ms);
        }
    });
}

/// # Safety
/// userdata is either NULL or exactly the live pointer returned by successful
/// init, consumed once. Original thread/context must be current to free GL names.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn gsr_plugin_deinit(userdata: *mut c_void) {
    boundary::guard((), || {
        if userdata.is_null() {
            return;
        }
        // SAFETY: single ownership transfer back from host; no later callbacks.
        let state = unsafe { Box::from_raw(userdata.cast::<State>()) };
        #[cfg(feature = "test-hooks")]
        if state.panic_at == "deinit" {
            panic!("test deinit");
        }
        // Renderer validates original thread/context before GL cleanup, including
        // during unwind. Never call GL blindly from a destructor on another thread.
        drop(state);
    });
}
