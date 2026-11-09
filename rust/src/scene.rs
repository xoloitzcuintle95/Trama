//! Concrete ordered layers. Files and decoders exist only during initialization.
use crate::{
    config::{ElementConfig, Placement},
    media::Media,
};
use serde::Deserialize;
use std::{
    io::Read,
    path::{Path, PathBuf},
};

pub const MAX_SCENE_BYTES: usize = 128 * 1024;
pub const MAX_LAYERS: usize = 16;
pub const MAX_SCENE_RGBA: usize = 64 * 1024 * 1024;
fn yes() -> bool {
    true
}
fn position() -> i32 {
    32
}
fn threshold() -> f32 {
    0.04
}
fn release() -> u64 {
    250
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct LayerSpec {
    pub name: String,
    pub path: Option<PathBuf>,
    pub idle: Option<PathBuf>,
    pub talking: Option<PathBuf>,
    #[serde(default = "position")]
    pub x: i32,
    #[serde(default = "position")]
    pub y: i32,
    pub width: Option<u32>,
    pub height: Option<u32>,
    #[serde(default = "yes")]
    pub keep_aspect: bool,
    #[serde(default = "yes")]
    pub visible: bool,
    #[serde(default = "threshold")]
    pub threshold: f32,
    #[serde(default = "release")]
    pub release_ms: u64,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SceneSpec {
    pub layers: Vec<LayerSpec>,
    pub microphone: Option<String>,
}
pub struct LoadedLayer {
    pub spec: LayerSpec,
    pub placement: Placement,
    pub sources: Vec<Media>,
}
pub struct LoadedScene {
    pub layers: Vec<LoadedLayer>,
    pub microphone: Option<String>,
    pub rgba_bytes: usize,
}
impl LoadedScene {
    pub fn from_path(path: &Path) -> Result<Self, String> {
        let file = std::fs::File::open(path).map_err(|e| format!("escena: {e}"))?;
        if !file.metadata().map_err(|e| e.to_string())?.is_file() {
            return Err("escena: archivo regular requerido".into());
        }
        let mut bytes = Vec::new();
        file.take((MAX_SCENE_BYTES + 1) as u64)
            .read_to_end(&mut bytes)
            .map_err(|e| e.to_string())?;
        if bytes.len() > MAX_SCENE_BYTES {
            return Err("escena excede 128 KiB".into());
        }
        let spec: SceneSpec = serde_json::from_slice(&bytes).map_err(|e| format!("escena: {e}"))?;
        Self::load(spec)
    }
    fn load(spec: SceneSpec) -> Result<Self, String> {
        if spec.layers.len() > MAX_LAYERS {
            return Err("escena: máximo 16 capas".into());
        }
        let mut total = 0usize;
        let mut layers = Vec::new();
        let mut avatars = 0;
        for layer in spec.layers {
            let result = (|| {
                if layer.name.is_empty() || layer.name.len() > 128 {
                    return Err("nombre vacío o >128 bytes".to_string());
                }
                let config = ElementConfig {
                    x: layer.x,
                    y: layer.y,
                    width: layer.width,
                    height: layer.height,
                    keep_aspect: layer.keep_aspect,
                    visible: layer.visible,
                };
                if !(-16384..=16384).contains(&config.x)
                    || !(-16384..=16384).contains(&config.y)
                    || config.width.is_some_and(|w| w == 0 || w > 16384)
                    || config.height.is_some_and(|h| h == 0 || h > 16384)
                    || (!config.keep_aspect && (config.width.is_none() || config.height.is_none()))
                {
                    return Err("posición/tamaño inválidos; rango ±16384, dimensiones 1..16384; deformar requiere ancho y alto".into());
                }
                let sources = match (&layer.path, &layer.idle, &layer.talking) {
                    (Some(path), None, None) => vec![Media::load(path)?],
                    (None, Some(idle), Some(talking)) => {
                        avatars += 1;
                        if avatars > 1 {
                            return Err("máximo un avatar".into());
                        }
                        if spec.microphone.as_ref().is_none_or(|s| s.is_empty()) {
                            return Err("avatar requiere micrófono resuelto".into());
                        }
                        if !layer.threshold.is_finite()
                            || layer.threshold <= 0.
                            || layer.threshold > 1.
                            || layer.release_ms > 5000
                        {
                            return Err(
                                "threshold: 0..1 exclusivo cero; release_ms: 0..5000".into()
                            );
                        }
                        let a = Media::load(idle)?;
                        let b = Media::load(talking)?;
                        if !matches!((&a, &b), (Media::Animated(_), Media::Animated(_))) {
                            return Err("avatar requiere dos GIF".into());
                        }
                        vec![a, b]
                    }
                    _ => return Err("elige path o bien idle y talking".into()),
                };
                for media in &sources {
                    let bytes = match media {
                        Media::Still(i) => i.rgba.len(),
                        Media::Animated(a) => a.cache_bytes,
                    };
                    total = total.checked_add(bytes).ok_or("presupuesto desbordado")?;
                    if total > MAX_SCENE_RGBA {
                        return Err("escena excede 64 MiB RGBA precargados".into());
                    }
                }
                let placement = config.resolve(sources[0].width(), sources[0].height())?;
                Ok((sources, placement))
            })();
            let (sources, placement) =
                result.map_err(|e: String| format!("capa {}: {e}", layer.name))?;
            layers.push(LoadedLayer {
                spec: layer,
                placement,
                sources,
            });
        }
        Ok(Self {
            layers,
            microphone: spec.microphone,
            rgba_bytes: total,
        })
    }
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({"rgba_bytes":self.rgba_bytes,"layers":self.layers.iter().map(|l|serde_json::json!({"name":l.spec.name,"x":l.placement.x,"y":l.placement.y,"width":l.placement.width,"height":l.placement.height,"visible":l.spec.visible,"avatar":l.sources.len()==2})).collect::<Vec<_>>()})
    }
}
