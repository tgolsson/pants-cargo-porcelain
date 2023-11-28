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
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import AllTargets
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pants_cargo_porcelain.internal.build import platform_to_target
from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import (
    CargoPackageSourcesField,
    CargoPackageTarget,
    CargoWorkspaceTarget,
)
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest
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


@dataclass(frozen=True)
class GenerateCargoPackageLockfileRequest:
    package: CargoPackageTarget


@rule
async def generate_rust_workspace_lockfile(
    req: GenerateCargoWorkspaceLockfileRequest,
) -> GenerateCargoLockfile:
    pass


@rule
async def generate_rust_package_lockfile(
    req: GenerateCargoPackageLockfileRequest,
    rustup: RustupTool,
    platform: Platform,
) -> GenerateCargoLockfile:
    toolchain, source_files = await MultiGet(
        Get(
            RustToolchain,
            RustToolchainRequest(rustup.rust_version, platform_to_target(platform), ("cargo",)),
        ),
        Get(SourceFiles, CargoSourcesRequest(frozenset([req.package.address]))),
    )

    print(f"toolchain: {toolchain}")
    print(f"source_files: {source_files}")
    raise ValueError(f"not implemented yet")


@rule
async def setup_user_lockfile_requests(
    requested: RequestedCargoUserResolveNames,
    all_targets: AllCargoTargets,
) -> UserGenerateLockfiles:
    packages = []
    workspaces = []

    for resolve in requested:
        for package in all_targets.packages:
            if str(package.address) == resolve:
                packages.append(
                    GenerateCargoPackageLockfileRequest(
                        package,
                    )
                )

        for workspace in all_targets.workspaces:
            if str(workspace.address) == resolve:
                workspaces.append(
                    GenerateCargoWorkspaceLockfileRequest(
                        workspace,
                        tuple(workspace.members),
                    ),
                )

    print(f"packages: {packages}")
    print(f"workspaces: {workspaces}")
    return UserGenerateLockfiles(packages + workspaces)


def rules():
    return (
        *collect_rules(),  #
        UnionRule(GenerateLockfile, GenerateCargoLockfile),
        UnionRule(KnownUserResolveNamesRequest, KnownCargoUserResolveNamesRequest),
        UnionRule(RequestedUserResolveNames, RequestedCargoUserResolveNames),
        UnionRule(GenerateLockfile, GenerateCargoPackageLockfileRequest),
        UnionRule(GenerateLockfile, GenerateCargoWorkspaceLockfileRequest),
    )
