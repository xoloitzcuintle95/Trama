//! Bounded preload + pure integer timeline. No GL, clocks, threads or file I/O.
use crate::image;
use std::{io::Cursor, num::NonZeroU64, time::Duration};

pub const MAX_CACHE_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_TEMP_BYTES: usize = 8 * 1024 * 1024;
pub const MAX_FRAMES: usize = 1024;

pub struct Frame {
    pub rgba: Vec<u8>,
    pub end_ms: u64,
}
pub struct Animation {
    pub width: u32,
    pub height: u32,
    pub frames: Vec<Frame>,
    pub plays: Option<u32>, // None infinite; n total plays, including first.
    pub cycle_ms: u64,
    pub cache_bytes: usize,
    pub temporary_bytes: usize,
}

struct Info {
    width: u32,
    height: u32,
    count: usize,
    plays: Option<u32>,
    max_indices: usize,
    previous_bytes: usize,
    background: [u8; 4],
}

struct Blocks<'a> {
    bytes: &'a [u8],
    pos: usize,
}
impl<'a> Blocks<'a> {
    fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
        let end = self.pos.checked_add(n).ok_or("GIF: desbordamiento")?;
        let value = self.bytes.get(self.pos..end).ok_or("GIF truncado")?;
        self.pos = end;
        Ok(value)
    }
    fn byte(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }
    fn subblocks(&mut self) -> Result<(), String> {
        loop {
            let n = self.byte()? as usize;
            if n == 0 {
                return Ok(());
            }
            self.take(n)?;
        }
    }
}
fn word(b: &[u8]) -> u32 {
    u16::from_le_bytes([b[0], b[1]]) as u32
}

// Parse container boundaries before allocating canvases/cache. Never search
// compressed image bytes for magic strings. Decoder still validates pixel data.
fn inspect(bytes: &[u8]) -> Result<Info, String> {
    if bytes.len() > image::MAX_FILE_BYTES {
        return Err("GIF comprimido excede 8 MiB".into());
    }
    let mut b = Blocks { bytes, pos: 0 };
    let header = b.take(13)?;
    if &header[..6] != b"GIF87a" && &header[..6] != b"GIF89a" {
        return Err("cabecera GIF inválida".into());
    }
    let width = word(&header[6..8]);
    let height = word(&header[8..10]);
    let canvas = image::rgba_size(width, height)?;
    let mut background = [0; 4];
    if header[10] & 0x80 != 0 {
        let palette = b.take(3 * (1 << ((header[10] & 7) + 1)))?;
        let index = header[11] as usize * 3;
        if let Some(rgb) = palette.get(index..index + 3) {
            background = [rgb[0], rgb[1], rgb[2], 255];
        }
    }
    let mut info = Info {
        width,
        height,
        count: 0,
        plays: Some(1),
        max_indices: 0,
        previous_bytes: 0,
        background,
    };
    let mut disposal = 0;
    loop {
        match b.byte()? {
            0x3b => {
                break;
            }
            0x21 => match b.byte()? {
                0xf9 => {
                    if b.byte()? != 4 {
                        return Err("GCE GIF inválido".into());
                    }
                    let control = b.take(4)?;
                    disposal = (control[0] >> 2) & 7;
                    if disposal > 3 || b.byte()? != 0 {
                        return Err("disposal/GCE GIF no soportado".into());
                    }
                }
                0xff => {
                    let n = b.byte()? as usize;
                    let app = b.take(n)?;
                    if app == b"NETSCAPE2.0" || app == b"ANIMEXTS1.0" {
                        if b.byte()? != 3 {
                            return Err("extensión de repetición inválida".into());
                        }
                        let repeat = b.take(3)?;
                        if repeat[0] != 1 {
                            return Err("extensión de repetición inválida".into());
                        }
                        info.plays = match word(&repeat[1..]) {
                            0 => None,
                            n => Some(n + 1),
                        };
                    }
                    b.subblocks()?;
                }
                0x01 => return Err("GIF con Plain Text no soportado".into()),
                _ => b.subblocks()?,
            },
            0x2c => {
                let rect = b.take(9)?;
                let (x, y, w, h) = (
                    word(&rect[..2]),
                    word(&rect[2..4]),
                    word(&rect[4..6]),
                    word(&rect[6..8]),
                );
                if w == 0 || h == 0 || x + w > width || y + h > height {
                    return Err("frame GIF fuera del lienzo".into());
                }
                info.count += 1;
                if info.count > MAX_FRAMES
                    || info
                        .count
                        .checked_mul(canvas)
                        .is_none_or(|n| n > MAX_CACHE_BYTES)
                {
                    return Err("GIF excede caché de 16 MiB o 1024 frames".into());
                }
                let indices = w as usize * h as usize;
                info.max_indices = info.max_indices.max(indices);
                if disposal == 3 {
                    info.previous_bytes = info.previous_bytes.max(indices * 4);
                }
                if canvas + info.max_indices + info.previous_bytes > MAX_TEMP_BYTES {
                    return Err("GIF excede temporales gestionados de 8 MiB".into());
                }
                disposal = 0;
                if rect[8] & 0x80 != 0 {
                    b.take(3 * (1 << ((rect[8] & 7) + 1)))?;
                }
                let minimum_code_size = b.byte()?;
                if !(2..=8).contains(&minimum_code_size) {
                    return Err("tamaño de código LZW inválido".into());
                }
                b.subblocks()?;
            }
            _ => return Err("bloque GIF desconocido".into()),
        }
    }
    if info.count == 0 {
        return Err("GIF sin frames/trailer".into());
    }
    Ok(info)
}

