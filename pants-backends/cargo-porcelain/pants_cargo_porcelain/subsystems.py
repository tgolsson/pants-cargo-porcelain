from pants.core.util_rules.external_tool import ExternalTool
from pants.engine.platform import Platform
from pants.option.option_types import BoolOption, SkipOption, StrOption
from pants.option.subsystem import Subsystem
from pants.util.strutil import softwrap


class RustSubsystem(Subsystem):
    """General settings for Rust."""

    name = "rust"
    options_scope = "rust"
    help = "General settings for Rust."

    tailor = BoolOption(
        default=True,
        help=softwrap(""" If true, add `cargo_package` targets with the `tailor` goal."""),
        advanced=True,
    )

    skip = SkipOption("fmt", "lint")


class RustupTool(ExternalTool):
    """The rustup tool."""

    options_scope = "rustup"
    help = "Rustup manages rust toolchains."

    default_version = "v1.26.0"
    default_known_versions = [
        (
            "v1.26.0|linux_arm64"
            " |1b7b4411c9723dbbdda4ae9dde23a33d8ab093b54c97d3323784b117d3e9413f|32542312"
        ),
        "v1.26.0|linux_x86_64|0b2f6c8f85a3d02fde2efc0ced4657869d73fccfce59defb4e8d29233116e6db|14293176",
        (
            "v1.26.0|macos_arm64"
            " |27c88183de036ebd4ffa5bc5211329666e3c40ac69c5d938bcdab9b9ec248fd4|30189956"
        ),
        "v1.26.0|macos_x86_64|6e00cf4661c081fb1d010ce60904dccb880788a52bf10de16a40f32082415a87|29390800",
    ]

    def generate_url(self, plat: Platform) -> str:
        platform_mapping = {
            "linux_arm64": "aarch64-unknown-linux-gnu",
            "linux_x86_64": "x86_64-unknown-linux-gnu",
            "macos_arm64": "aarch64-apple-darwin",
            "macos_x86_64": "x86_64-apple-darwin",
        }
        plat_str = platform_mapping[plat.value]
        return (
            f"https://static.rust-lang.org/rustup/archive/{self.version[1:]}/{plat_str}/rustup-init"
        )

    def generate_exe(self, plat: Platform) -> str:
        return "./rustup-init"

    rust_version = StrOption(
        default="stable",
        help=softwrap("""The version of rust to install. If unspecified, stable is used."""),
    )


def rules():
    return [
        *RustSubsystem.rules(),
        *RustupTool.rules(),
    ]
