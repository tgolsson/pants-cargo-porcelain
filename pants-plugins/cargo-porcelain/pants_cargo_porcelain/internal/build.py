from dataclasses import dataclass

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.fs import Digest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule

from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import CargoPackageSourcesField
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


@dataclass(frozen=True)
class CargoBinary:
    digest: Digest


@dataclass(frozen=True)
class CargoBinaryRequest:
    address: Address
    sources: CargoPackageSourcesField
    binary_name: str

    release_mode: bool = False


def platform_to_target(platform: Platform):
    if platform == Platform.linux_x86_64:
        return "x86_64-unknown-linux-gnu"
    elif platform == Platform.linux_arm64:
        return "aarch64-unknown-linux-gnu"
    elif platform == Platform.macos_x86_64:
        return "x86_64-apple-darwin"
    elif platform == Platform.macos_arm64:
        return "aarch64-apple-darwin"
    else:
        raise Exception("Unknown platform")


@rule
async def build_cargo_binary(
    req: CargoBinaryRequest, rust: RustSubsystem, rustup: RustupTool, platform: Platform
) -> CargoBinary:
    source_files, toolchain = await MultiGet(
        Get(
            SourceFiles,
            SourceFilesRequest([req.sources]),
        ),
        Get(
            RustToolchain,
            RustToolchainRequest(
                rustup.rust_version, platform_to_target(platform), ("cargo", "rustfmt")
            ),
        ),
    )

    process_result = await Get(
        ProcessResult,
        CargoProcessRequest(
            toolchain,
            (
                "build",
                f"--manifest-path={req.address.spec_path}/Cargo.toml",
                "--locked",
                f"--bin={req.binary_name}",
            ),
            source_files.snapshot.digest,
            output_files=(f"{{cache_path}}/debug/{req.binary_name}",),
            cache_path=req.address.spec_path,
        ),
    )

    return CargoBinary(process_result.output_digest)


def rules():
    return collect_rules()
