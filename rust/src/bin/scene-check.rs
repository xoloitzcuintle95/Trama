use gsr_overlay_rust::scene::LoadedScene;
fn main() {
    let result = std::env::args_os()
        .nth(1)
        .ok_or("Uso: scene-check escena.json".to_string())
        .and_then(|path| LoadedScene::from_path(std::path::Path::new(&path)));
    match result {
        Ok(scene) => println!("{}", scene.summary()),
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    }
}
