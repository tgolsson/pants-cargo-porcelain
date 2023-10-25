from __future__ import annotations

import json
from typing import Iterable, Optional, Tuple

from pants.core.goals.package import OutputPathField
from pants.core.util_rules.environments import EnvironmentField
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    BoolField,
    Dependencies,
    GeneratedTargets,
    GenerateTargetsRequest,
    InvalidFieldException,
    MultipleSourcesField,
    StringField,
    Target,
    TargetGenerator,
    generate_multiple_sources_field_help_message,
)
from pants.engine.unions import UnionRule
from pants.util.strutil import help_text

from pants_cargo_porcelain.internal.build import platform_to_target
from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


class CargoPackageNameField(StringField):
    alias = "package_name"
    help = "The name of the package."


class CargoPackageSourcesField(MultipleSourcesField):
    default = ("Cargo.toml", "Cargo.lock", "build.rs", "src/**/*", "tests/**/*.rs", "examples/**/*")
    expected_file_extensions = (".rs", ".toml", ".lock")
    help = generate_multiple_sources_field_help_message(
        "Example: `sources=['Cargo.toml', 'src/lib.rs', 'build.rs', '!test_ignore.rs']`"
    )

    @classmethod
    def compute_value(
        cls, raw_value: Optional[Iterable[str]], address: Address
    ) -> Optional[Tuple[str, ...]]:
        value_or_default = super().compute_value(raw_value, address)
        if not value_or_default:
            raise InvalidFieldException(
                f"The {repr(cls.alias)} field in target {address} must be set to files/globs in "
                f"the target's directory, but it was set to {repr(value_or_default)}."
            )
        return value_or_default


class CargoPackageDependenciesField(Dependencies):
    pass


class SkipCargoTestsField(BoolField):
    alias = "skip_tests"
    default = False
    help = "If true, don't run this package's tests."


class CargoPackageTarget(TargetGenerator):
    alias = "cargo_package"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoPackageSourcesField,
    )
    copied_fields = (
        *COMMON_TARGET_FIELDS,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
    )
    moved_fields = (CargoPackageDependenciesField,)
    help = help_text(
        """
        """
    )


class CargoBinaryNameField(StringField):
    alias = "binary_name"
    help = "The name of the binary."


class CargoTestNameField(StringField):
    alias = "test_name"
    help = "The name of the test."


class CargoLibraryNameField(StringField):
    alias = "library_name"
    help = "The name of the library."


class CargoPackageTargetImpl(Target):
    alias = "cargo_package_impl"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoPackageNameField,
    )
    help = help_text(
        """

        """
    )


class CargoBinaryTarget(Target):
    alias = "cargo_binary"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoBinaryNameField,
    )
    help = help_text(
        """

        """
    )


class CargoTestTarget(Target):
    alias = "cargo_test"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoTestNameField,
    )
    help = help_text(
        """

        """
    )


class CargoLibraryTarget(Target):
    alias = "cargo_library"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoLibraryNameField,
    )
    help = help_text(
        """

        """
    )


class GenerateCargoTargetsRequest(GenerateTargetsRequest):
    generate_from = CargoPackageTarget


@rule
async def generate_cargo_generated_target(
    request: GenerateCargoTargetsRequest,
    rust: RustSubsystem,
    rustup: RustupTool,
    platform: Platform,
) -> GeneratedTargets:
    source_files, toolchain = await MultiGet(
        Get(
            SourceFiles,
            SourceFilesRequest(
                [request.generator.get(CargoPackageSourcesField)],
            ),
        ),
        Get(
            RustToolchain,
            RustToolchainRequest(rustup.rust_version, platform_to_target(platform), ()),
        ),
    )

    process_result = await Get(
        ProcessResult,
        CargoProcessRequest(
            toolchain,
            (
                "metadata",
                f"--manifest-path={request.generator.address.spec_path}/Cargo.toml",
                "--format-version=1",
                "--no-deps",
            ),
            source_files.snapshot.digest,
        ),
    )

    output = json.loads(process_result.stdout)
    targets_meta = output["packages"][0]["targets"]

    libraries = []
    binaries = []
    tests = []

    for target in targets_meta:
        if "bin" in target["kind"]:
            binaries.append(target)

        if "lib" in target["kind"]:
            libraries.append(target)

        if "test" in target["kind"]:
            tests.append(target)

    name = request.generator.address.create_generated("package")
    generated_targets = [
        CargoPackageTargetImpl(
            {
                CargoPackageNameField.alias: output["packages"][0]["name"],
                **request.template,
            },
            name,
        )
    ]
    generated_lib_names = []
    for target in libraries:
        name = request.generator.address.create_generated("library")
        generated_targets.append(
            CargoLibraryTarget(
                {
                    CargoLibraryNameField.alias: target["name"],
                    **request.template,
                },
                name,
            )
        )
        generated_lib_names.append(str(name))

    for target in binaries:
        name = request.generator.address.create_generated(target["name"])
        generated_targets.append(
            CargoBinaryTarget(
                {
                    CargoPackageDependenciesField.alias: generated_lib_names,
                    CargoBinaryNameField.alias: target["name"],
                    **request.template,
                },
                name,
            )
        )

    for target in tests:
        name = request.generator.address.create_generated(target["name"])
        generated_targets.append(
            CargoTestTarget(
                {
                    **request.template,
                    CargoPackageDependenciesField.alias: generated_lib_names,
                    CargoTestNameField.alias: target["name"],
                    CargoPackageSourcesField.alias: [
                        *CargoPackageSourcesField.default,
                        "tests/**/*.rs",
                    ],
                },
                name,
            )
        )

    return GeneratedTargets(
        request.generator,
        generated_targets,
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(GenerateTargetsRequest, GenerateCargoTargetsRequest),
    ]


def target_types():
    return [
        CargoPackageTarget,
        CargoPackageTargetImpl,
        CargoBinaryTarget,
        CargoLibraryTarget,
    ]
