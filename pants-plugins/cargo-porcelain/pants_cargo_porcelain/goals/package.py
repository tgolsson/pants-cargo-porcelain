"""`pants package` of a `cargo_binary`: `dist/<path>/<binary name>`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from pants.core.environments.target_types import EnvironmentField
from pants.core.goals.package import (
    BuiltPackage,
    BuiltPackageArtifact,
    OutputPathField,
    PackageFieldSet,
)
from pants.core.goals.run import RunFieldSet, RunInSandboxBehavior
from pants.engine.fs import AddPrefix
from pants.engine.intrinsics import add_prefix
from pants.engine.rules import collect_rules, implicitly, rule
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pants_cargo_porcelain.internal.build import CargoBinaryRequest, build_cargo_binary
from pants_cargo_porcelain.subsystems import RustSubsystem
from pants_cargo_porcelain.target_types import (
    CargoArtifactKindField,
    CargoArtifactNameField,
    CargoEnvField,
)


@dataclass(frozen=True)
class CargoBinaryFieldSet(PackageFieldSet, RunFieldSet):
    required_fields = (CargoArtifactKindField, CargoArtifactNameField, OutputPathField)
    run_in_sandbox_behavior = RunInSandboxBehavior.RUN_REQUEST_HERMETIC

    kind: CargoArtifactKindField
    artifact_name: CargoArtifactNameField
    output_path: OutputPathField
    env: CargoEnvField
    environment: EnvironmentField

    @classmethod
    def opt_out(cls, tgt: Target) -> bool:
        return tgt[CargoArtifactKindField].value != "bin"


@rule(desc="Package a cargo binary", level=LogLevel.DEBUG)
async def package_cargo_binary(field_set: CargoBinaryFieldSet, rust: RustSubsystem) -> BuiltPackage:
    name = field_set.artifact_name.value
    binary = await build_cargo_binary(
        CargoBinaryRequest(field_set.address, name, rust.release),
        **implicitly(),
    )
    # `output_path` names the directory (unset, the default template's directory,
    # `path.to.target/`); the file keeps cargo's name for the binary.
    output_path = field_set.output_path
    path = PurePath(output_path.value_or_default(file_ending=None))
    directory = path.parent if output_path.value == output_path.default else path
    digest = await add_prefix(AddPrefix(binary.digest, str(directory)))
    return BuiltPackage(digest, (BuiltPackageArtifact(relpath=str(directory / name)),))


def rules():
    return [*collect_rules(), UnionRule(PackageFieldSet, CargoBinaryFieldSet)]
