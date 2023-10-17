from dataclasses import dataclass

from pants.engine.fs import (
    Digest,
    DigestContents,
    DigestEntries,
    DigestSubset,
    Directory,
    FileEntry,
    PathGlobs,
)
from pants.engine.rules import Get, UnionRule, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    HydratedSources,
    HydrateSourcesRequest,
    InferDependenciesRequest,
    InferredDependencies,
)

from pants_cargo_porcelain.target_types import CargoPackageSourcesField


@dataclass(frozen=True)
class CargoDependenciesInferenceFieldSet(FieldSet):
    required_fields = (CargoPackageSourcesField,)

    sources: CargoPackageSourcesField


class InferCargoDependencies(InferDependenciesRequest):
    infer_from = CargoDependenciesInferenceFieldSet


@rule
async def infer_cargo_dependencies(request: InferCargoDependencies) -> InferredDependencies:
    hydrated_sources = await Get(HydratedSources, HydrateSourcesRequest(request.field_set.sources))
    cargo_toml_path = f"{request.field_set.address.spec_path}/Cargo.toml"

    new_digest = await Get(
        Digest, DigestSubset(hydrated_sources.snapshot.digest, PathGlobs([cargo_toml_path]))
    )
    digest_contents = await Get(DigestContents, Digest, new_digest)
    for file_content in digest_contents:
        print(file_content.path)
        print(file_content.content)  # This will be `bytes`.
    return InferredDependencies(...)


def rules():
    return [
        *collect_rules(),
        UnionRule(InferDependenciesRequest, InferCargoDependencies),
    ]
