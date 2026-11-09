fn main() {
    let args: Vec<_> = std::env::args_os().collect();
    if args.len() != 2 {
        eprintln!("Uso: image-check recurso.png|gif");
        std::process::exit(2);
    }
    match gsr_overlay_rust::media::Media::load(std::path::Path::new(&args[1])) {
        Ok(gsr_overlay_rust::media::Media::Still(i)) => println!(
            "PNG estático {}x{}, {} bytes RGBA",
            i.width,
            i.height,
            i.rgba.len()
        ),
        Ok(gsr_overlay_rust::media::Media::Animated(a)) => println!(
            "GIF {}x{}, {} frames, ciclo {} ms, reproducciones {:?}, caché {} bytes, temporales {} bytes",
            a.width,
            a.height,
            a.frames.len(),
            a.cycle_ms,
            a.plays,
            a.cache_bytes,
            a.temporary_bytes
        ),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
