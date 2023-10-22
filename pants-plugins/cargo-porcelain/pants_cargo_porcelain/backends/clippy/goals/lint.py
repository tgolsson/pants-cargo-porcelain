from __future__ import annotations

from dataclasses import dataclass

from pants.core.goals.lint import LintResult, LintTargetsRequest, Partitions
from pants.core.util_rules.partitions import Partition
from pants.core.util_rules.source_files import SourceFiles
from pants.engine.addresses import Address
from pants.engine.platform import Platform
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel

from pants_cargo_porcelain.backends.clippy.subsystem import ClippySubsystem
from pants_cargo_porcelain.subsystems import RustupTool
from pants_cargo_porcelain.target_types import CargoPackageNameField, CargoPackageSourcesField
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest


@dataclass(frozen=True)
class CargoClippyFieldSet(FieldSet):
    required_fields = (CargoPackageSourcesField, CargoPackageNameField)

    sources: CargoPackageSourcesField


class CargoClippyRequest(LintTargetsRequest):
    field_set_type = CargoClippyFieldSet
    tool_subsystem = ClippySubsystem


@dataclass(frozen=True)
class PackageMetadata:
    address: Address

    @property
    def description(self) -> None:
        return None


@rule
async def partition(
    request: CargoClippyRequest.PartitionRequest[CargoClippyFieldSet], subsystem: ClippySubsystem
) -> Partitions[CargoClippyFieldSet, PackageMetadata]:
    if subsystem.skip:
        return Partitions()

    partitions = []
    for field_set in request.field_sets:
        partitions.append(
            Partition(
                (field_set,),
                PackageMetadata(
                    address=field_set.address,
                ),
            )
        )

    return Partitions(partitions)


@rule(desc="Lint Cargo package", level=LogLevel.DEBUG)
async def run_cargo_lint(
    request: CargoClippyRequest.Batch[CargoClippyFieldSet, PackageMetadata],
    cargo_subsystem: ClippySubsystem,
    rustup_tool: RustupTool,
    clippy: ClippySubsystem,
    platform: Platform,
) -> LintResult:
    toolchain, source_files = await MultiGet(
        Get(
            RustToolchain,
            RustToolchainRequest("1.72.1", "x86_64-unknown-linux-gnu", ("cargo",)),
        ),
        Get(SourceFiles, CargoSourcesRequest(frozenset([request.elements[0].address]))),
    )

    cargo_toml_path = f"{request.partition_metadata.address.spec_path}/Cargo.toml"
    process_result = await Get(
        FallibleProcessResult,
        CargoProcessRequest(
            toolchain,
            (
                "clippy",
                "-q",
                "--locked",
                "--color=always",
                f"--manifest-path={cargo_toml_path}",
                *clippy.args,
            ),
            source_files.snapshot.digest,
        ),
    )

    return LintResult.create(request, process_result)


def rules():
    return [
        *collect_rules(),
        *CargoClippyRequest.rules(),
    ]
