"""The Rust toolchain. rustup-init (a pinned download) installs an exact version into named
caches for `RUSTUP_HOME` and `CARGO_HOME`, shared by every sandbox and every session; nothing
from the host's `~/.rustup` or `~/.cargo` is used. The version comes from `[rustup].rust_version`
or the `rust-toolchain.toml` at the build root."""

from __future__ import annotations

import fcntl
import os
import re
import tomllib
from dataclasses import dataclass

from pants.base.build_environment import get_pants_cachedir
from pants.core.util_rules.external_tool import download_external_tool
from pants.engine.fs import PathGlobs
from pants.engine.intrinsics import get_digest_contents, path_globs_to_digest
from pants.engine.platform import Platform
from pants.engine.process import Process, ProcessCacheScope, fallible_to_exec_result_or_raise
from pants.engine.rules import collect_rules, implicitly, rule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import PLATFORM_TRIPLES, RustupTool

RUSTUP_NAMED_CACHE = ".rustup-home"
CARGO_NAMED_CACHE = ".cargo-home"
TOOLCHAIN_CACHES = FrozenDict({"rustup": RUSTUP_NAMED_CACHE, "cargo": CARGO_NAMED_CACHE})
TOOLCHAIN_FILE = "rust-toolchain.toml"

_EXACT_VERSION = re.compile(r"^\d+\.\d+\.\d+$|^nightly-\d{4}-\d{2}-\d{2}$")

_TOOLCHAIN_ENV = FrozenDict({
    "RUSTUP_HOME": f"{{chroot}}/{RUSTUP_NAMED_CACHE}",
    "CARGO_HOME": f"{{chroot}}/{CARGO_NAMED_CACHE}",
})


@dataclass(frozen=True)
class RustVersion:
    """The toolchain to install: an exact version and the components `rust-toolchain.toml`
    asks for, plus clippy and rustfmt for `lint` and `fmt`."""

    version: str
    components: tuple[str, ...]


@rule(desc="Determine the Rust version", level=LogLevel.DEBUG)
async def determine_rust_version(rustup: RustupTool) -> RustVersion:
    contents = await get_digest_contents(await path_globs_to_digest(PathGlobs([TOOLCHAIN_FILE])))
    channel: str | None = None
    components: tuple[str, ...] = ()
    if contents:
        toolchain = tomllib.loads(contents[0].content.decode()).get("toolchain", {})
        channel = toolchain.get("channel")
        components = tuple(toolchain.get("components", ()))

    # One toolchain request per session, whatever the goal: a second `rustup` run while a
    # cargo process executes a proxy in CARGO_HOME/bin fails with "text file busy".
    for component in ("clippy", "rustfmt"):
        if component not in components:
            components = (*components, component)

    version = rustup.rust_version or channel
    if not version:
        raise ValueError(
            f"No Rust version: set `[rustup].rust_version`, or add a `{TOOLCHAIN_FILE}` with "
            '`[toolchain] channel = "<version>"` at the build root.'
        )
    if not _EXACT_VERSION.match(version):
        raise ValueError(
            f"The Rust version must be exact (`1.97.0`, `nightly-2026-01-31`), not `{version}`: "
            "the toolchain is part of every cache key."
        )
    return RustVersion(version, components)


@dataclass(frozen=True)
class RustToolchainRequest:
    version: str
    target: str
    components: tuple[str, ...] = ()


@dataclass(frozen=True)
class RustToolchain:
    """An installed toolchain, as a sandbox-relative path into the rustup named cache."""

    path: str
    version: str
    target: str

    @property
    def bin_dir(self) -> str:
        return f"{self.path}/bin"

    @property
    def cargo(self) -> str:
        return f"{self.bin_dir}/cargo"


class _FileLock:
    """Serialises toolchain installs across Pants sessions: the engine runs one install per
    request per session, but two sessions on one machine share the named cache."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._fd = os.open(path, os.O_RDWR | os.O_CREAT)

    def __enter__(self):
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)


@rule(desc="Install the Rust toolchain", level=LogLevel.DEBUG)
async def install_rust_toolchain(
    request: RustToolchainRequest, rustup: RustupTool, platform: Platform
) -> RustToolchain:
    rustup_init = await download_external_tool(rustup.get_request(platform))
    components = [f"--component={c}" for c in request.components]

    # rustup is idempotent and quick when everything is installed, so these run once per
    # session rather than being memoised forever: a process-cache hit must not be able to
    # claim a toolchain that a wiped named cache no longer holds.
    with _FileLock(os.path.join(get_pants_cachedir(), "locks", "rustup")):
        await fallible_to_exec_result_or_raise(
            **implicitly(
                Process(
                    argv=[
                        rustup_init.exe,
                        "-y",
                        "--no-modify-path",
                        "--no-update-default-toolchain",
                        "--default-toolchain=none",
                        "--profile=minimal",
                    ],
                    input_digest=rustup_init.digest,
                    description="Install rustup",
                    level=LogLevel.DEBUG,
                    append_only_caches=TOOLCHAIN_CACHES,
                    env=_TOOLCHAIN_ENV,
                    cache_scope=ProcessCacheScope.PER_SESSION,
                )
            )
        )
        await fallible_to_exec_result_or_raise(
            **implicitly(
                Process(
                    argv=[
                        f"{{chroot}}/{CARGO_NAMED_CACHE}/bin/rustup",
                        "toolchain",
                        "install",
                        request.version,
                        "--no-self-update",
                        "--profile=minimal",
                        f"--target={request.target}",
                        *components,
                    ],
                    description=f"Install Rust {request.version} for {request.target}",
                    level=LogLevel.DEBUG,
                    append_only_caches=TOOLCHAIN_CACHES,
                    env=_TOOLCHAIN_ENV,
                    cache_scope=ProcessCacheScope.PER_SESSION,
                )
            )
        )

    host = platform_triple(platform)
    return RustToolchain(
        path=f"{RUSTUP_NAMED_CACHE}/toolchains/{request.version}-{host}",
        version=request.version,
        target=request.target,
    )


def platform_triple(platform: Platform) -> str:
    return PLATFORM_TRIPLES[platform.value]


def rules():
    return collect_rules()
