import dataclasses
import os
from abc import ABCMeta
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Generic, Type, TypeVar

from pants.backend.python.target_types import InterpreterConstraintsField, PythonSourceField
from pants.core.goals.package import (
    BuiltPackage,
    EnvironmentAwarePackageRequest,
    OutputPathField,
    PackageFieldSet,
    TraverseIfNotPackageTarget,
)
from pants.engine.environment import EnvironmentName
from pants.engine.fs import CreateDigest, Digest, DigestEntries, MergeDigests, Snapshot
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    FieldSet,
    FieldSetsPerTarget,
    FieldSetsPerTargetRequest,
    GeneratedSources,
    GenerateSourcesRequest,
    ImmutableValue,
    NoApplicableTargetsBehavior,
    ScalarField,
    SourcesField,
    StringField,
    Target,
    TargetRootsToFieldSets,
    TargetRootsToFieldSetsRequest,
    Targets,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionMembership, UnionRule, union
from pants.util.frozendict import FrozenDict
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
    core_fields = (
        *COMMON_TARGET_FIELDS,
        PackagesField,
        Dummy,
        ModuleNameField,
        OutputPathField,
        InterpreterConstraintsField,
    )

    help = help_text(
        """

        """
    )


@dataclasses.dataclass(frozen=True)
class CargoLibraryPythonExtensionSettings:
    interpreter_version: str


class CargoLibraryPythonExtensionField(ScalarField):
    alias = "python_extension_settings"
    expected_type = CargoLibraryPythonExtensionSettings
    expected_type_help = "python_extension_settings(...)"
    value: CargoLibraryPythonExtensionSettings
    required = False
    help = help_text(
        """
        Foobar
        """
    )


_T = TypeVar("_T", bound="PythonExtensionRequest")


class PythonExtensionOutputData(FrozenDict[str, ImmutableValue]):
    pass


@union(in_scope_types=[EnvironmentName])
@dataclass(frozen=True)
class PythonExtensionFieldSet(Generic[_T], FieldSet, metaclass=ABCMeta):
    """FieldSet for PythonExtensionRequest.

    Union members may list any fields required to fulfill the
    instantiation of the `PythonExtensionResponse` result of the python_extension
    rule.

    """

    # Subclasses must provide this, to a union member (subclass) of `PythonExtensionRequest`.
    python_extension_request_type: ClassVar[Type[_T]]  # type: ignore[misc]

    def _request(self) -> _T:
        """Internal helper for the core python_extension goal."""
        return self.python_extension_request_type(field_set=self)

    @classmethod
    def rules(cls) -> tuple[UnionRule, ...]:
        """Helper method for registering the union members."""
        return (
            UnionRule(PythonExtensionFieldSet, cls),
            UnionRule(PythonExtensionRequest, cls.python_extension_request_type),
        )

    def get_output_data(self) -> PythonExtensionOutputData:
        return PythonExtensionOutputData({"target": self.address})


_F = TypeVar("_F", bound=FieldSet)


@union(in_scope_types=[EnvironmentName])
@dataclass(frozen=True)
class PythonExtensionRequest:
    field_set_type: ClassVar[type[PythonExtensionFieldSet]]


@dataclass(frozen=True)
class PythonExtension:
    digest: Digest


@dataclass(frozen=True)
class RustPythonExtensionRequest(PythonExtensionRequest):
    field_set: "RustPythonExtensionFieldSet"


@dataclass(frozen=True)
class RustPythonExtensionFieldSet(PythonExtensionFieldSet):
    python_extension_request_type = RustPythonExtensionRequest
    required_fields = (CargoLibraryPythonExtensionField,)

    python_extension: CargoLibraryPythonExtensionField


@rule
async def rust_python_extension(
    request: RustPythonExtensionRequest,
) -> PythonExtension:
    return PythonExtension(digest="")


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
        FieldSetsPerTargetRequest(PythonExtensionFieldSet, transitive_targets.dependencies),
    )

    requests = [pkg.field_set._request() for pkg in embedded_pkgs_per_target.field_sets]

    print(requests)

    embedded_pkgs = await MultiGet(
        Get(PythonExtension, PythonExtensionRequest, request) for request in requests
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
    from pants_cargo_porcelain.target_types import CargoLibraryTarget, CargoPackageTarget

    return [
        *collect_rules(),
        UnionRule(GenerateSourcesRequest, GeneratePythonFromPackagesRequest),
        UnionRule(PythonExtensionRequest, RustPythonExtensionRequest),
        CargoPackageTarget.register_plugin_field(CargoLibraryPythonExtensionField),
        CargoLibraryTarget.register_plugin_field(CargoLibraryPythonExtensionField),
    ]
