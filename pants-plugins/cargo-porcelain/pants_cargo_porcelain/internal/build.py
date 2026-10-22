"""`cargo build` of one binary."""

from __future__ import annotations

from dataclasses import dataclass

from pants.engine.addresses import Address
from pants.engine.fs import Digest, RemovePrefix
from pants.engine.intrinsics import remove_prefix
from pants.engine.platform import Platform
from pants.engine.process import fallible_to_exec_result_or_raise
from pants.engine.rules import collect_rules, implicitly, rule

from pants_cargo_porcelain.util_rules.cargo import TARGET_DIR, CargoProcessRequest, manifest_path
from pants_cargo_porcelain.util_rules.rustup import (
    RustToolchainRequest,
    RustVersion,
    install_rust_toolchain,
    platform_triple,
)
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest, cargo_sources


@dataclass(frozen=True)
class CargoBinaryRequest:
    address: Address
    binary_name: str
    release: bool


@dataclass(frozen=True)
class CargoBinary:
    """The built binary, alone at the root of the digest."""

    digest: Digest
    name: str


@rule(desc="Build a cargo binary")
async def build_cargo_binary(
    request: CargoBinaryRequest, version: RustVersion, platform: Platform
) -> CargoBinary:
    toolchain = await install_rust_toolchain(
        RustToolchainRequest(version.version, platform_triple(platform), version.components)
    )
    sources = await cargo_sources(
        CargoSourcesRequest(frozenset([request.address]), include_packages=True)
    )
    profile = "release" if request.release else "debug"
    result = await fallible_to_exec_result_or_raise(
        **implicitly(
            CargoProcessRequest(
                toolchain,
                (
                    "build",
                    "--locked",
                    f"--manifest-path={manifest_path(request.address.spec_path)}",
                    f"--bin={request.binary_name}",
                    *(("--release",) if request.release else ()),
                ),
                description=f"cargo build {request.address}",
                digest=sources.digest,
                output_files=(f"{TARGET_DIR}/{profile}/{request.binary_name}",),
                env=sources.env,
            )
        )
    )
    digest = await remove_prefix(RemovePrefix(result.output_digest, f"{TARGET_DIR}/{profile}"))
    return CargoBinary(digest, request.binary_name)


def rules():
    return collect_rules()
