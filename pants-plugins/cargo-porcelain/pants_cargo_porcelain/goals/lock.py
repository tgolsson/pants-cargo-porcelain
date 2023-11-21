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
from pants_backend_rust.subsystem import RustSubsystem
from pants_backend_rust.targets import (
    CargoPackage,
    CargoWorkspace,
    RustSources,
    WorkspacePackages,
    WorkspaceSources,
)


@dataclass(frozen=True)
class GenerateRustLockfile(GenerateLockfile):
    sources: RustSources


@rule(desc="Generate Rust lockfile", level=LogLevel.DEBUG)
async def generate_lockfile(
    req: GenerateRustLockfile,
    generate_lockfiles_subsystem: RustSubsystem,
) -> GenerateLockfileResult:
    pass


class RequestedRustUserResolveNames(RequestedUserResolveNames):
    pass


class KnownRustUserResolveNamesRequest(KnownUserResolveNamesRequest):
    pass


@rule
def determine_rust_user_resolves(_: KnownRustUserResolveNamesRequest) -> KnownUserResolveNames:
    return KnownUserResolveNames(
        names=["default"],
        option_name=f"[rust].resolves",
        requested_resolve_names_cls=RequestedRustUserResolveNames,
    )


@dataclass(frozen=True)
class GenerateRustWorkspaceLockfileRequest:
    workspace: CargoWorkspace
    packages: tuple[CargoPackage, ...]


class GenerateRustPackageLockfileRequest:
    pass


@rule
async def generate_rust_workspace_lockfile(
    req: GenerateRustWorkspaceLockfileRequest,
    rust_subsystem: RustSubsystem,
) -> GenerateRustLockfile:
    pass


@rule
async def generate_rust_package_lockfile(
    req: GenerateRustPackageLockfileRequest,
    rust_subsystem: RustSubsystem,
) -> GenerateRustLockfile:
    pass


@rule
async def setup_user_lockfile_requests(
    requested: RequestedRustUserResolveNames,
    all_targets: AllTargets,
    rust_subsystem: RustSubsystem,
) -> UserGenerateLockfiles:
    print("HELLO")

    workspaces = []
    packages = []

    for tgt in sorted(all_targets, key=lambda t: t.address):
        if tgt.has_field(WorkspaceSources):
            workspaces.append(tgt)

        if tgt.has_field(RustSources):
            packages.append(tgt)

    workspace_to_packages = defaultdict(list)

    solo_packages = []
    for pkg in packages:
        for workspace in workspaces:
            print(f"Adding {pkg.address} to {workspace.get(WorkspacePackages).value}")
            if pkg.address in workspace.get(WorkspacePackages).value:
                workspace_to_packages[workspace].append(pkg)
                break
        else:
            solo_packages.append(pkg)

    workspace_requests = [
        Get(
            GenerateRustLockfile,
            GenerateRustWorkspaceLockfileRequest(
                workspace=workspace,
                packages=tuple(workspace_to_packages[workspace]),
            ),
        )
        for resolve in requested
    ]

    package_requests = [
        Get(
            GenerateRustLockfile,
            GenerateRustPackageLockfileRequest(
                package=package,
            ),
        )
        for package in solo_packages
    ]

    rust_lockfile_requests = await MultiGet(
        *(workspace_requests + package_requests),
    )
    return UserGenerateLockfiles(rust_lockfile_requests)


def rules():
    return (
        *collect_rules(),  #
        # UnionRule(GenerateLockfile, GenerateRustLockfile),
        # UnionRule(KnownUserResolveNamesRequest, KnownRustUserResolveNamesRequest),
        # UnionRule(RequestedUserResolveNames, RequestedRustUserResolveNames),
    )
