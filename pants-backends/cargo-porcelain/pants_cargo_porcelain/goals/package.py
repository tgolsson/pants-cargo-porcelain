from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath

from pants.core.cargoals.package import (
    BuiltPackage,
    BuiltPackageArtifact,
    OutputPathField,
    PackageFieldSet,
)
from pants.core.cargoals.run import RunFieldSet, RunInSandboxBehavior
from pants.core.util_rules.environments import EnvironmentField
from pants.engine.fs import AddPrefix, Digest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.rules import collect_rules, rule
from pants.engine.unions import UnionRule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel

from pants_cargo_porcelain.target_types import CargoPackageSourcesField, CargoPackageTarget
from pants_cargo_porcelain.util_rules.binary import (
    CargoBinaryMainPackage,
    CargoBinaryMainPackageRequest,
)
from pants_cargo_porcelain.util_rules.build_opts import (
    CargoBuildOptions,
    CargoBuildOptionsFromTargetRequest,
)

# from pants_cargo_porcelain.util_rules.build_pkg import BuiltCargoPackage
# from pants_cargo_porcelain.util_rules.build_pkg_target import BuildCargoPackageTargetRequest
# from pants_cargo_porcelain.util_rules.cargo_mod import CargoModInfo, CargoModInfoRequest
# from pants_cargo_porcelain.util_rules.first_party_pkg import (
#     FallibleFirstPartyPkgAnalysis,
#     FirstPartyPkgAnalysisRequest,
# )
# from pants_cargo_porcelain.util_rules.link import LinkCargoBinaryRequest, LinkedCargoBinary
# from pants_cargo_porcelain.util_rules.third_party_pkg import (
#     ThirdPartyPkgAnalysis,
#     ThirdPartyPkgAnalysisRequest,
# )


@dataclass(frozen=True)
class CargoBinaryFieldSet(PackageFieldSet, RunFieldSet):
    required_fields = (CargoPackageSourcesField,)
    run_in_sandbox_behavior = RunInSandboxBehavior.RUN_REQUEST_HERMETIC

    main: CargoBinaryMainPackageField
    output_path: OutputPathField
    environment: EnvironmentField


@rule(desc="Package Cargo binary", level=LogLevel.DEBUG)
async def package_cargo_binary(field_set: CargoBinaryFieldSet) -> BuiltPackage:
    output_filename = PurePath(field_set.output_path.value_or_default(file_ending=None))
    binary = await Get(
        CargoBinary,
        CargoBinaryRequest(
            field_set.main,
        ),
    )

    renamed_output_digest = await Get(Digest, AddPrefix(binary.digest, str(output_filename.parent)))

    artifact = BuiltPackageArtifact(relpath=str(output_filename))
    return BuiltPackage(renamed_output_digest, (artifact,))


def rules():
    return [*collect_rules(), UnionRule(PackageFieldSet, CargoBinaryFieldSet)]
