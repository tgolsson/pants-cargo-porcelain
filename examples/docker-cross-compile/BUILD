docker_image(
    name = "cross-compiler",
    dependencies = [":cargo-lock"],
    source = "Dockerfile",
    skip_push = True,
    repository = "example/rust-cross-compiler",
)

docker_environment(
    name = "cross-compiler-env",
    image = "example/rust-cross-compiler",
)

cargo_package(
    name="hello-cross",
    environment="cross-compiler",
)

files(
    name="cargo-lock",
    description="Cargo lock file",
    sources = ["Cargo.toml", "Cargo.lock"],
)
