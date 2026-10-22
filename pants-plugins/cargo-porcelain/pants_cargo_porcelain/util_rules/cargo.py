"""One cargo invocation as a Pants `Process`.

Every process gets the installed toolchain and the rustup/cargo named caches, a fresh `target/`
inside the sandbox, and, unless disabled, kache as `RUSTC_WRAPPER`: cargo's own incremental
state cannot survive a fresh sandbox, so compiled crates are keyed by content and kept in a
named cache instead. The sandbox root is remapped to a fixed prefix in rustc's output, so
compiled artefacts and kache keys do not depend on the sandbox path."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass

from pants.core.util_rules.external_tool import download_external_tool
from pants.core.util_rules.system_binaries import (
    BashBinary,
    BinaryPathRequest,
    BinaryShimsRequest,
    SystemBinariesSubsystem,
    create_binary_shims,
    find_binary,
)
from pants.engine.fs import (
    EMPTY_DIGEST,
    CreateDigest,
    Digest,
    DigestSubset,
    FileContent,
    MergeDigests,
    PathGlobs,
)
from pants.engine.intrinsics import (
    create_digest,
    digest_subset_to_digest,
    get_digest_contents,
    merge_digests,
)
from pants.engine.platform import Platform
from pants.engine.process import Process, ProcessCacheScope
from pants.engine.rules import collect_rules, concurrently, implicitly, rule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import KacheTool
from pants_cargo_porcelain.util_rules.rustup import (
    CARGO_NAMED_CACHE,
    RUSTUP_NAMED_CACHE,
    TOOLCHAIN_CACHES,
    RustToolchain,
)

TARGET_DIR = "target"
KACHE_TOOL_DIR = ".kache"
KACHE_NAMED_CACHE = ".kache-data"
SANDBOX_PREFIX = "/pants-sandbox"
SCRIPT_NAME = "__cargo.sh"

# What rustc and build scripts reach through PATH. `cc` is rustc's default linker driver and
# what cc-rs runs; the binutils are what `cc` and build scripts call by name; `getconf` and
# (on Linux) `ldd` are how kache identifies the host libc for its cache key: without them
# every crate is "uncacheable".
_SHIMMED = ("cc", "ld", "ar", "as", "getconf")
_SHIMMED_LINUX = ("ldd",)
# Shimmed when the host has them: what `-sys` crates' build scripts look for.
_OPTIONAL = ("pkg-config",)

# What every cargo process sets itself (see `make_cargo_process`); a package's `env` may not.
_RESERVED_ENV = frozenset({
    "PATH",
    "CARGO",
    "CARGO_HOME",
    "CARGO_TARGET_DIR",
    "CARGO_INCREMENTAL",
    "RUSTUP_HOME",
    "RUSTC_WRAPPER",
    "RUSTFLAGS",
})


def is_reserved_env(key: str) -> bool:
    return key in _RESERVED_ENV or key.startswith("KACHE_")


async def config_linkers(digest: Digest) -> tuple[str, ...]:
    """The bare-name linkers the staged `.cargo/config.toml`s set per target (`linker =
    "gcc"`, `"x86_64-w64-mingw32-gcc"`): cargo passes them to rustc by name, so they must be
    on the sandbox PATH too."""
    contents = await get_digest_contents(
        await digest_subset_to_digest(DigestSubset(digest, PathGlobs(["**/.cargo/config.toml"])))
    )
    names = set()
    for file_content in contents:
        config = tomllib.loads(file_content.content.decode())
        for target in config.get("target", {}).values():
            linker = target.get("linker") if isinstance(target, dict) else None
            if isinstance(linker, str) and "/" not in linker:
                names.add(linker)
    return tuple(sorted(names))


def manifest_path(spec_path: str) -> str:
    """`<spec_path>/Cargo.toml`, or `Cargo.toml` for a target at the build root."""
    return os.path.join(spec_path, "Cargo.toml")


@dataclass(frozen=True)
class CargoProcessRequest:
    """`cargo <command>`; or, with `script`, a shell script that runs `$CARGO` itself (the
    test build needs to post-process cargo's output in the same sandbox)."""

    toolchain: RustToolchain
    command: tuple[str, ...]
    description: str
    digest: Digest = EMPTY_DIGEST
    output_files: tuple[str, ...] = ()
    output_directories: tuple[str, ...] = ()
    env: FrozenDict[str, str] = FrozenDict()
    script: str | None = None
    extra_shims: tuple[str, ...] = ()
    cache_scope: ProcessCacheScope = ProcessCacheScope.SUCCESSFUL
    level: LogLevel = LogLevel.DEBUG


@rule
async def make_cargo_process(
    request: CargoProcessRequest,
    kache: KacheTool,
    bash: BashBinary,
    platform: Platform,
    system_binaries: SystemBinariesSubsystem.EnvironmentAware,
) -> Process:
    shims = await create_binary_shims(
        BinaryShimsRequest.for_binaries(
            *_SHIMMED,
            *(_SHIMMED_LINUX if platform.value.startswith("linux") else ()),
            *request.extra_shims,
            rationale="run cargo",
            search_path=system_binaries.system_binary_paths,
        ),
        **implicitly(),
    )
    # Linkers from the cargo config and the optional tools are shimmed when the host has
    # them; a linker for another target (the MinGW one on a Mac) is simply absent, and only
    # a build for that target would miss it.
    optional_paths = await concurrently(
        find_binary(
            BinaryPathRequest(binary_name=name, search_path=system_binaries.system_binary_paths),
            **implicitly(),
        )
        for name in (*_OPTIONAL, *await config_linkers(request.digest))
    )
    linkers = await create_binary_shims(
        BinaryShimsRequest.for_paths(
            *(paths.first_path for paths in optional_paths if paths.first_path),
            rationale="run cargo",
        ),
        **implicitly(),
    )

    env = {
        "PATH": ":".join((
            f"{{chroot}}/{request.toolchain.bin_dir}",
            linkers.path_component,
            shims.path_component,
        )),
        "RUSTUP_HOME": f"{{chroot}}/{RUSTUP_NAMED_CACHE}",
        "CARGO_HOME": f"{{chroot}}/{CARGO_NAMED_CACHE}",
        "CARGO_TARGET_DIR": f"{{chroot}}/{TARGET_DIR}",
        # Incremental compilation only pays off when the target directory is reused.
        "CARGO_INCREMENTAL": "0",
        # Overrides `build.rustflags` from a `.cargo/config.toml`; see the README.
        "RUSTFLAGS": f"--remap-path-prefix={{chroot}}={SANDBOX_PREFIX}",
    }
    append_only_caches = dict(TOOLCHAIN_CACHES)
    immutable_input_digests = {
        **shims.immutable_input_digests,
        **linkers.immutable_input_digests,
    }

    if kache.enabled:
        tool = await download_external_tool(kache.get_request(platform))
        immutable_input_digests[KACHE_TOOL_DIR] = tool.digest
        append_only_caches["kache"] = KACHE_NAMED_CACHE
        env.update({
            "RUSTC_WRAPPER": f"{{chroot}}/{KACHE_TOOL_DIR}/kache",
            "KACHE_CACHE_DIR": f"{{chroot}}/{KACHE_NAMED_CACHE}",
            "KACHE_BASE_DIR": "{chroot}",
            "KACHE_MAX_SIZE": kache.cache_size,
            "KACHE_LOCAL_ONLY": "1",
        })

    env.update(request.env)

    cargo = f"{{chroot}}/{request.toolchain.cargo}"
    if request.script is None:
        argv: tuple[str, ...] = (cargo, *request.command)
        input_digest = request.digest
    else:
        env["CARGO"] = cargo
        script = await create_digest(
            CreateDigest([FileContent(SCRIPT_NAME, request.script.encode(), is_executable=True)])
        )
        input_digest = await merge_digests(MergeDigests([request.digest, script]))
        argv = (bash.path, SCRIPT_NAME, *request.command)

    return Process(
        argv=argv,
        input_digest=input_digest,
        description=request.description,
        level=request.level,
        env=env,
        append_only_caches=FrozenDict(append_only_caches),
        immutable_input_digests=FrozenDict(immutable_input_digests),
        output_files=request.output_files,
        output_directories=request.output_directories,
        cache_scope=request.cache_scope,
    )


def rules():
    return collect_rules()
