import logging
from dataclasses import dataclass

import toml
from pants.base.specs import DirGlobSpec, RawSpecs
from pants.build_graph.address import Address
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import DigestContents, DigestSubset, PathGlobs, Paths
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import AllTargets, MultipleSourcesField, Target, Targets, UnexpandedTargets
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.target_types import (
    CargoPackageNameField,
    CargoPackageSourcesField,
    CargoPackageTargetImpl,
    CargoWorkspaceSourcesField,
    CargoWorkspaceTarget,
    _CargoPackageMarker,
)

logger = logging.getLogger(__name__)


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

        if target.has_field(_CargoPackageMarker):
            packages.append(target)

    return AllCargoTargets(
        packages=tuple(packages),
        workspaces=tuple(workspaces),
    )


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

    digest_contents = await Get(
        DigestContents, DigestSubset(files.snapshot.digest, PathGlobs(["**/Cargo.toml"]))
    )

    return CargoToml(digest_contents[0].content)


@dataclass(frozen=True)
class CargoWorkspaceMember:
    member_path: str
    target: CargoPackageTargetImpl


@dataclass(frozen=True)
class CargoPackageMapping:
    workspace_to_packages: FrozenDict[Address, tuple[CargoWorkspaceMember, ...]]
    loose_packages: frozenset[CargoPackageTargetImpl]


@rule(desc="Assign packages to workspaces")
async def assign_packages_to_workspaces(
    all_cargo_targets: AllCargoTargets,
) -> CargoPackageMapping:
    workspace_cargo_toml = await MultiGet(
        Get(CargoToml, CargoTomlRequest(workspace[CargoWorkspaceSourcesField]))
        for workspace in all_cargo_targets.workspaces
    )

    workspace_to_packages = {}
    packages = set(all_cargo_targets.packages)
    for ws, cargo_content in zip(all_cargo_targets.workspaces, workspace_cargo_toml):
        toml_data = toml.loads(cargo_content.contents.decode("utf-8"))
        members = toml_data["workspace"].get("members", [])

        candidate_targets_per_member = await MultiGet(
            Get(
                Targets,
                RawSpecs(
                    dir_globs=(DirGlobSpec(f"{ws.address.spec_path}/{member}"),),
                    description_of_origin="Assigning packages to workspaces",
                ),
            )
            for member in members
        )

        workspace_members = []

        for member, member_targets in zip(members, candidate_targets_per_member):
            filtered_targets = [
                target for target in member_targets if target.has_field(_CargoPackageMarker)
            ]

            if len(filtered_targets) > 1:
                addresses = [t.address for t in filtered_targets]
                raise ValueError(
                    f"found two package targets in directory '{ws.address.spec_path}/{member}':"
                    f" {addresses}"
                )
            packages -= set(filtered_targets)

            workspace_members.append(
                CargoWorkspaceMember(
                    member_path=member,
                    target=filtered_targets[0],
                )
            )

        workspace_to_packages[ws.address] = frozenset(workspace_members)

    return CargoPackageMapping(
        workspace_to_packages=FrozenDict(workspace_to_packages), loose_packages=frozenset(packages)
    )


def rules():
    return [
        *collect_rules(),
    ]