impl Animation {
    pub fn decode(bytes: Vec<u8>) -> Result<Self, String> {
        let info = inspect(&bytes)?;
        let canvas_bytes = image::rgba_size(info.width, info.height)?;
        let temporary_bytes = canvas_bytes + info.max_indices + info.previous_bytes;
        let mut canvas = image::buffer(canvas_bytes)?;
        let mut previous = image::buffer(info.previous_bytes)?;
        let mut indices = image::buffer(info.max_indices)?;
        let mut options = gif::DecodeOptions::new();
        options.set_color_output(gif::ColorOutput::Indexed);
        options.check_frame_consistency(true);
        options.check_lzw_end_code(true);
        options.set_memory_limit(gif::MemoryLimit::Bytes(
            NonZeroU64::new(MAX_TEMP_BYTES as u64).ok_or("presupuesto inválido")?,
        ));
        let mut reader = options
            .read_info(Cursor::new(bytes))
            .map_err(|e| format!("GIF: {e}"))?;
        let mut frames = Vec::new();
        frames
            .try_reserve_exact(info.count)
            .map_err(|_| "no se pudo reservar el caché GIF")?;
        let mut cycle_ms = 0u64;
        let mut first_transparent = false;
        while let Some(frame) = reader.next_frame_info().map_err(|e| format!("GIF: {e}"))? {
            let (x, y, w, h) = (
                frame.left as usize,
                frame.top as usize,
                frame.width as usize,
                frame.height as usize,
            );
            let (transparent, disposal, delay) = (frame.transparent, frame.dispose, frame.delay);
            if frames.len() >= info.count {
                return Err("conteo GIF inconsistente".into());
            }
            if frames.is_empty() {
                first_transparent = transparent.is_some();
                let bg = if first_transparent {
                    [0; 4]
                } else {
                    info.background
                };
                for pixel in canvas.as_chunks_mut::<4>().0 {
                    *pixel = bg;
                }
            }
            let mut palette = [0u8; 768];
            let table = reader.palette().map_err(|e| format!("paleta GIF: {e}"))?;
            if table.is_empty() || table.len() > palette.len() || table.len() % 3 != 0 {
                return Err("paleta GIF inválida".into());
            }
            let palette_len = table.len();
            palette[..palette_len].copy_from_slice(table);
            reader
                .read_into_buffer(&mut indices[..w * h])
                .map_err(|e| format!("LZW GIF: {e}"))?;
            if disposal == gif::DisposalMethod::Previous {
                for row in 0..h {
                    let start = ((y + row) * info.width as usize + x) * 4;
                    previous[row * w * 4..(row + 1) * w * 4]
                        .copy_from_slice(&canvas[start..start + w * 4]);
                }
            }
            for row in 0..h {
                for col in 0..w {
                    let index = indices[row * w + col];
                    if Some(index) != transparent {
                        let color = index as usize * 3;
                        if color + 3 > palette_len {
                            return Err("índice GIF fuera de la paleta".into());
                        }
                        let out = ((y + row) * info.width as usize + x + col) * 4;
                        canvas[out..out + 4].copy_from_slice(&[
                            palette[color],
                            palette[color + 1],
                            palette[color + 2],
                            255,
                        ]);
                    }
                }
            }
            let mut rgba = image::buffer(canvas_bytes)?;
            rgba.copy_from_slice(&canvas);
            image::premultiply(&mut rgba);
            cycle_ms = cycle_ms
                .checked_add(if delay == 0 { 100 } else { delay as u64 * 10 })
                .ok_or("duración GIF desbordada")?;
            frames.push(Frame {
                rgba,
                end_ms: cycle_ms,
            });
            if disposal == gif::DisposalMethod::Background {
                // Common transparent GIF convention, matching our C/Pillow reference.
                let bg = if first_transparent || transparent.is_some() {
                    [0; 4]
                } else {
                    info.background
                };
                for row in 0..h {
                    for col in 0..w {
                        let start = ((y + row) * info.width as usize + x + col) * 4;
                        canvas[start..start + 4].copy_from_slice(&bg);
                    }
                }
            } else if disposal == gif::DisposalMethod::Previous {
                for row in 0..h {
                    let start = ((y + row) * info.width as usize + x) * 4;
                    canvas[start..start + w * 4]
                        .copy_from_slice(&previous[row * w * 4..(row + 1) * w * 4]);
                }
            }
        }
        if frames.len() != info.count {
            return Err("GIF truncado o conteo inconsistente".into());
        }
        Ok(Self {
            width: info.width,
            height: info.height,
            cache_bytes: frames.len() * canvas_bytes,
            frames,
            cycle_ms,
            plays: info.plays,
            temporary_bytes,
        })
    }

