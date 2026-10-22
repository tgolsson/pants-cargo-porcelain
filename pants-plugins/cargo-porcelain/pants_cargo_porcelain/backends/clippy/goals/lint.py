"""`pants lint` with clippy: one `cargo clippy` per workspace (or loose package)."""

from __future__ import annotations

from dataclasses import dataclass

from pants.core.environments.target_types import EnvironmentField
from pants.core.goals.lint import LintResult, LintTargetsRequest
from pants.core.util_rules.partitions import Partition, Partitions
from pants.engine.intrinsics import execute_process
from pants.engine.platform import Platform
from pants.engine.rules import collect_rules, implicitly, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel

from pants_cargo_porcelain.backends.clippy.subsystem import ClippySubsystem
from pants_cargo_porcelain.goals.fmt import RootMetadata, root_of
from pants_cargo_porcelain.target_types import CargoPackageNameField, _CargoPackageMarker
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest, manifest_path
from pants_cargo_porcelain.util_rules.rustup import (
    RustToolchainRequest,
    RustVersion,
    install_rust_toolchain,
    platform_triple,
)
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest, cargo_sources
from pants_cargo_porcelain.util_rules.workspace import CargoPackageMapping


@dataclass(frozen=True)
class CargoClippyFieldSet(FieldSet):
    required_fields = (CargoPackageNameField, _CargoPackageMarker)

    environment: EnvironmentField


class CargoClippyRequest(LintTargetsRequest):
    field_set_type = CargoClippyFieldSet
    tool_subsystem = ClippySubsystem


@rule
async def partition_clippy(
    request: CargoClippyRequest.PartitionRequest[CargoClippyFieldSet],
    clippy: ClippySubsystem,
    mapping: CargoPackageMapping,
) -> Partitions[CargoClippyFieldSet, RootMetadata]:
    if clippy.skip:
        return Partitions()
    by_root: dict[RootMetadata, list[CargoClippyFieldSet]] = {}
    for field_set in request.field_sets:
        by_root.setdefault(root_of(mapping, field_set.address), []).append(field_set)
    return Partitions(Partition(tuple(fss), root) for root, fss in by_root.items())


@rule(desc="Lint with clippy", level=LogLevel.DEBUG)
async def run_clippy(
    request: CargoClippyRequest.Batch[CargoClippyFieldSet, RootMetadata],
    clippy: ClippySubsystem,
    version: RustVersion,
    platform: Platform,
) -> LintResult:
    root = request.partition_metadata
    toolchain = await install_rust_toolchain(
        RustToolchainRequest(version.version, platform_triple(platform), version.components)
    )
    sources = await cargo_sources(
        CargoSourcesRequest(frozenset([root.root]), include_packages=True)
    )
    result = await execute_process(
        **implicitly(
            CargoProcessRequest(
                toolchain,
                (
                    "clippy",
                    "--locked",
                    f"--manifest-path={manifest_path(root.root.spec_path)}",
                    *(("--workspace",) if root.workspace else ()),
                    *clippy.args,
                ),
                description=f"cargo clippy {root.root}",
                digest=sources.digest,
                env=sources.env,
                level=LogLevel.INFO,
            )
        )
    )
    return LintResult.create(request, result)


def rules():
    return [*collect_rules(), *CargoClippyRequest.rules()]
