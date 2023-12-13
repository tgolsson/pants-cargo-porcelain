import dataclasses
import os
from pathlib import Path

from pants.backend.python.target_types import PythonSourceField
from pants.core.goals.package import (
    BuiltPackage,
    EnvironmentAwarePackageRequest,
    OutputPathField,
    PackageFieldSet,
    TraverseIfNotPackageTarget,
)
from pants.core.target_types import ResourceSourceField
from pants.core.util_rules.system_binaries import BinaryShims, BinaryShimsRequest
from pants.engine.fs import CreateDigest, Digest, DigestEntries, MergeDigests, Snapshot
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    FieldSetsPerTarget,
    FieldSetsPerTargetRequest,
    GeneratedSources,
    GenerateSourcesRequest,
    SourcesField,
    StringField,
    Target,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionMembership, UnionRule
from pants.util.strutil import help_text


class Dummy(SourcesField):
    alias = "_do_not_use"


class PackagesField(Dependencies):
    alias = "package"


class ModuleNameField(StringField):
    alias = "module_name"


class GeneratePythonFromPackagesRequest(GenerateSourcesRequest):
    input = Dummy
    output = PythonSourceField


class PythonExtensionsTarget(Target):
    alias = "python_extension"
    core_fields = (*COMMON_TARGET_FIELDS, PackagesField, Dummy, ModuleNameField, OutputPathField)

    help = help_text(
        """

        """
    )


@rule
async def generate_python_from_packages(
    request: GeneratePythonFromPackagesRequest,
    union_membership: UnionMembership,
) -> GeneratedSources:
    transitive_targets = await Get(
        TransitiveTargets,
        TransitiveTargetsRequest(
            [request.protocol_target.address],
            should_traverse_deps_predicate=TraverseIfNotPackageTarget(
                roots=[request.protocol_target.address],
                union_membership=union_membership,
            ),
        ),
    )

    if len(transitive_targets.dependencies) > 1:
        raise ValueError(
            f"""{PythonExtensionsTarget.alias} can only handle one target at a time."""
        )

    embedded_pkgs_per_target = await Get(
        FieldSetsPerTarget,
        FieldSetsPerTargetRequest(PackageFieldSet, transitive_targets.dependencies),
    )

    embedded_pkgs = await MultiGet(
        Get(BuiltPackage, EnvironmentAwarePackageRequest(field_set))
        for field_set in embedded_pkgs_per_target.field_sets
    )

    embedded_pkgs_digests = [built_package.digest for built_package in embedded_pkgs]

    snapshot = await Get(Snapshot, MergeDigests(d for d in embedded_pkgs_digests if d))

    entries = await Get(DigestEntries, Digest, snapshot.digest)
    new_entry = dataclasses.replace(
        entries[0],
        path=os.path.join(
            Path(
                request.protocol_target.get(OutputPathField).value_or_default(file_ending="unused")
            ).parent,
            request.protocol_target.get(ModuleNameField).value,
        ),
    )
    snapshot = await Get(Snapshot, CreateDigest([new_entry]))

    return GeneratedSources(snapshot)


def rules():
    return [
        *collect_rules(),
        UnionRule(GenerateSourcesRequest, GeneratePythonFromPackagesRequest),
    ]
