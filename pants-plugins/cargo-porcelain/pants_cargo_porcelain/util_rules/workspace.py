"""Which packages belong to which workspace, from the workspace manifests' `members`."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass

from pants.base.specs import DirGlobSpec, RawSpecs
from pants.build_graph.address import Address
from pants.engine.addresses import Addresses
from pants.engine.fs import DigestSubset, PathGlobs
from pants.engine.internals.graph import hydrate_sources, resolve_targets
from pants.engine.internals.specs_rules import resolve_addresses_from_raw_specs
from pants.engine.intrinsics import digest_subset_to_digest, get_digest_contents
from pants.engine.rules import collect_rules, concurrently, implicitly, rule
from pants.engine.target import AllTargets, HydrateSourcesRequest, MultipleSourcesField
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.target_types import (
    CargoPackageTargetImpl,
    CargoWorkspaceSourcesField,
    CargoWorkspaceTarget,
    _CargoPackageMarker,
)


@dataclass(frozen=True)
class AllCargoTargets:
    packages: tuple[CargoPackageTargetImpl, ...]
    workspaces: tuple[CargoWorkspaceTarget, ...]


@rule(desc="Find all cargo packages and workspaces")
async def find_all_cargo_targets(all_targets: AllTargets) -> AllCargoTargets:
    packages = []
    workspaces = []
    for target in all_targets:
        if target.has_field(CargoWorkspaceSourcesField):
            workspaces.append(target)
        if target.has_field(_CargoPackageMarker):
            packages.append(target)
    return AllCargoTargets(packages=tuple(packages), workspaces=tuple(workspaces))


@dataclass(frozen=True)
class CargoToml:
    contents: str


@dataclass(frozen=True)
class CargoTomlRequest:
    sources: MultipleSourcesField


@rule(desc="Load a Cargo.toml")
async def load_cargo_toml(request: CargoTomlRequest) -> CargoToml:
    hydrated = await hydrate_sources(HydrateSourcesRequest(request.sources), **implicitly())
    manifest = await digest_subset_to_digest(
        DigestSubset(hydrated.snapshot.digest, PathGlobs(["**/Cargo.toml"]))
    )
    contents = await get_digest_contents(manifest)
    if not contents:
        raise ValueError(f"{request.sources.address}: no Cargo.toml among its sources")
    return CargoToml(contents[0].content.decode())


@dataclass(frozen=True)
class CargoWorkspaceMember:
    member_path: str
    package: CargoPackageTargetImpl


@dataclass(frozen=True)
class CargoPackageMapping:
    workspace_to_packages: FrozenDict[Address, frozenset[CargoWorkspaceMember]]
    loose_packages: frozenset[CargoPackageTargetImpl]

    def workspace_for(self, address: Address) -> Address | None:
        """The workspace a package (by its `cargo_package_impl` address) belongs to."""
        for workspace, members in self.workspace_to_packages.items():
            if any(address == m.package.address for m in members):
                return workspace
        return None


@rule(desc="Assign packages to workspaces")
async def assign_packages_to_workspaces(all_cargo_targets: AllCargoTargets) -> CargoPackageMapping:
    manifests = await concurrently(
        load_cargo_toml(CargoTomlRequest(workspace[CargoWorkspaceSourcesField]))
        for workspace in all_cargo_targets.workspaces
    )

    workspace_to_packages: dict[Address, frozenset[CargoWorkspaceMember]] = {}
    packages = set(all_cargo_targets.packages)
    for workspace, manifest in zip(all_cargo_targets.workspaces, manifests):
        data = tomllib.loads(manifest.contents)
        members = list(data.get("workspace", {}).get("members", []))
        if "package" in data:
            members.append(".")
        globs = [os.path.normpath(os.path.join(workspace.address.spec_path, m)) for m in members]

        address_sets = await concurrently(
            resolve_addresses_from_raw_specs(
                RawSpecs(
                    dir_globs=(DirGlobSpec(glob),),
                    description_of_origin=f"the members of {workspace.address}",
                )
            )
            for glob in globs
        )
        candidates = await concurrently(
            resolve_targets(**implicitly({addresses: Addresses})) for addresses in address_sets
        )

        found = []
        for member, targets in zip(members, candidates):
            package_targets = [t for t in targets if t.has_field(_CargoPackageMarker)]
            if len(package_targets) > 1:
                raise ValueError(
                    f"{workspace.address}: member `{member}` has more than one package target: "
                    f"{sorted(t.address for t in package_targets)}"
                )
            if not package_targets:
                continue
            packages -= set(package_targets)
            found.append(CargoWorkspaceMember(member_path=member, package=package_targets[0]))
        workspace_to_packages[workspace.address] = frozenset(found)

    return CargoPackageMapping(
        workspace_to_packages=FrozenDict(workspace_to_packages),
        loose_packages=frozenset(packages),
    )


def rules():
    return collect_rules()
