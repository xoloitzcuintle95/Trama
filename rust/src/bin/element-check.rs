//! Same configuration and decoders as plugin init, without a graphics context.
use gsr_overlay_rust::{config::ElementConfig, media::Media};
fn run() -> Result<(), String> {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 2 {
        return Err("Uso: element-check recurso.png|gif".into());
    }
    let config = ElementConfig::from_env()?;
    let media = Media::load(std::path::Path::new(&args[1]))?;
    let rect = config.resolve(media.width(), media.height())?;
    let asset = match &media {
        Media::Still(i) => format!(
            "{{\"width\":{},\"height\":{},\"frames\":1,\"cache_bytes\":0}}",
            i.width, i.height
        ),
        Media::Animated(a) => format!(
            "{{\"width\":{},\"height\":{},\"frames\":{},\"cache_bytes\":{},\"temporary_bytes\":{},\"cycle_ms\":{},\"plays\":{}}}",
            a.width,
            a.height,
            a.frames.len(),
            a.cache_bytes,
            a.temporary_bytes,
            a.cycle_ms,
            a.plays.map_or("null".into(), |n| n.to_string())
        ),
    };
    println!(
        "{{\"element\":{{\"x\":{},\"y\":{},\"width\":{},\"height\":{},\"visible\":{},\"keep_aspect\":{}}},\"asset\":{}}}",
        rect.x, rect.y, rect.width, rect.height, config.visible, config.keep_aspect, asset
    );
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
