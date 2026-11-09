//! Initial configuration for ONE visual element. Independent of media and GL.
//! Environment is read once in init; no reload, scene model or dynamic control.
const LIMIT: i32 = 16384;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Placement {
    pub x: f32,
    pub y: f32,
    pub width: f32,
    pub height: f32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ElementConfig {
    pub x: i32,
    pub y: i32,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub keep_aspect: bool,
    pub visible: bool,
}

#[derive(Default)]
struct Raw {
    x: Option<String>,
    y: Option<String>,
    width: Option<String>,
    height: Option<String>,
    keep_aspect: Option<String>,
    visible: Option<String>,
}

fn integer(name: &str, value: Option<&str>, minimum: i32) -> Result<Option<i32>, String> {
    let Some(value) = value else {
        return Ok(None);
    };
    let n = value
        .parse::<i32>()
        .map_err(|_| format!("{name}: se requiere un entero"))?;
    if n < minimum || n > LIMIT {
        return Err(format!("{name}: fuera de {minimum}..{LIMIT}"));
    }
    Ok(Some(n))
}

fn boolean(name: &str, value: Option<&str>) -> Result<bool, String> {
    match value {
        None | Some("true") => Ok(true),
        Some("false") => Ok(false),
        _ => Err(format!("{name}: usa true o false")),
    }
}

impl ElementConfig {
    fn parse(raw: Raw) -> Result<Self, String> {
        let config = Self {
            x: integer("GSR_OVERLAY_X", raw.x.as_deref(), -LIMIT)?.unwrap_or(32),
            y: integer("GSR_OVERLAY_Y", raw.y.as_deref(), -LIMIT)?.unwrap_or(32),
            width: integer("GSR_OVERLAY_WIDTH", raw.width.as_deref(), 1)?.map(|n| n as u32),
            height: integer("GSR_OVERLAY_HEIGHT", raw.height.as_deref(), 1)?.map(|n| n as u32),
            keep_aspect: boolean("GSR_OVERLAY_KEEP_ASPECT", raw.keep_aspect.as_deref())?,
            visible: boolean("GSR_OVERLAY_VISIBLE", raw.visible.as_deref())?,
        };
        if !config.keep_aspect && (config.width.is_none() || config.height.is_none()) {
            return Err("KEEP_ASPECT=false requiere WIDTH y HEIGHT explícitos".into());
        }
        Ok(config)
    }

    pub fn from_env() -> Result<Self, String> {
        fn read(name: &str) -> Result<Option<String>, String> {
            match std::env::var(name) {
                Ok(s) => Ok(Some(s)),
                Err(std::env::VarError::NotPresent) => Ok(None),
                Err(_) => Err(format!("{name}: valor no Unicode")),
            }
        }
        Self::parse(Raw {
            x: read("GSR_OVERLAY_X")?,
            y: read("GSR_OVERLAY_Y")?,
            width: read("GSR_OVERLAY_WIDTH")?,
            height: read("GSR_OVERLAY_HEIGHT")?,
            keep_aspect: read("GSR_OVERLAY_KEEP_ASPECT")?,
            visible: read("GSR_OVERLAY_VISIBLE")?,
        })
    }

    pub fn resolve(self, source_width: u32, source_height: u32) -> Result<Placement, String> {
        if source_width == 0 || source_height == 0 {
            return Err("recurso sin dimensiones".into());
        }
        let (sw, sh) = (source_width as f64, source_height as f64);
        let (w, h) = match (self.width, self.height) {
            (Some(w), Some(h)) if !self.keep_aspect => (w as f64, h as f64),
            (Some(w), Some(h)) => {
                let scale = (w as f64 / sw).min(h as f64 / sh);
                (sw * scale, sh * scale)
            }
            (None, Some(h)) => (h as f64 * sw / sh, h as f64),
            (width, None) => {
                let w = width.unwrap_or(320) as f64;
                (w, w * sh / sw)
            }
        };
        // Derived dimensions must obey the same output limits as explicit ones.
        if w <= 0. || h <= 0. || w > LIMIT as f64 || h > LIMIT as f64 {
            return Err("tamaño final fuera de 0..16384; especifica una caja menor".into());
        }
        Ok(Placement {
            x: self.x as f32,
            y: self.y as f32,
            width: w as f32,
            height: h as f32,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn defaults_and_each_dimension() {
        let c = ElementConfig::parse(Raw::default()).unwrap();
        assert!(c.visible && c.keep_aspect);
        assert_eq!(
            c.resolve(640, 480).unwrap(),
            Placement {
                x: 32.,
                y: 32.,
                width: 320.,
                height: 240.
            }
        );
        let height = ElementConfig::parse(Raw {
            height: Some("90".into()),
            ..Default::default()
        })
        .unwrap();
        assert_eq!(height.resolve(160, 90).unwrap().width, 160.);
        let width = ElementConfig::parse(Raw {
            width: Some("40".into()),
            ..Default::default()
        })
        .unwrap();
        assert_eq!(width.resolve(160, 90).unwrap().height, 22.5);
    }
    #[test]
    fn contain_or_explicit_stretch_and_hidden() {
        let mut c = ElementConfig::parse(Raw {
            x: Some("-12".into()),
            y: Some("0".into()),
            width: Some("100".into()),
            height: Some("100".into()),
            visible: Some("false".into()),
            ..Default::default()
        })
        .unwrap();
        assert!(!c.visible);
        assert_eq!(
            c.resolve(200, 100).unwrap(),
            Placement {
                x: -12.,
                y: 0.,
                width: 100.,
                height: 50.
            }
        );
        c.keep_aspect = false;
        assert_eq!(c.resolve(200, 100).unwrap().height, 100.);
        assert!(
            ElementConfig::parse(Raw {
                keep_aspect: Some("false".into()),
                ..Default::default()
            })
            .is_err()
        );
    }
    #[test]
    fn reject_invalid_bounds_and_booleans() {
        for value in ["0", "-1", "16385", "NaN", "", "1.5"] {
            assert!(
                ElementConfig::parse(Raw {
                    width: Some(value.into()),
                    ..Default::default()
                })
                .is_err()
            );
        }
        for value in ["yes", "0", "TRUE", ""] {
            assert!(
                ElementConfig::parse(Raw {
                    visible: Some(value.into()),
                    ..Default::default()
                })
                .is_err()
            );
        }
        assert!(
            ElementConfig::parse(Raw {
                x: Some("-16385".into()),
                ..Default::default()
            })
            .is_err()
        );
        let c = ElementConfig::parse(Raw::default()).unwrap();
        assert!(c.resolve(1, 4096).is_err());
        assert!(c.resolve(0, 2).is_err());
    }
}
