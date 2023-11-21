from collections import defaultdict
from dataclasses import dataclass

from pants.core.goals.generate_lockfiles import (
    GenerateLockfile,
    GenerateLockfileResult,
    GenerateLockfilesSubsystem,
    KnownUserResolveNames,
    KnownUserResolveNamesRequest,
    RequestedUserResolveNames,
    UserGenerateLockfiles,
    WrappedGenerateLockfile,
)
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import AllTargets
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pants_cargo_porcelain.target_types import (
    CargoPackageSourcesField,
    CargoPackageTarget,
    CargoWorkspaceTarget,
)
from pants_cargo_porcelain.util_rules.workspace import (
    AllCargoTargets,
    CargoPackageMapping,
    assign_packages_to_workspaces,
)


class CargoLock(GenerateLockfilesSubsystem):
    name = "cargo-lock"
    help = "Update Cargo.lock files."


@dataclass(frozen=True)
class GenerateCargoLockfile(GenerateLockfile):
    sources: CargoPackageSourcesField


@rule(desc="Generate Cargo lockfile", level=LogLevel.DEBUG)
async def generate_lockfile(
    req: GenerateCargoLockfile,
) -> GenerateLockfileResult:
    pass


class RequestedCargoUserResolveNames(RequestedUserResolveNames):
    pass


class KnownCargoUserResolveNamesRequest(KnownUserResolveNamesRequest):
    pass


@rule
async def determine_rust_user_resolves(
    _: KnownCargoUserResolveNamesRequest,
    cargo_targets: AllCargoTargets,
) -> KnownUserResolveNames:
    mapping = await assign_packages_to_workspaces(cargo_targets)

    names = [str(ws) for ws in mapping.workspace_to_packages]

    names.extend(str(p.address) for p in mapping.loose_packages)

    return KnownUserResolveNames(
        names=sorted(names),
        option_name=None,
        requested_resolve_names_cls=RequestedCargoUserResolveNames,
    )


@dataclass(frozen=True)
class GenerateCargoWorkspaceLockfileRequest:
    workspace: CargoWorkspaceTarget
    packages: tuple[CargoPackageTarget, ...]


class GenerateCargoPackageLockfileRequest:
    pass


@rule
async def generate_rust_workspace_lockfile(
    req: GenerateCargoWorkspaceLockfileRequest,
) -> GenerateCargoLockfile:
    pass


@rule
async def generate_rust_package_lockfile(
    req: GenerateCargoPackageLockfileRequest,
) -> GenerateCargoLockfile:
    pass


@rule
async def setup_user_lockfile_requests(
    requested: RequestedCargoUserResolveNames,
    all_targets: AllCargoTargets,
) -> UserGenerateLockfiles:
    print(requested)
    raise ValueError("foobar")

    # for tgt in sorted(all_targets, key=lambda t: t.address):
    #     if tgt.has_field(WorkspaceSources):
    #         workspaces.append(tgt)

    #     if tgt.has_field(CargoSources):
    #         packages.append(tgt)

    # workspace_to_packages = defaultdict(list)

    # solo_packages = []
    # for pkg in packages:
    #     for workspace in workspaces:
    #         print(f"Adding {pkg.address} to {workspace.get(WorkspacePackages).value}")
    #         if pkg.address in workspace.get(WorkspacePackages).value:
    #             workspace_to_packages[workspace].append(pkg)
    #             break
    #     else:
    #         solo_packages.append(pkg)

    # workspace_requests = [
    #     Get(
    #         GenerateCargoLockfile,
    #         GenerateCargoWorkspaceLockfileRequest(
    #             workspace=workspace,
    #             packages=tuple(workspace_to_packages[workspace]),
    #         ),
    #     )
    #     for resolve in requested
    # ]

    # package_requests = [
    #     Get(
    #         GenerateCargoLockfile,
    #         GenerateCargoPackageLockfileRequest(
    #             package=package,
    #         ),
    #     )
    #     for package in solo_packages
    # ]

    # rust_lockfile_requests = await MultiGet(
    #     *(workspace_requests + package_requests),
    # )
    return UserGenerateLockfiles(rust_lockfile_requests)


def rules():
    return (
        *collect_rules(),  #
        UnionRule(GenerateLockfile, GenerateCargoLockfile),
        UnionRule(KnownUserResolveNamesRequest, KnownCargoUserResolveNamesRequest),
        UnionRule(RequestedUserResolveNames, RequestedCargoUserResolveNames),
    )
