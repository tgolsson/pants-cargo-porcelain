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

    release = BoolOption(
        default=False,
        help=softwrap("""If true, build in release mode."""),
        advanced=True,
    )

    skip = SkipOption("fmt", "lint")


class RustupTool(ExternalTool):
    """The rustup tool."""

    options_scope = "rustup"
    help = "Rustup manages rust toolchains."

    default_version = "v1.26.0"
    default_known_versions = [
        "v1.26.0|linux_arm64|673e336c81c65e6b16dcdede33f4cc9ed0f08bde1dbe7a935f113605292dc800|14131368",
        "v1.26.0|linux_x86_64|0b2f6c8f85a3d02fde2efc0ced4657869d73fccfce59defb4e8d29233116e6db|14293176",
        "v1.26.0|macos_arm64|ed299a8fe762dc28161a99a03cf62836977524ad557ad70e13882d2f375d3983|8000713",
        "v1.26.0|macos_x86_64|f6d1a9fac1a0d0802d87c254f02369a79973bc8c55aa0016d34af4fcdbd67822|8670640",
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
