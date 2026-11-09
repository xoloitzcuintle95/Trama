//! No unwind crosses C. Expected errors use Result; a panic disables that instance.
use std::{
    io::Write,
    panic::{AssertUnwindSafe, catch_unwind},
};

pub fn log(message: &str) {
    // Ignore I/O errors: stderr may have closed. Never install a global panic hook.
    let _ = writeln!(std::io::stderr().lock(), "gsr-rust: {message}");
}

pub fn guard<T>(fallback: T, action: impl FnOnce() -> T) -> T {
    match catch_unwind(AssertUnwindSafe(action)) {
        Ok(result) => result,
        Err(payload) => {
            // A foreign panic payload could itself panic when dropped. Leak only
            // this exceptional payload rather than starting another unwind at FFI.
            std::mem::forget(payload);
            log("panic contenido en la frontera C; instancia desactivada");
            fallback
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn contains_unwind_and_payload_with_panicking_drop() {
        struct BadDrop;
        impl Drop for BadDrop {
            fn drop(&mut self) {
                panic!("payload drop");
            }
        }
        assert!(!guard(false, || std::panic::panic_any(BadDrop)));
        assert!(guard(false, || true));
    }
}
