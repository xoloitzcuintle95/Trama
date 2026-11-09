//! CPU-only image validation and decode, called during init, never during draw.
use std::{
    fs::File,
    io::{Cursor, Read},
    path::Path,
};

pub const MAX_FILE_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_RGBA_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_DIMENSION: u32 = 4096;

pub struct Image {
    pub width: u32,
    pub height: u32,
    pub rgba: Vec<u8>,
}

pub fn rgba_size(width: u32, height: u32) -> Result<usize, String> {
    if width == 0 || height == 0 || width > MAX_DIMENSION || height > MAX_DIMENSION {
        return Err("dimensiones de imagen fuera de 1..4096".into());
    }
    let bytes = (width as usize)
        .checked_mul(height as usize)
        .and_then(|n| n.checked_mul(4))
        .ok_or("desbordamiento de dimensiones")?;
    if bytes > MAX_RGBA_BYTES {
        return Err("imagen excede 16 MiB RGBA".into());
    }
    Ok(bytes)
}

pub(crate) fn buffer(size: usize) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    out.try_reserve_exact(size)
        .map_err(|_| "no se pudo reservar el buffer PNG")?;
    out.resize(size, 0);
    Ok(out)
}

pub fn load(path: &Path) -> Result<Image, String> {
    decode(read_file(path)?)
}

pub(crate) fn read_file(path: &Path) -> Result<Vec<u8>, String> {
    if !std::fs::metadata(path)
        .map_err(|e| e.to_string())?
        .is_file()
    {
        return Err("el recurso debe ser un archivo regular".into());
    }
    let file = File::open(path).map_err(|e| format!("abrir recurso: {e}"))?;
    if !file.metadata().map_err(|e| e.to_string())?.is_file() {
        return Err("la imagen debe ser un archivo regular".into());
    }
    if file.metadata().map_err(|e| e.to_string())?.len() > MAX_FILE_BYTES as u64 {
        return Err("recurso comprimido excede 8 MiB".into());
    }
    let mut bytes = Vec::new();
    file.take((MAX_FILE_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() > MAX_FILE_BYTES {
        return Err("recurso comprimido excede 8 MiB".into());
    }
    Ok(bytes)
}

pub(crate) fn premultiply(rgba: &mut [u8]) {
    for pixel in rgba.as_chunks_mut::<4>().0 {
        let alpha = pixel[3] as u16;
        for channel in &mut pixel[..3] {
            *channel = ((*channel as u16 * alpha + 127) / 255) as u8;
        }
    }
}

pub fn decode(bytes: Vec<u8>) -> Result<Image, String> {
    if bytes.len() > MAX_FILE_BYTES {
        return Err("recurso comprimido excede 8 MiB".into());
    }
    // IHDR is fixed at the start: reject oversized images before decoder allocation.
    if bytes.len() < 33 || bytes[..8] != *b"\x89PNG\r\n\x1a\n" || &bytes[12..16] != b"IHDR" {
        return Err("se requiere PNG estático válido".into());
    }
    let width = u32::from_be_bytes(bytes[16..20].try_into().map_err(|_| "IHDR inválido")?);
    let height = u32::from_be_bytes(bytes[20..24].try_into().map_err(|_| "IHDR inválido")?);
    let rgba_len = rgba_size(width, height)?;
    let mut decoder = png::Decoder::new_with_limits(
        Cursor::new(bytes),
        png::Limits {
            bytes: 32 * 1024 * 1024,
        },
    );
    decoder.set_ignore_text_chunk(true);
    decoder.set_ignore_iccp_chunk(true);
    decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
    let mut reader = decoder
        .read_info()
        .map_err(|e| format!("cabecera PNG: {e}"))?;
    if reader.info().animation_control.is_some() {
        return Err("APNG no soportado en esta entrega".into());
    }
    let size = reader.output_buffer_size().ok_or("tamaño PNG inválido")?;
    if size > MAX_RGBA_BYTES {
        return Err("salida PNG excede presupuesto".into());
    }
    let mut decoded = buffer(size)?;
    let info = reader
        .next_frame(&mut decoded)
        .map_err(|e| format!("decodificar PNG: {e}"))?;
    if info.width != width || info.height != height || info.bit_depth != png::BitDepth::Eight {
        return Err("formato PNG de salida no soportado".into());
    }
    decoded.truncate(info.buffer_size());
    let rgba = if info.color_type == png::ColorType::Rgba {
        decoded
    } else {
        let channels = match info.color_type {
            png::ColorType::Rgb => 3,
            png::ColorType::Grayscale => 1,
            png::ColorType::GrayscaleAlpha => 2,
            _ => return Err("paleta PNG no expandida".into()),
        };
        let mut out = buffer(rgba_len)?;
        for (src, dst) in decoded
            .chunks_exact(channels)
            .zip(out.as_chunks_mut::<4>().0.iter_mut())
        {
            match channels {
                1 => dst.copy_from_slice(&[src[0], src[0], src[0], 255]),
                2 => dst.copy_from_slice(&[src[0], src[0], src[0], src[1]]),
                _ => dst.copy_from_slice(&[src[0], src[1], src[2], 255]),
            }
        }
        out
    };
    if rgba.len() != rgba_len {
        return Err("longitud RGBA inesperada".into());
    }
    Ok(Image {
        width,
        height,
        rgba,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn reject_bad_and_oversized_before_decode() {
        assert!(decode(Vec::new()).is_err());
        assert!(decode(b"not a png".to_vec()).is_err());
        assert!(rgba_size(0, 12).is_err());
        assert!(rgba_size(4096, 4096).is_err());
        assert_eq!(rgba_size(627, 627).unwrap(), 1_572_516);
    }
    #[test]
    fn png_alpha_and_truncation() {
        let mut bytes = Vec::new();
        {
            let mut encoder = png::Encoder::new(&mut bytes, 2, 1);
            encoder.set_color(png::ColorType::Rgba);
            let mut writer = encoder.write_header().unwrap();
            writer
                .write_image_data(&[1, 2, 3, 0, 40, 80, 120, 128])
                .unwrap();
        }
        assert_eq!(
            decode(bytes.clone()).unwrap().rgba,
            [1, 2, 3, 0, 40, 80, 120, 128]
        );
        bytes.truncate(40);
        assert!(decode(bytes).is_err());
    }
}
