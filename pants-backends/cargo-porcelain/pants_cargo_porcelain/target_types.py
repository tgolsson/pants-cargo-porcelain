from typing import Iterable, Optional, Sequence, Tuple

from pants.core.goals.package import OutputPathField
from pants.core.util_rules.environments import EnvironmentField
from pants.engine.addresses import Address
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    AsyncFieldMixin,
    BoolField,
    Dependencies,
    InvalidFieldException,
    InvalidTargetException,
    MultipleSourcesField,
    StringField,
    StringSequenceField,
    Target,
    TargetGenerator,
    TriBoolField,
    ValidNumbers,
    generate_multiple_sources_field_help_message,
)
from pants.util.strutil import help_text


class CargoPackageSourcesField(MultipleSourcesField):
    default = ("Cargo.toml", "build.rs")
    expected_file_extensions = (".rs", ".toml")
    ban_subdirectories = True
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


class CargoPackageTarget(Target):
    alias = "cargo_package"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoPackageSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
    )
    help = help_text(
        """
        """
    )


class CargoSourcesField(MultipleSourcesField):
    default = ""
    expected_file_extensions = (".rs",)

    help = generate_multiple_sources_field_help_message("Example: `TODO`")

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


class CargoBinaryTarget(Target):
    alias = "cargo_binary"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        CargoPackageDependenciesField,
        CargoSourcesField,
        SkipCargoTestsField,
        OutputPathField,
        EnvironmentField,
    )
    help = help_text(
        """

        """
    )


def target_types():
    return [CargoPackageTarget, CargoBinaryTarget]
