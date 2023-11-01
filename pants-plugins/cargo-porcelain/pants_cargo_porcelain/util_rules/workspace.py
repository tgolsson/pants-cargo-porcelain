from dataclasses import dataclass

import toml
from pants.build_graph.address import Address
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import DigestContents, DigestSubset, PathGlobs, Paths
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import AllTargets, MultipleSourcesField, Target
from pants.util.frozendict import FrozenDict

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


@dataclass(frozen=True)
class CargoPackageMapping:
    workspace_to_packages: FrozenDict[Address, frozenset[Address]]
    loose_packages: frozenset


@dataclass(frozen=True)
class CargoToml:
    contents: str


@dataclass(frozen=True)
class CargoTomlRequest:
    sources: MultipleSourcesField


@rule(desc="Load Cargo.toml for Cargo target")
async def load_cargo_toml(request: CargoTomlRequest) -> CargoToml:
    files = await Get(
        SourceFiles,
        SourceFilesRequest(
            [request.sources],
        ),
    )

    print(files)
    digest_contents = await Get(
        DigestContents, DigestSubset(files.snapshot.digest, PathGlobs(["**/Cargo.toml"]))
    )

    print(digest_contents)
    return CargoToml(digest_contents[0].content)


@rule(desc="Assign packages to workspaces")
async def assign_packages_to_workspaces(all_cargo_targets: AllCargoTargets) -> CargoPackageMapping:
    workspace_cargo_toml = await MultiGet(
        Get(CargoToml, CargoTomlRequest(workspace[CargoWorkspaceSourcesField]))
        for workspace in all_cargo_targets.workspaces
    )

    for ws, cargo_content in zip(all_cargo_targets.workspaces, workspace_cargo_toml):
        toml_data = toml.loads(cargo_content.contents.decode("utf-8"))

        members = toml_data["workspace"].get("members", [])

    return CargoPackageMapping({}, {})


def rules():
    return [
        *collect_rules(),
    ]
