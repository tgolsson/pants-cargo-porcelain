from __future__ import annotations

from dataclasses import dataclass

from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.core.util_rules.environments import EnvironmentField
from pants.core.util_rules.partitions import Partition, PartitionerType, Partitions
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import RustSubsystem
from pants_cargo_porcelain.target_types import CargoPackageNameField, CargoPackageSourcesField
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest


@dataclass(frozen=True)
class CargoFmtFieldSet(FieldSet):
    required_fields = (CargoPackageSourcesField, CargoPackageNameField)

    sources: CargoPackageSourcesField
    environment: EnvironmentField


@dataclass(frozen=True)
class CargoFmtRequest(FmtTargetsRequest):
    field_set_type = CargoFmtFieldSet
    partitioner_type = PartitionerType.CUSTOM
    tool_subsystem = RustSubsystem


@dataclass(frozen=True)
class PackageMetadata:
    address: Address

    @property
    def description(self) -> None:
        return None


@rule
async def partition(
    request: CargoFmtRequest.PartitionRequest[CargoFmtFieldSet], subsystem: RustSubsystem
) -> Partitions[CargoFmtFieldSet, PackageMetadata]:
    if subsystem.skip:
        return Partitions()

    partitions = []
    for field_set in request.field_sets:
        source_files = await Get(
            SourceFiles,
            SourceFilesRequest([field_set.sources]),
        )

        partitions.append(
            Partition(
                frozenset([f for f in source_files.files if f.endswith("rs")]),
                PackageMetadata(
                    address=field_set.address,
                ),
            )
        )

    return Partitions(partitions)


@rule(desc="Format Cargo package", level=LogLevel.DEBUG)
async def cargo_fmt(request: CargoFmtRequest.Batch[CargoFmtFieldSet, PackageMetadata]) -> FmtResult:
    toolchain, source_files = await MultiGet(
        Get(
            RustToolchain,
            RustToolchainRequest("1.72.1", "x86_64-unknown-linux-gnu", ("cargo",)),
        ),
        Get(SourceFiles, CargoSourcesRequest(frozenset([request.partition_metadata.address]))),
    )

    cargo_toml_path = f"{request.partition_metadata.address.spec_path}/Cargo.toml"
    process_result = await Get(
        ProcessResult,
        CargoProcessRequest(
            toolchain,
            ("fmt", f"--manifest-path={cargo_toml_path}"),
            source_files.snapshot.digest,
            output_files=request.files,
        ),
    )

    return await FmtResult.create(request, process_result)


def rules():
    return [
        *collect_rules(),
        *CargoFmtRequest.rules(),
    ]
