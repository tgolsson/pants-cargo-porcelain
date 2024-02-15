from dataclasses import dataclass

from pants.core.util_rules.source_files import SourceFiles
from pants.engine.addresses import Address
from pants.engine.fs import Digest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.internal.platform import platform_to_target
from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import CargoPackageSourcesField
from pants_cargo_porcelain.tool import InstalledRustTool, RustToolRequest, Sccache
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest


@dataclass(frozen=True)
class CargoBinary:
    digest: Digest


@dataclass(frozen=True)
class CargoBinaryRequest:
    address: Address
    sources: CargoPackageSourcesField
    binary_name: str

    release_mode: bool = False


@rule
async def build_cargo_binary(
    req: CargoBinaryRequest,
    rust: RustSubsystem,
    rustup: RustupTool,
    sccache: Sccache,
    platform: Platform,
) -> CargoBinary:
    immutable_input_digests = {}
    env = {}
    extra_args = []
    append_only_caches = {}
    source_files, toolchain = await MultiGet(
        Get(
            SourceFiles,
            CargoSourcesRequest(
                frozenset([req.address]),
            ),
        ),
        Get(
            RustToolchain,
            RustToolchainRequest(
                rustup.rust_version, platform_to_target(platform), ("cargo", "rustfmt")
            ),
        ),
    )

    if sccache.enabled:
        sccache_tool = await Get(InstalledRustTool, RustToolRequest, sccache.as_tool_request())

        immutable_input_digests[".sccache"] = sccache_tool.digest
        env["RUSTC_WRAPPER"] = f"{{chroot}}/.sccache/sccache"
        append_only_caches["sccache"] = ".sccache-cache"

    if rust.release:
        extra_args.append("--release")

    build_level = "debug"
    if rust.release:
        build_level = "release"

    process_result = await Get(
        ProcessResult,
        CargoProcessRequest(
            toolchain,
            (
                "build",
                *extra_args,
                f"--manifest-path={req.address.spec_path}/Cargo.toml",
                "--locked",
                f"--bin={req.binary_name}",
            ),
            source_files.snapshot.digest,
            output_files=(f"{{cache_path}}/{build_level}/{req.binary_name}",),
            cache_path=req.address.spec_path,
            immutable_input_digests=FrozenDict(immutable_input_digests),
            env=FrozenDict(env),
            append_only_caches=FrozenDict(append_only_caches),
        ),
    )

    return CargoBinary(process_result.output_digest)


def rules():
    return collect_rules()
