![Pants](https://img.shields.io/badge/Pants-2.33.1-%2355acee)

# Cargo porcelain for Pants

A [Pants](https://www.pantsbuild.org) backend for Rust that wraps Cargo rather than replacing
it: Cargo keeps its package model, its lockfiles and its workspaces, and Pants adds target
addresses, caching, a hermetic toolchain and the usual goals on top. Work in progress; no
stability guarantees until it nears feature completeness.

## Targets

- `cargo_workspace`: the root of a Cargo workspace: `Cargo.toml`, `Cargo.lock`,
  `rust-toolchain.toml` and `.cargo/config.toml`. Members are found through the manifest's
  `members` and depend on it. Test executables and clippy run once per workspace.
- `cargo_package`: a package. `cargo metadata` on its manifest generates
  - `path:name#package` (`cargo_package_impl`): the sources and cargo dependencies, what
    `fmt` and `lint` act on;
  - `path:name#library` (`cargo_library`), one `cargo_binary` per `[[bin]]` named after it,
    one `cargo_test` per `[[test]]`: what `test` runs, and for binaries what `package` and
    `run` build.

  `dependencies` adds `files`/`resources` targets the build reads (`include_str!`, build
  script inputs) and packageable targets of other backends whose `package` output the build
  needs: they are built and staged in the sandbox at their package path for `package`,
  `run`, `test` and `lint` (not for `fmt` and `generate-lockfiles`). Their own dependencies
  are their backend's inputs and are not staged. `env` sets `KEY=VALUE` entries for every
  cargo process whose sandbox holds the package (its own, those of packages depending on it,
  and the per-workspace `test` build, `fmt` and `lint`), and for the test executables and
  `run` binaries those build; `{chroot}` is the sandbox root, so
  `env=["MYLIB_DIR={chroot}/build"]` points a build script at a staged library. `PATH`,
  `CARGO`, `CARGO_HOME`, `CARGO_TARGET_DIR`, `CARGO_INCREMENTAL`, `RUSTUP_HOME`,
  `RUSTC_WRAPPER`, `RUSTFLAGS` and `KACHE_*` are the backend's and rejected. `skip_tests` as
  usual; `output_path` is the directory under `dist/` (default `path.to.target/`), the file
  keeps the binary's name. A target with `test = false` in
  `Cargo.toml` gets `skip_tests`. A `[[bin]]` or `[[test]]` named `package` or `library`, or a
  bin and a test of the same name, is an error: rename it.

`path` dependencies between packages are inferred. `pants tailor` adds both target types.
Pants reads nothing `.gitignore` ignores, so a workspace's `.cargo/config.toml` must not be
(`!/.cargo/` after a `.cargo` rule).

## Toolchain

Nothing from the host's `~/.rustup` or `~/.cargo` is used. `[rustup]` pins rustup-init, which
installs the toolchain into a named cache shared by every sandbox. The version is
`[rustup].rust_version` or, unset, the `channel` of the `rust-toolchain.toml` at the build
root, and must be exact: it is part of every cache key. The components the file lists are
installed with it; `fmt` and `lint` add `rustfmt` and `clippy`.

Every cargo process runs in a fresh sandbox with its own `target/`, so cargo's own incremental
state never carries over. Instead, `[kache]` puts [kache](https://github.com/kunobi-ninja/kache)
in front of rustc: compiled crates are keyed by their inputs and kept in a named cache, and
unchanged crates are restored rather than rebuilt, across sandboxes and across packages of a
workspace. Local only, no daemon. `--remap-path-prefix` maps the sandbox root to a fixed
prefix so rustc's output does not depend on the sandbox path; this sets `RUSTFLAGS`, so a
`build.rustflags` in `.cargo/config.toml` is not read. Cargo's own `[target.<triple>]
linker` is.

## Goals

- `package`: `cargo build --locked --bin <name>` (`--release` with `[rust].release`), the
  binary at `dist/<path.to.target>/<name>` or under `output_path`.
- `run`: the packaged binary, in a sandbox with the build's sources and staged packages.
- `test`: one `cargo test --no-run --workspace` per workspace (or per package outside any),
  then one process per test executable, so each `cargo_library`, `cargo_binary` and
  `cargo_test` is its own cached test result. Doctests are not run. The executables run from
  the package directory with the sources at hand and `CARGO_MANIFEST_DIR` set to it, as
  `cargo test` does, but a path compiled in through `env!("CARGO_MANIFEST_DIR")` names the
  build sandbox, not the run sandbox. A target cargo builds no executable for (its
  `required-features` are off) is skipped with a warning.
- `fmt` / `lint`: `cargo fmt` (`[rust].skip`) and, with
  `pants_cargo_porcelain.backends.clippy`, `cargo clippy` (`[clippy].args`, `[clippy].skip`),
  once per workspace.
- `generate-lockfiles`: `cargo update`, never cached across runs; the resolve names are the workspace and package
  addresses (`pants generate-lockfiles --resolve=path:name#package`), and a member's name
  updates its workspace's `Cargo.lock`.

## Setup

```toml
[GLOBAL]
backend_packages = [
  "pants_cargo_porcelain",
  "pants_cargo_porcelain.backends.clippy",
]

[rustup]
rust_version = "1.97.0"  # or a rust-toolchain.toml at the build root

[clippy]
args = ["--", "-Dwarnings"]

[kache]
enabled = true  # the default; false runs rustc bare
```

Linux and macOS, host `cc`/binutils for linking. No cross-compilation yet.
