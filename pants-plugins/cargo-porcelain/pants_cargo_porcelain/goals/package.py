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
from pants.engine.fs import AddPrefix, Digest
from pants.engine.internals.selectors import Get
from pants.engine.rules import collect_rules, rule
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pants_cargo_porcelain.internal.build import CargoBinary, CargoBinaryRequest
from pants_cargo_porcelain.subsystems import RustSubsystem
from pants_cargo_porcelain.target_types import CargoBinaryNameField, CargoPackageSourcesField


@dataclass(frozen=True)
class CargoBinaryFieldSet(PackageFieldSet, RunFieldSet):
    required_fields = (OutputPathField, CargoBinaryNameField)
    run_in_sandbox_behavior = RunInSandboxBehavior.RUN_REQUEST_HERMETIC

    binary_name: CargoBinaryNameField
    sources: CargoPackageSourcesField
    output_path: OutputPathField
    environment: EnvironmentField


@rule(desc="Package Cargo binary", level=LogLevel.DEBUG)
async def package_cargo_binary(
    field_set: CargoBinaryFieldSet,
    rust: RustSubsystem,
) -> BuiltPackage:
    output_filename = PurePath(field_set.output_path.value_or_default(file_ending=None))
    binary = await Get(
        CargoBinary,
        CargoBinaryRequest(field_set.address, field_set.sources, field_set.binary_name.value),
    )

    renamed_output_digest = await Get(Digest, AddPrefix(binary.digest, str(output_filename.parent)))

    artifact = BuiltPackageArtifact(relpath=str(output_filename))
    return BuiltPackage(renamed_output_digest, (artifact,))


def rules():
    return [*collect_rules(), UnionRule(PackageFieldSet, CargoBinaryFieldSet)]
