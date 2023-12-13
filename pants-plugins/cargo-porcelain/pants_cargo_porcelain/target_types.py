from __future__ import annotations

from typing import Iterable, Optional, Tuple

from pants.core.goals.package import OutputPathField
from pants.core.util_rules.environments import EnvironmentField
from pants.engine.addresses import Address
from pants.engine.rules import collect_rules
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    BoolField,
    Dependencies,
    InvalidFieldException,
    MultipleSourcesField,
    StringField,
    Target,
    TargetGenerator,
    generate_multiple_sources_field_help_message,
)
from pants.util.strutil import help_text


class CargoWorkspaceSourcesField(MultipleSourcesField):
    default = ("Cargo.toml", "Cargo.lock")
    expected_file_extensions = (".toml", ".lock")
    help = generate_multiple_sources_field_help_message(
        "Example: `sources=['Cargo.toml', 'Cargo.lock']`"
    )


class CargoWorkspaceTarget(Target):
    alias = "cargo_workspace"
    core_fields = (*COMMON_TARGET_FIELDS, CargoWorkspaceSourcesField)


class CargoPackageNameField(StringField):
    alias = "package_name"
    help = "The name of the package."


class _CargoPackageMarker(StringField):
    alias = "_package_tag"
    help = "Marker for a top level package"


class _CargoSourcesMarker(StringField):
    alias = "_sources_tag"
    help = "Marker for a Rust source bundle with Cargo files"


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
        _CargoPackageMarker,
    )
    copied_fields = (
        *COMMON_TARGET_FIELDS,
        SkipCargoTestsField,
        EnvironmentField,
        _CargoPackageMarker,
    )
    moved_fields = (CargoPackageDependenciesField,)
    help = help_text("""
        """)


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
        SkipCargoTestsField,
        EnvironmentField,
        CargoPackageNameField,
        _CargoPackageMarker,
    )
    help = help_text("""

        """)


class CargoSourcesTarget(Target):
    alias = "cargo_sources"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        EnvironmentField,
        CargoPackageNameField,
        _CargoSourcesMarker,
    )
    help = help_text("""

        """)


class CargoBinaryTarget(Target):
    alias = "cargo_binary"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoBinaryNameField,
    )
    help = help_text("""

        """)


class CargoTestTarget(Target):
    alias = "cargo_test"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        SkipCargoTestsField,
        EnvironmentField,
        CargoTestNameField,
        CargoPackageSourcesField,
    )
    help = help_text("""

        """)


class CargoLibraryTarget(Target):
    alias = "cargo_library"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
        CargoLibraryNameField,
    )
    help = help_text("""

        """)


def rules():
    return [
        *collect_rules(),
    ]


def target_types():
    return [
        CargoPackageTarget,
        CargoPackageTargetImpl,
        CargoBinaryTarget,
        CargoLibraryTarget,
        CargoWorkspaceTarget,
    ]
