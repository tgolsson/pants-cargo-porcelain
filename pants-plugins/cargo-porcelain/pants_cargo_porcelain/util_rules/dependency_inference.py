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

from pants_cargo_porcelain.target_types import CargoLibraryNameField, CargoPackageSourcesField
from pants_cargo_porcelain.util_rules.workspace import AllCargoTargets, CargoPackageMapping


@dataclass(frozen=True)
class CargoDependenciesInferenceFieldSet(FieldSet):
    required_fields = (CargoPackageSourcesField,)

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
        all_dependencies.append(package_mapping.get_workspace_for_package(request.field_set))

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
                    description_of_origin="the `openapi_document` dependency inference",
                ),
            )
            addresses = [
                target.address
                for target in candidate_targets
                if target.has_field(CargoLibraryNameField)
            ]

            all_dependencies.extend(addresses)

    return InferredDependencies(sorted(all_dependencies))


def rules():
    return [
        *collect_rules(),
        UnionRule(InferDependenciesRequest, InferCargoDependencies),
    ]
