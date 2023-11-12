import os
import pathlib
from dataclasses import dataclass

import toml
from pants.base.specs import DirGlobSpec, RawSpecs
from pants.engine.fs import Digest, DigestContents, DigestSubset, PathGlobs
from pants.engine.rules import Get, UnionRule, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    HydratedSources,
    HydrateSourcesRequest,
    InferDependenciesRequest,
    InferredDependencies,
    Targets,
)

from pants_cargo_porcelain.target_types import (
    CargoLibraryNameField,
    CargoPackageNameField,
    CargoPackageSourcesField,
    CargoWorkspaceSourcesField,
    _CargoPackageMarker,
)
from pants_cargo_porcelain.util_rules.workspace import AllCargoTargets, CargoPackageMapping


@dataclass(frozen=True)
class CargoDependenciesInferenceFieldSet(FieldSet):
    required_fields = (CargoPackageNameField, _CargoPackageMarker)

    sources: CargoPackageSourcesField


class InferCargoDependencies(InferDependenciesRequest):
    infer_from = CargoDependenciesInferenceFieldSet


@rule
async def infer_cargo_dependencies(
    request: InferCargoDependencies,
    all_targets: AllCargoTargets,
    package_mapping: CargoPackageMapping,
) -> InferredDependencies:
    hydrated_sources = await Get(HydratedSources, HydrateSourcesRequest(request.field_set.sources))
    cargo_toml_path = f"{request.field_set.address.spec_path}/Cargo.toml"

    new_digest = await Get(
        Digest, DigestSubset(hydrated_sources.snapshot.digest, PathGlobs([cargo_toml_path]))
    )
    digest_contents = await Get(DigestContents, Digest, new_digest)

    base_path = pathlib.Path(cargo_toml_path).parent

    all_dependencies = []

    if package_mapping.is_workspace_member(request.field_set):
        ws = package_mapping.get_workspace_for_package(request.field_set)
        all_dependencies.append(ws)

    for file_content in digest_contents:
        content = toml.loads(file_content.content.decode())
        dependencies = content.get("dependencies", {})

        for name, dependency in dependencies.items():
            if "path" not in dependency:
                continue

            path = dependency["path"]

            dependency_directory = os.path.normpath(base_path / path)

            candidate_targets = await Get(
                Targets,
                RawSpecs(
                    dir_globs=(DirGlobSpec(f"{dependency_directory}"),),
                    description_of_origin="the `cargo` dependency inference",
                ),
            )

            addresses = [
                target.address
                for target in candidate_targets
                if target.has_field(CargoLibraryNameField)
            ]

            all_dependencies.extend(addresses)

    if request.field_set.address in all_dependencies:
        all_dependencies.remove(request.field_set.address)

    return InferredDependencies(sorted(all_dependencies))


@dataclass(frozen=True)
class CargoWorkspaceDependenciesInferenceFieldSet(FieldSet):
    required_fields = (CargoWorkspaceSourcesField,)

    sources: CargoWorkspaceSourcesField


class InferWorkspaceDependencies(InferDependenciesRequest):
    infer_from = CargoWorkspaceDependenciesInferenceFieldSet


@rule
async def infer_workspace_dependencies(
    request: InferWorkspaceDependencies,
    package_mapping: CargoPackageMapping,
) -> InferredDependencies:
    workspace_packages = package_mapping.get_workspace_members(request.field_set.address)

    return InferredDependencies(tuple(wp.sources.address for wp in workspace_packages))


def rules():
    return [
        *collect_rules(),
        UnionRule(InferDependenciesRequest, InferCargoDependencies),
        UnionRule(InferDependenciesRequest, InferWorkspaceDependencies),
    ]
