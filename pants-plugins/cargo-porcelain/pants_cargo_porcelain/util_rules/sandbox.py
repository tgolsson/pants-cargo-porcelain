"""What a cargo process gets in its sandbox: the cargo sources of the transitive closure, the
`files`/`resources` in it, and, when asked for, the `package` output of any packageable target
in it (a library another backend builds, for example), staged at its package path. The closure
stops at such a target: its own dependencies are its backend's inputs, not cargo's. A workspace
root brings its member packages, which do not depend on it in the graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pants.core.goals.package import (
    EnvironmentAwarePackageRequest,
    PackageFieldSet,
    environment_aware_package,
)
from pants.core.target_types import FileSourceField, ResourceSourceField
from pants.core.util_rules.source_files import SourceFilesRequest, determine_source_files
from pants.engine.addresses import Address
from pants.engine.fs import Digest, MergeDigests
from pants.engine.internals.graph import find_valid_field_sets, transitive_targets
from pants.engine.intrinsics import merge_digests
from pants.engine.rules import collect_rules, concurrently, implicitly, rule
from pants.engine.target import (
    Dependencies,
    DepsTraversalBehavior,
    FieldSetsPerTargetRequest,
    ShouldTraverseDepsPredicate,
    SpecialCasedDependencies,
    Target,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionMembership
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.target_types import (
    CargoArtifactKindField,
    CargoEnvField,
    CargoPackageSourcesField,
    CargoWorkspaceSourcesField,
)
from pants_cargo_porcelain.util_rules.cargo import is_reserved_env
from pants_cargo_porcelain.util_rules.workspace import CargoPackageMapping

_CARGO_FIELDS = (CargoPackageSourcesField, CargoWorkspaceSourcesField)


@dataclass(frozen=True)
class CargoSourcesRequest:
    addresses: frozenset[Address]
    include_packages: bool
    """Whether to build the packageable targets in the closure and stage their outputs: what
    compiles needs them, `cargo fmt` and `cargo update` do not."""


@dataclass(frozen=True)
class CargoSources:
    digest: Digest
    files: tuple[str, ...]
    env: FrozenDict[str, str]
    """The `env` of every cargo package in the closure, merged: a dependency's build script
    reads what its own package set (`MYLIB_DIR`), whichever package the cargo process is
    for."""


def parse_env(entries: tuple[str, ...] | None) -> FrozenDict[str, str]:
    """A target's `env` field (`KEY=VALUE` entries) as a dict."""
    env = {}
    for entry in entries or ():
        key, sep, value = entry.partition("=")
        if not sep or not key:
            raise ValueError(f"`env` entries are `KEY=VALUE`, not `{entry}`")
        env[key] = value
    return FrozenDict(env)


def merge_env(targets: Iterable[Target]) -> FrozenDict[str, str]:
    env: dict[str, str] = {}
    for target in targets:
        if not target.has_field(CargoEnvField):
            continue
        for key, value in parse_env(target[CargoEnvField].value).items():
            if is_reserved_env(key):
                raise ValueError(
                    f"{target.address} sets `{key}` in `env`, but the cargo backend sets "
                    f"`{key}` itself for every cargo process"
                )
            if env.get(key, value) != value:
                raise ValueError(
                    f"{target.address} sets `{key}` in `env` to `{value}`, but another package "
                    f"of the same build sets it to `{env[key]}`"
                )
            env[key] = value
    return FrozenDict(env)


def _is_cargo(tgt: Target) -> bool:
    return tgt.has_field(CargoArtifactKindField) or any(tgt.has_field(f) for f in _CARGO_FIELDS)


@dataclass(frozen=True)
class _StopAtPackages(ShouldTraverseDepsPredicate):
    """Traverses everything but the dependencies of a packageable non-cargo target."""

    package_field_sets: tuple[type[PackageFieldSet], ...]

    def __call__(
        self, target: Target, field: Dependencies | SpecialCasedDependencies
    ) -> DepsTraversalBehavior:
        if not isinstance(field, Dependencies) or (
            not _is_cargo(target)
            and any(fs.is_applicable(target) for fs in self.package_field_sets)
        ):
            return DepsTraversalBehavior.EXCLUDE
        return DepsTraversalBehavior.INCLUDE


@rule(desc="Collect the sources of a cargo build")
async def cargo_sources(
    request: CargoSourcesRequest,
    mapping: CargoPackageMapping,
    union_membership: UnionMembership,
) -> CargoSources:
    predicate = _StopAtPackages(tuple(union_membership.get(PackageFieldSet)))
    # cargo loads every member's manifest whenever a workspace is involved, so a workspace
    # in the closure (as a root, or as a member's dependency) brings all its members.
    roots = set(request.addresses)
    closure = await transitive_targets(
        TransitiveTargetsRequest(sorted(roots), should_traverse_deps_predicate=predicate),
        **implicitly(),
    )
    members = {
        m.package.address
        for tgt in closure.closure
        if tgt.address in mapping.workspace_to_packages
        for m in mapping.workspace_to_packages[tgt.address]
    }
    if not members <= roots:
        roots |= members
        closure = await transitive_targets(
            TransitiveTargetsRequest(sorted(roots), should_traverse_deps_predicate=predicate),
            **implicitly(),
        )

    source_fields = []
    packageable = []
    for tgt in closure.closure:
        cargo_field = next((f for f in _CARGO_FIELDS if tgt.has_field(f)), None)
        if cargo_field is not None:
            source_fields.append(tgt[cargo_field])
        elif tgt.has_field(FileSourceField):
            source_fields.append(tgt[FileSourceField])
        elif tgt.has_field(ResourceSourceField):
            source_fields.append(tgt[ResourceSourceField])
        elif tgt.has_field(CargoArtifactKindField):
            continue  # cargo's own binaries are built by this process, not staged into it
        elif request.include_packages:
            packageable.append(tgt)

    field_sets = await find_valid_field_sets(
        FieldSetsPerTargetRequest(PackageFieldSet, packageable), **implicitly()
    )
    sources, packages = await concurrently(
        determine_source_files(SourceFilesRequest(source_fields)),
        concurrently(
            environment_aware_package(EnvironmentAwarePackageRequest(fs))
            for fs in field_sets.field_sets
        ),
    )
    digest = await merge_digests(
        MergeDigests([sources.snapshot.digest, *(p.digest for p in packages)])
    )
    return CargoSources(digest, sources.files, merge_env(closure.closure))


def rules():
    return collect_rules()