    pub fn index_at(&self, elapsed: Duration) -> usize {
        let ms = elapsed.as_millis();
        let cycle = self.cycle_ms as u128;
        if self.plays.is_some_and(|n| ms >= cycle * n as u128) {
            return self.frames.len() - 1;
        }
        let phase = (ms % cycle) as u64;
        self.frames.partition_point(|frame| frame.end_ms <= phase)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn clip(plays: Option<u32>) -> Animation {
        Animation {
            width: 1,
            height: 1,
            frames: [150, 2150, 2300, 5300]
                .into_iter()
                .map(|end_ms| Frame {
                    rgba: vec![0; 4],
                    end_ms,
                })
                .collect(),
            plays,
            cycle_ms: 5300,
            cache_bytes: 16,
            temporary_bytes: 5,
        }
    }
    #[test]
    fn integer_timeline_boundaries_and_large_jumps() {
        let a = clip(None);
        for (ms, expected) in [
            (0, 0),
            (149, 0),
            (150, 1),
            (2149, 1),
            (2150, 2),
            (2299, 2),
            (2300, 3),
            (5299, 3),
            (5300, 0),
            (5450, 1),
            (10600, 0),
            (5_300_150, 1),
        ] {
            assert_eq!(a.index_at(Duration::from_millis(ms)), expected, "{ms}");
        }
        assert!(a.index_at(Duration::MAX) < 4);
    }
    #[test]
    fn finite_loops_hold_last_frame() {
        assert_eq!(clip(Some(1)).index_at(Duration::from_millis(5300)), 3);
        assert_eq!(clip(Some(2)).index_at(Duration::from_millis(5300)), 0);
        assert_eq!(clip(Some(2)).index_at(Duration::from_millis(10600)), 3);
        assert_eq!(clip(Some(2)).index_at(Duration::MAX), 3);
    }
    // Container only, intentionally no valid LZW for large dimensions: inspect
    // must reject budgets before any pixel decoding/allocation can be attempted.
    fn container(w: u16, h: u16, count: usize, previous: bool) -> Vec<u8> {
        let mut b = b"GIF89a".to_vec();
        b.extend(w.to_le_bytes());
        b.extend(h.to_le_bytes());
        b.extend([0x80, 0, 0, 0, 0, 0, 255, 255, 255]);
        for _ in 0..count {
            if previous {
                b.extend([0x21, 0xf9, 4, 12, 1, 0, 0, 0]);
            }
            b.extend([0x2c, 0, 0, 0, 0]);
            b.extend(w.to_le_bytes());
            b.extend(h.to_le_bytes());
            b.extend([0, 2, 2, 0x44, 1, 0]);
        }
        b.push(0x3b);
        b
    }
    #[test]
    fn budgets_checked_before_decoding() {
        assert!(inspect(&container(512, 512, 16, false)).is_ok());
        assert!(
            inspect(&container(512, 512, 17, false))
                .err()
                .unwrap()
                .contains("caché")
        );
        assert!(inspect(&container(1, 1, 1024, false)).is_ok());
        assert!(inspect(&container(1, 1, 1025, false)).is_err());
        assert!(inspect(&container(1024, 1024, 1, false)).is_ok());
        assert!(
            inspect(&container(1024, 1024, 1, true))
                .err()
                .unwrap()
                .contains("temporales")
        );
        assert!(Animation::decode(vec![0; image::MAX_FILE_BYTES + 1]).is_err());
    }
    #[test]
    fn container_validation() {
        let mut b = container(1, 1, 1, false);
        b.pop();
        assert!(inspect(&b).is_err());
        assert!(inspect(&container(0, 1, 1, false)).is_err());
        assert!(Animation::decode(container(100, 100, 1, false)).is_err()); // too few pixels
        assert!(inspect(&container(1, 1, 0, false)).is_err());
        let mut outside = container(1, 1, 1, false);
        outside[20] = 1; // x=1, width=1 exceeds the 1-pixel canvas.
        assert!(inspect(&outside).is_err());
        let mut unsupported = container(1, 1, 1, false);
        unsupported.splice(19..19, [0x21, 0xf9, 4, 16, 1, 0, 0, 0]);
        assert!(inspect(&unsupported).is_err()); // reserved disposal 4
    }
}
