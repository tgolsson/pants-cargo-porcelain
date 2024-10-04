FROM rust:latest

# Install dependencies for cross-compiling
RUN apt-get update && apt-get install -y \
    gcc-aarch64-linux-gnu \
    libc6-dev-arm64-cross

# Install the ARM64 target for Rust
RUN rustup target add aarch64-unknown-linux-gnu

# Set environment variables for cross-compiling
ENV CC=aarch64-linux-gnu-gcc
ENV CXX=aarch64-linux-gnu-g++
ENV CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc

# Create a new directory for the project
WORKDIR /usr/src/

# Cache the dependencies
COPY examples/docker-cross-compile/Cargo.toml examples/docker-cross-compile/Cargo.lock ./

# Build only dependencies to cache them
RUN mkdir src && echo 'fn main() {}' > src/main.rs && cargo build --release --target=aarch64-unknown-linux-gnu && rm -rf src

CMD [ "cargo", "build",  "--release", "--target=aarch64-unknown-linux-gnu" ]
