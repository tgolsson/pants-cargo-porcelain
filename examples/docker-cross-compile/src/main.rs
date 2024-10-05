#[cfg(not(all(target_arch = "aarch64", target_os = "linux")))]
compile_error!("This program only compiles for ARM64 running Linux (e.g., Raspberry Pi).");

fn main() {
    println!("Successfully compiled for ARM architecture.");
}
