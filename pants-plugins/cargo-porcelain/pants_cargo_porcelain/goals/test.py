from __future__ import annotations

from dataclasses import dataclass

from pants.core.goals.test import ShowOutput, TestRequest, TestResult
from pants.core.util_rules.environments import EnvironmentField
from pants.core.util_rules.partitions import Partition, PartitionerType, Partitions
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.internals.selectors import Get
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import RustSubsystem
from pants_cargo_porcelain.target_types import (
    CargoBinaryNameField,
    CargoLibraryNameField,
    CargoPackageSourcesField,
    CargoTestNameField,
)
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


@dataclass(frozen=True)
class CargoTestFieldSet(FieldSet):
    required_fields = (CargoPackageSourcesField,)

    library_name: CargoLibraryNameField
    binary_name: CargoBinaryNameField
    test_name: CargoTestNameField

    sources: CargoPackageSourcesField
    environment: EnvironmentField


@dataclass(frozen=True)
class CargoTestRequest(TestRequest):
    field_set_type = CargoTestFieldSet
    tool_subsystem = RustSubsystem


@dataclass(frozen=True)
class PackageMetadata:
    address: Address

    @property
    def description(self) -> None:
        return None


@rule(desc="Test Cargo package", level=LogLevel.DEBUG)
async def cargo_test(
    request: CargoTestRequest.Batch[CargoTestFieldSet, PackageMetadata]
) -> TestResult:
    toolchain = await Get(
        RustToolchain,
        RustToolchainRequest("1.72.1", "x86_64-unknown-linux-gnu", ("cargo",)),
    )

    source_files = await Get(
        SourceFiles,
        SourceFilesRequest([request.elements[0].sources]),
    )

    cargo_toml_path = f"{request.elements[0].address.spec_path}/Cargo.toml"

    if request.elements[0].library_name.value:
        process_result = await Get(
            FallibleProcessResult,
            CargoProcessRequest(
                toolchain,
                ("test", f"--manifest-path={cargo_toml_path}", "--lib"),
                source_files.snapshot.digest,
            ),
        )

    elif request.elements[0].test_name.value:
        process_result = await Get(
            FallibleProcessResult,
            CargoProcessRequest(
                toolchain,
                (
                    "test",
                    f"--manifest-path={cargo_toml_path}",
                    f"--test={request.elements[0].test_name.value}",
                ),
                source_files.snapshot.digest,
            ),
        )
    elif request.elements[0].binary_name.value:
        process_result = await Get(
            FallibleProcessResult,
            CargoProcessRequest(
                toolchain,
                (
                    "test",
                    f"--manifest-path={cargo_toml_path}",
                    f"--bin={request.elements[0].binary_name.value}",
                ),
                source_files.snapshot.digest,
            ),
        )
    else:
        return TestResult.no_tests_found(request, ShowOutput.FAILED)

    return TestResult.from_fallible_process_result(
        process_result, request.elements[0].address, ShowOutput.FAILED
    )


def rules():
    return [
        *collect_rules(),
        *CargoTestRequest.rules(),
    ]
