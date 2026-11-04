# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

- Targets Pants 2.33 on CPython 3.14, with the rules written in the call-by-name API; Pants
  2.24 and Python 3.9 are no longer supported.
- `cargo_workspace`, the root of a workspace, whose members are found through the manifest's
  `members` globs less `exclude`; `cargo_package` generates `#package`, `#library`, one
  `cargo_binary` per `[[bin]]` and one `cargo_test` per `[[test]]` from its own manifest.
  `dependencies` stages `files`, `resources` and packageable targets of other backends in the
  sandbox; `env` sets variables for every cargo process holding the package.
- Toolchain: `[rustup]` pins rustup-init and installs the toolchain of `[rustup].rust_version`
  or the `rust-toolchain.toml` channel into named caches, nothing from the host's `~/.rustup`
  or `~/.cargo`, and `RUSTUP_TOOLCHAIN` pins every cargo process to it, so subcommands run
  through rustup's proxies (`cargo clippy`) do not fall back to the cache's default toolchain;
  every cargo process gets a fresh `target/`, and `[kache]` caches compiled
  crates across sandboxes. `[sccache]` and `[binstall]` are gone.
- Platforms through pants-backend-platforms: a `cargo_package`'s `platforms` builds its binaries
  for the enabled `platform` targets under `dist/<platform>/`, and the platform's `cc_toolchain`
  from pants-backend-cc links and serves cc-rs. Both backends are dependencies, pinned to a
  pants-backends commit until they are released.
- `test` builds one `cargo test --no-run --workspace` per workspace and runs each executable as
  its own process; `package` and `run` build `--locked`; `fmt` and `lint` (clippy) run per
  workspace; `generate-lockfiles` runs `cargo update`.
- Sandboxes are narrower: other workspace members bring only their cargo sources, and run
  requests carry none.
- The workspace's own manifest is read, a manifest without a `[package]` is named, files with
  glob characters in their names are formatted, and rustup installs are locked within their
  process.
- The cargo-mtime and cargo-binstall tools went with sccache, as did the `toml` dependency.
- The distribution is now built by `pants package pants-plugins/cargo-porcelain:package`, and
  carries the Apache-2.0 license text, which the repository now has as `LICENSE-APACHE`.
