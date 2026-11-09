"""Shared checks/arguments for single-element CLIs; never mutates GSR/C."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from measure import ROOT


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(media, require_c=False, *, require_gif=True, overrides=None, check_device=True):
    media = Path(media).resolve(strict=True)
    plugin = ROOT / "build/overlay-rust.so"
    manifest = ROOT / "build/overlay-rust.build.json"
    gsr = Path("/usr/local/bin/gpu-screen-recorder")
    checker = ROOT / "build/rust-target/release/element-check"
    if not all(p.is_file() for p in (plugin, manifest, gsr, checker)):
        raise ValueError("Falta GSR o el build Rust; ejecuta bash scripts/build-rust-overlay.sh")
    build = json.loads(manifest.read_text())
    if build["test_hooks"] or sha(plugin) != build["plugin_sha256"] or sha(gsr) != build["gsr_sha256"]:
        raise ValueError("GSR/plugin no coincide con el build/ABI verificado")
    if require_c:
        c_plugin = ROOT / "build/overlay.so"
        c_manifest = ROOT / "build/overlay-c.build.json"
        if not c_plugin.is_file() or not c_manifest.is_file():
            raise ValueError("Falta la referencia C; ejecuta bash scripts/build-overlay.sh")
        c_build = json.loads(c_manifest.read_text())
        if sha(c_plugin) != c_build["plugin_sha256"] or any(
                sha(ROOT/name) != digest for name,digest in c_build["sources"].items()):
            raise ValueError("La referencia C cambió; recompila con bash scripts/build-overlay.sh")
    environment = os.environ.copy()
    environment.update(GSR_RUST_IMAGE=str(media), GSR_OVERLAY_FILE=str(media))
    environment.pop("GSR_RUST_TEST_PANIC", None)
    environment.pop("GSR_RUST_SCENE", None)
    environment.update(overrides or {})
    check = subprocess.run([str(checker), str(media)], env=environment, capture_output=True, text=True)
    if check.returncode:
        raise ValueError(check.stderr.strip())
    checked = json.loads(check.stdout)
    info = checked["asset"]
    if require_gif and "cycle_ms" not in info:
        raise ValueError("Esta prueba requiere GIF animado; el PNG usa la validación estática")
    if require_c and (environment.get("GSR_OVERLAY_HEIGHT") is not None
                      or not checked["element"]["visible"] or not checked["element"]["keep_aspect"]
                      or checked["element"]["x"] < 0 or checked["element"]["y"] < 0):
        raise ValueError("La referencia C solo admite X/Y no negativos y ancho proporcional; usa esa configuración para comparar")
    if check_device and not Path("/dev/dri").is_dir():
        raise ValueError("Sin /dev/dri: ejecuta desde tu terminal COSMIC, sin sudo")
    metadata = {"media": str(media), "media_sha256": sha(media), "asset": info, "build": build,
                "kernel": platform.release(), "logical_cpus": os.cpu_count(),
                "os_release": Path("/etc/os-release").read_text(),
                "gsr_version": subprocess.check_output([str(gsr), "--version"], text=True).strip(),
                "element": checked["element"],
                "overlay_settings": {k: environment.get(k, default) for k, default in
                    (("GSR_OVERLAY_X", "32"), ("GSR_OVERLAY_Y", "32"), ("GSR_OVERLAY_WIDTH", None),
                     ("GSR_OVERLAY_HEIGHT", None), ("GSR_OVERLAY_KEEP_ASPECT", "true"), ("GSR_OVERLAY_VISIBLE", "true"))}}
    if require_c:
        metadata["c_plugin_sha256"] = sha(ROOT / "build/overlay.so")
    return gsr, plugin, environment, metadata


def command(gsr, video, plugin=None, audio=False):
    args = [str(gsr), "-w", "screen", "-f", "30", "-fm", "cfr", "-k", "h264",
            "-q", "very_high", "-encoder", "gpu", "-fallback-cpu-encoding", "no"]
    if plugin is not None:
        args += ["-p", str(plugin)]
    if audio:
        args += ["-a", "default_output"]
    return args + ["-o", str(video)]
