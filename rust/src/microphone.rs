//! Amplitude detector. No audio buffers or locks are used by the GL thread.
use std::{
    io::Read,
    process::{Child, Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

pub struct Gate {
    threshold: f32,
    release: Duration,
    last_loud: Option<Duration>,
}
impl Gate {
    pub fn new(threshold: f32, release_ms: u64) -> Self {
        Self {
            threshold,
            release: Duration::from_millis(release_ms),
            last_loud: None,
        }
    }
    pub fn update(&mut self, rms: f32, now: Duration) -> bool {
        if rms >= self.threshold {
            self.last_loud = Some(now);
        }
        self.last_loud
            .is_some_and(|last| now.saturating_sub(last) < self.release || rms >= self.threshold)
    }
}
pub struct Microphone {
    child: Child,
    worker: Option<JoinHandle<()>>,
    talking: Arc<AtomicBool>,
    failed: Arc<AtomicBool>,
}
impl Microphone {
    pub fn start(source: &str, threshold: f32, release_ms: u64) -> Result<Self, String> {
        let mut child = Command::new("parec")
            .args([
                "--raw",
                "--format=float32le",
                "--rate=16000",
                "--channels=1",
                "--latency-msec=30",
                "--device",
                source,
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .map_err(|e| format!("micrófono/parec: {e}"))?;
        let mut stdout = child.stdout.take().ok_or("parec sin stdout")?;
        let talking = Arc::new(AtomicBool::new(false));
        let failed = Arc::new(AtomicBool::new(false));
        let (out, err) = (talking.clone(), failed.clone());
        let worker = match thread::Builder::new()
            .name("avatar-level".into())
            .spawn(move || {
                let mut bytes = [0u8; 1280]; // 20 ms, mono f32; fixed allocation.
                let started = Instant::now();
                let mut gate = Gate::new(threshold, release_ms);
                while stdout.read_exact(&mut bytes).is_ok() {
                    let sum: f32 = bytes
                        .as_chunks::<4>()
                        .0
                        .iter()
                        .map(|b| {
                            let value = f32::from_le_bytes([b[0], b[1], b[2], b[3]]);
                            if value.is_finite() {
                                value.clamp(-1., 1.).powi(2)
                            } else {
                                0.
                            }
                        })
                        .sum();
                    out.store(
                        gate.update((sum / 320.).sqrt(), started.elapsed()),
                        Ordering::Relaxed,
                    );
                }
                out.store(false, Ordering::Relaxed);
                err.store(true, Ordering::Relaxed);
            }) {
            Ok(worker) => worker,
            Err(e) => {
                let _ = child.kill();
                let _ = child.wait();
                return Err(e.to_string());
            }
        };
        Ok(Self {
            child,
            worker: Some(worker),
            talking,
            failed,
        })
    }
    pub fn talking(&self) -> bool {
        self.talking.load(Ordering::Relaxed)
    }
    pub fn failed(&self) -> bool {
        self.failed.load(Ordering::Relaxed)
    }
}
impl Drop for Microphone {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        if let Some(worker) = self.worker.take() {
            let _ = worker.join();
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn threshold_and_release() {
        let mut gate = Gate::new(0.1, 200);
        assert!(!gate.update(0.01, Duration::ZERO));
        assert!(gate.update(0.2, Duration::from_millis(10)));
        assert!(gate.update(0., Duration::from_millis(209)));
        assert!(!gate.update(0., Duration::from_millis(210)));
        assert!(gate.update(0.1, Duration::from_millis(211)));
    }
}
