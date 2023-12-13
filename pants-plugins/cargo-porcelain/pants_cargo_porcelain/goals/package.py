from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from pants.core.goals.package import (
    BuiltPackage,
    BuiltPackageArtifact,
    OutputPathField,
    PackageFieldSet,
)
from pants.core.goals.run import RunFieldSet, RunInSandboxBehavior
from pants.core.util_rules.environments import EnvironmentField
from pants.engine.fs import AddPrefix, Digest, RemovePrefix
from pants.engine.internals.selectors import Get
from pants.engine.rules import collect_rules, rule
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pants_cargo_porcelain.internal.build import (
    CargoBinary,
    CargoBinaryRequest,
    CargoLibrary,
    CargoLibraryRequest,
)
from pants_cargo_porcelain.subsystems import RustSubsystem
from pants_cargo_porcelain.target_types import (
    CargoBinaryNameField,
    CargoLibraryNameField,
    CargoPackageSourcesField,
)


@dataclass(frozen=True)
class CargoBinaryFieldSet(PackageFieldSet, RunFieldSet):
    required_fields = (OutputPathField, CargoBinaryNameField)
    run_in_sandbox_behavior = RunInSandboxBehavior.RUN_REQUEST_HERMETIC

    binary_name: CargoBinaryNameField
    library_name: CargoLibraryNameField
    sources: CargoPackageSourcesField
    output_path: OutputPathField
    environment: EnvironmentField


@dataclass(frozen=True)
class CargoLibraryFieldSet(PackageFieldSet, RunFieldSet):
    required_fields = (OutputPathField, CargoLibraryNameField)
    run_in_sandbox_behavior = RunInSandboxBehavior.RUN_REQUEST_HERMETIC

    binary_name: CargoBinaryNameField
    library_name: CargoLibraryNameField
    sources: CargoPackageSourcesField
    output_path: OutputPathField
    environment: EnvironmentField


@dataclass(frozen=True)
class CargoArtifactRequest:
    address: Address
    binary_name: CargoBinaryNameField
    library_name: CargoLibraryNameField
    sources: CargoPackageSourcesField
    output_path: OutputPathField
    environment: EnvironmentField


@rule(desc="Package Cargo artifact", level=LogLevel.DEBUG)
async def package_cargo_artifact(
    field_set: CargoArtifactRequest,
    rust: RustSubsystem,
) -> BuiltPackage:
    output_filename = PurePath(field_set.output_path.value_or_default(file_ending=None))
    if field_set.binary_name:
        artifact = await Get(
            CargoBinary,
            CargoBinaryRequest(field_set.address, field_set.sources, field_set.binary_name.value),
        )
    else:
        artifact = await Get(
            CargoLibrary,
            CargoLibraryRequest(field_set.address, field_set.sources, field_set.library_name.value),
        )
    build_level = "debug"
    if rust.release:
        build_level = "release"

    removed_prefix = await Get(
        Digest,
        RemovePrefix(
            artifact.digest, f".cargo-target-cache/{field_set.address.spec_path}/{build_level}"
        ),
    )

    renamed_output_digest = await Get(
        Digest, AddPrefix(removed_prefix, str(output_filename.parent))
    )

    artifact = BuiltPackageArtifact(relpath=str(output_filename))
    return BuiltPackage(renamed_output_digest, (artifact,))


@rule(desc="Package Cargo binary", level=LogLevel.DEBUG)
async def package_cargo_binary(
    field_set: CargoBinaryFieldSet,
) -> BuiltPackage:
    return await Get(
        BuiltPackage,
        CargoArtifactRequest(
            address=field_set.address,
            binary_name=field_set.binary_name.value,
            library_name=None,
            sources=field_set.sources,
            output_path=field_set.output_path,
            environment=field_set.environment,
        ),
    )


@rule(desc="Package Cargo library")
async def package_cargo_library(
    field_set: CargoLibraryFieldSet,
) -> BuiltPackage:
    return await Get(
        BuiltPackage,
        CargoArtifactRequest(
            address=field_set.address,
            binary_name=None,
            library_name=field_set.library_name,
            sources=field_set.sources,
            output_path=field_set.output_path,
            environment=field_set.environment,
        ),
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PackageFieldSet, CargoBinaryFieldSet),
        UnionRule(PackageFieldSet, CargoLibraryFieldSet),
    ]
