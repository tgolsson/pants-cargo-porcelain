from __future__ import annotations

from dataclasses import dataclass

from pants.core.util_rules.system_binaries import (
    SEARCH_PATHS,
    BinaryPath,
    BinaryPathRequest,
    BinaryPaths,
    BinaryPathTest,
    BinaryShims,
    BinaryShimsRequest,
)
from pants.engine.fs import EMPTY_DIGEST, Digest
from pants.engine.internals.selectors import Get
from pants.engine.process import Process
from pants.engine.rules import collect_rules, rule
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
    working_directory: str | None = None


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


@rule(level=LogLevel.DEBUG, desc="Determine candidate Cargo targets to create")
async def make_cargo_process(
    req: CargoProcessRequest,
    cc: CCBinary,
    ld: LDBinary,
) -> Process:
    binary_shims = await Get(
        BinaryShims,
        BinaryShimsRequest.for_binaries(
            "cc",
            "ld",
            rationale="rustc",
            search_path=SEARCH_PATHS,
        ),
    )

    return Process(
        argv=(f"{{chroot}}/{req.toolchain.cargo}", *req.command),
        input_digest=req.digest,
        description=f"Run {req.command} with {req.toolchain}",
        append_only_caches=BOTH_CACHES,
        output_files=req.output_files,
        immutable_input_digests=binary_shims.immutable_input_digests,
        level=LogLevel.DEBUG,
        env={
            "PATH": f"{{chroot}}/{req.toolchain.path}/bin:{binary_shims.path_component}",
            "RUSTUP_HOME": RUSTUP_NAMED_CACHE,
            "CARGO_HOME": CARGO_NAMED_CACHE,
            "RUSTFLAGS": f"-C linker={cc.path}",
        },
        working_directory=req.working_directory,
    )


def rules():
    return [
        *collect_rules(),
    ]
