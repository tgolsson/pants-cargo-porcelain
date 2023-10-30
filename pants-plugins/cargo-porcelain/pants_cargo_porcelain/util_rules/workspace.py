from dataclasses import dataclass

from pants.engine.rules import rule
from pants.engine.target import AllTargets, Target

from pants_cargo_porcelain.target_types import (
    CargoPackageSourcesField,
    CargoPackageTargetImpl,
    CargoWorkspaceSourcesField,
    CargoWorkspaceTarget,
)


@dataclass(frozen=True)
class AllCargoTargets:
    packages: tuple[CargoPackageTargetImpl, ...]
    workspaces: tuple[CargoWorkspaceTarget, ...]


@rule(desc="Find all cargo packages in project")
def find_all_cargo_targets(all_targets: AllTargets) -> AllCargoTargets:
    packages = []
    workspaces = []

    for target in all_targets:
        if target.has_field(CargoWorkspaceSourcesField):
            workspaces.append(target)

        if target.has_field(CargoPackageSourcesField):
            packages.append(target)

    return AllCargoTargets(
        packages=tuple(packages),
        workspaces=tuple(workspaces),
    )


def rules():
    return [
        find_all_cargo_targets,
    ]
