//! Diagnostic oracle for independent tests; outputs cached premultiplied RGBA.
use gsr_overlay_rust::media::Media;
use std::{io::Write, time::Duration};
fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 3 {
        return Err("Uso: media-dump recurso --info|milisegundos".into());
    }
    let media = Media::load(std::path::Path::new(&args[1]))?;
    if args[2] == "--info" {
        match &media {
            Media::Still(i) => println!(
                "{{\"width\":{},\"height\":{},\"frames\":1,\"cache_bytes\":0}}",
                i.width, i.height
            ),
            Media::Animated(a) => {
                let ends: Vec<_> = a.frames.iter().map(|f| f.end_ms).collect();
                println!(
                    "{{\"width\":{},\"height\":{},\"frames\":{},\"cache_bytes\":{},\"temporary_bytes\":{},\"cycle_ms\":{},\"plays\":{},\"ends_ms\":{:?}}}",
                    a.width,
                    a.height,
                    a.frames.len(),
                    a.cache_bytes,
                    a.temporary_bytes,
                    a.cycle_ms,
                    a.plays.map_or("null".into(), |n| n.to_string()),
                    ends
                );
            }
        }
    } else {
        let ms: u64 = args[2]
            .to_str()
            .ok_or("tiempo inválido")?
            .parse()
            .map_err(|_| "tiempo inválido")?;
        let pixels = match &media {
            Media::Still(i) => &i.rgba,
            Media::Animated(a) => &a.frames[a.index_at(Duration::from_millis(ms))].rgba,
        };
        std::io::stdout()
            .lock()
            .write_all(pixels)
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{error}");
        std::process::exit(1);
    }
}
