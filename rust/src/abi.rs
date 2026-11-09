//! Layout mirror of upstream plugin/plugin.h, commit f97d1e3; checked against C.
//! Enums are c_int instead of Rust enums: invalid incoming values must be rejected,
//! not cause undefined behavior before validation. Caller owns all argument memory.
use std::ffi::{c_char, c_int, c_void};

pub const API_MAJOR: u32 = 0;
pub const API_MINOR: u32 = 1;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct DrawParams {
    pub width: u32,
    pub height: u32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct InitParams {
    pub width: u32,
    pub height: u32,
    pub fps: u32,
    pub color_depth: c_int,
    pub graphics_api: c_int,
}

pub type Draw = unsafe extern "C" fn(*const DrawParams, *mut c_void);
pub type Damaged = unsafe extern "C" fn(*mut c_void) -> bool;
pub type ClearDamage = unsafe extern "C" fn(*mut c_void);

#[repr(C)]
pub struct InitReturn {
    pub name: *const c_char,
    pub version: u32,
    pub userdata: *mut c_void,
    pub draw: Option<Draw>,
    pub is_damaged: Option<Damaged>,
    pub clear_damage: Option<ClearDamage>,
}

impl Default for InitReturn {
    fn default() -> Self {
        Self {
            name: std::ptr::null(),
            version: 0,
            userdata: std::ptr::null_mut(),
            draw: None,
            is_damaged: None,
            clear_damage: None,
        }
    }
}
