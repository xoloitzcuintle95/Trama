//! One preloaded source; no decoder/file survives initialization.
use crate::{
    animation::Animation,
    image::{self, Image},
};
use std::path::Path;

pub enum Media {
    Still(Image),
    Animated(Animation),
}

impl Media {
    pub fn load(path: &Path) -> Result<Self, String> {
        let bytes = image::read_file(path)?;
        if bytes.starts_with(b"GIF87a") || bytes.starts_with(b"GIF89a") {
            Ok(Self::Animated(Animation::decode(bytes)?))
        } else if bytes.starts_with(&[0xff, 0xd8]) {
            use zune_jpeg::zune_core::{colorspace::ColorSpace, options::DecoderOptions};
            let options = DecoderOptions::default()
                .set_max_width(image::MAX_DIMENSION as usize)
                .set_max_height(image::MAX_DIMENSION as usize)
                .jpeg_set_max_scans(64)
                .set_strict_mode(true)
                // RGB is the decoder's supported conversion target for all
                // JPEG inputs, including CMYK. Add opaque alpha ourselves.
                .jpeg_set_out_colorspace(ColorSpace::RGB);
            let mut decoder = zune_jpeg::JpegDecoder::new_with_options(&bytes, options);
            decoder
                .decode_headers()
                .map_err(|e| format!("cabecera JPG: {e}"))?;
            let info = decoder.info().ok_or("JPG sin dimensiones")?;
            let (width, height) = (info.width as u32, info.height as u32);
            let expected = image::rgba_size(width, height)?;
            // Grayscale JPEG headers override the requested RGB output in
            // zune-jpeg. Validate the actual layout, then expand once in init.
            let output_space = decoder.get_output_colorspace();
            let channels = match output_space {
                Some(ColorSpace::RGBA) => 4,
                Some(ColorSpace::RGB) => 3,
                Some(ColorSpace::Luma) => 1,
                _ => return Err("JPG: espacio de salida no soportado".into()),
            };
            let size = expected / 4 * channels;
            if decoder.output_buffer_size() != Some(size) {
                return Err("JPG: tamaño de salida inválido".into());
            }
            let decoded = decoder
                .decode()
                .map_err(|e| format!("decodificar JPG: {e}"))?;
            if decoded.len() != size || decoder.get_output_colorspace() != output_space {
                return Err("JPG: formato de salida cambió durante decode".into());
            }
            let rgba = if channels == 4 {
                decoded
            } else {
                let mut out = image::buffer(expected)?;
                for (pixel, rgba) in decoded
                    .chunks_exact(channels)
                    .zip(out.as_chunks_mut::<4>().0.iter_mut())
                {
                    if channels == 1 {
                        rgba.copy_from_slice(&[pixel[0], pixel[0], pixel[0], 255]);
                    } else {
                        rgba.copy_from_slice(&[pixel[0], pixel[1], pixel[2], 255]);
                    }
                }
                out
            };
            Ok(Self::Still(Image {
                width,
                height,
                rgba,
            }))
        } else {
            let mut image = image::decode(bytes)?;
            image::premultiply(&mut image.rgba);
            Ok(Self::Still(image))
        }
    }
    pub fn width(&self) -> u32 {
        match self {
            Self::Still(i) => i.width,
            Self::Animated(a) => a.width,
        }
    }
    pub fn height(&self) -> u32 {
        match self {
            Self::Still(i) => i.height,
            Self::Animated(a) => a.height,
        }
    }
    pub fn first_pixels(&self) -> &[u8] {
        match self {
            Self::Still(i) => &i.rgba,
            Self::Animated(a) => &a.frames[0].rgba,
        }
    }
}
