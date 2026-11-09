use gsr_overlay_rust::abi::*;
use std::mem::{align_of, offset_of, size_of};
fn main() {
    println!("api {} {}", API_MAJOR, API_MINOR);
    println!(
        "draw {} {} {} {}",
        size_of::<DrawParams>(),
        align_of::<DrawParams>(),
        offset_of!(DrawParams, width),
        offset_of!(DrawParams, height)
    );
    println!(
        "init {} {} {} {} {} {} {}",
        size_of::<InitParams>(),
        align_of::<InitParams>(),
        offset_of!(InitParams, width),
        offset_of!(InitParams, height),
        offset_of!(InitParams, fps),
        offset_of!(InitParams, color_depth),
        offset_of!(InitParams, graphics_api)
    );
    println!(
        "return {} {} {} {} {} {} {} {}",
        size_of::<InitReturn>(),
        align_of::<InitReturn>(),
        offset_of!(InitReturn, name),
        offset_of!(InitReturn, version),
        offset_of!(InitReturn, userdata),
        offset_of!(InitReturn, draw),
        offset_of!(InitReturn, is_damaged),
        offset_of!(InitReturn, clear_damage)
    );
    println!(
        "primitives {} {} {} {}",
        size_of::<u32>(),
        size_of::<std::ffi::c_int>(),
        size_of::<bool>(),
        size_of::<Option<Draw>>()
    );
}
