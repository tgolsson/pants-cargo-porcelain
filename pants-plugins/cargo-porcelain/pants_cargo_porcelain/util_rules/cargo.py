from __future__ import annotations

from dataclasses import dataclass

from pants.core.util_rules.system_binaries import (
    SEARCH_PATHS,
    BashBinary,
    BinaryPath,
    BinaryPathRequest,
    BinaryPaths,
    BinaryPathTest,
    BinaryShims,
    BinaryShimsRequest,
)
from pants.engine.fs import EMPTY_DIGEST, CreateDigest, Digest, FileContent, MergeDigests
from pants.engine.process import Process
from pants.engine.rules import Get, collect_rules, rule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel

from pants_cargo_porcelain.util_rules.rustup import (
    BOTH_CACHES,
    CARGO_NAMED_CACHE,
    RUSTUP_NAMED_CACHE,
    RustToolchain,
)


@dataclass(frozen=True)
class CargoProcessRequest:
    toolchain: RustToolchain
    command: str

    digest: Digest = EMPTY_DIGEST
    output_files: tuple[str, ...] = ()

    cache_path: str | None = None


@dataclass(frozen=True)
class CargoProcess:
    request: Process


class CCBinary(BinaryPath):
    """Path to the rustup binary used to select and gain access to Rust toolchains."""


@rule(desc="Finding the `zip` binary", level=LogLevel.DEBUG)
async def find_cc() -> CCBinary:
    request = BinaryPathRequest(
        binary_name="cc", search_path=SEARCH_PATHS, test=BinaryPathTest(args=["-v"])
    )
    paths = await Get(BinaryPaths, BinaryPathRequest, request)
    first_path = paths.first_path_or_raise(request, rationale="create `.zip` archives")
    return CCBinary(first_path.path, first_path.fingerprint)


class LDBinary(BinaryPath):
    """Path to the rustup binary used to select and gain access to Rust toolchains."""


@rule(desc="Finding the `zip` binary", level=LogLevel.DEBUG)
async def find_ld() -> LDBinary:
    request = BinaryPathRequest(
        binary_name="ld", search_path=SEARCH_PATHS, test=BinaryPathTest(args=["-v"])
    )
    paths = await Get(BinaryPaths, BinaryPathRequest, request)
    first_path = paths.first_path_or_raise(request, rationale="create `.zip` archives")
    return LDBinary(first_path.path, first_path.fingerprint)


class RealpathBinary(BinaryPath):
    pass


@rule(desc="Finding the `realpath` binary", level=LogLevel.DEBUG)
async def find_realpath() -> RealpathBinary:
    request = BinaryPathRequest(
        binary_name="realpath", search_path=SEARCH_PATHS, test=BinaryPathTest(args=["-v"])
    )
    paths = await Get(BinaryPaths, BinaryPathRequest, request)
    first_path = paths.first_path_or_raise(request, rationale="resolve named caches")
    return LDBinary(first_path.path, first_path.fingerprint)


@rule(level=LogLevel.DEBUG, desc="Determine candidate Cargo targets to create")
async def make_cargo_process(
    req: CargoProcessRequest,
    cc: CCBinary,
    ld: LDBinary,
    bash: BashBinary,
) -> Process:
    binary_shims = await Get(
        BinaryShims,
        BinaryShimsRequest.for_binaries(
            "cc",
            "ld",
            "realpath",
            rationale="rustc",
            search_path=SEARCH_PATHS,
        ),
    )

    append_only_caches = BOTH_CACHES
    env = {
        "PATH": f"{{chroot}}/{req.toolchain.path}/bin:{binary_shims.path_component}",
        "RUSTUP_HOME": RUSTUP_NAMED_CACHE,
        "CARGO_HOME": CARGO_NAMED_CACHE,
        "RUSTFLAGS": f"-C linker={cc.path}",
        #        "CARGO_LOG": "cargo::core::compiler::fingerprint=trace",
    }

    if req.cache_path:
        append_only_caches = FrozenDict({"ctc": ".cargo-target-cache", **append_only_caches})
        env["CARGO_TARGET_DIR"] = f".cargo-target-cache/{req.cache_path}"

    command = " ".join(req.command)
    script = f"""
    #!/usr/bin/env bash
    set -euo pipefail
    export CARGO_HOME=$(realpath .cargo)
    export RUSTUP_HOME=$(realpath .rustup)
    {req.toolchain.cargo} {command}
    """

    digest = await Get(Digest, CreateDigest([FileContent("run.sh", script.encode())]))
    merged_digest = await Get(Digest, MergeDigests([digest, req.digest]))
    return Process(
        argv=(bash.path, "run.sh"),
        input_digest=merged_digest,
        description=f"Run {req.command} with {req.toolchain}",
        append_only_caches=append_only_caches,
        output_files=req.output_files,
        immutable_input_digests=binary_shims.immutable_input_digests,
        level=LogLevel.DEBUG,
        env=env,
    )


def rules():
    return [
        *collect_rules(),
    ]
