from pants.core.util_rules.external_tool import ExternalTool
from pants.engine.platform import Platform
from pants.option.option_types import BoolOption
from pants.util.strutil import softwrap


class BinstallTool(ExternalTool):
    """Binstall is a rust tool for installing binaries from github
    releases, instead of building them from source.

    This can be enabled per-tool by setting the `binstall` option to
    `True` in the tool's scope. It can also be disabled or disabled
    globally by setting the `binstall` option to `True` or `False` in
    the `binstall` scope.

    """

    name = "binstall"
    options_scope = "binstall"
    help = """Binstall is a rust tool for installing binaries from
    github releases, instead of building them from source.

    This can be enabled per-tool by setting the `binstall` option to
    `True` in the tool's scope. It can also be disabled or disabled
    globally by setting the `binstall` option to `True` or `False` in
    the `binstall` scope."""

    enable = BoolOption(
        default=None,
        help=softwrap("""Can be used to enable or disable `binstall` globally."""),
    )

    default_version = "v1.4.6"
    default_known_versions = [
        "v1.4.6|linux_arm64|b321b6ee360d39465027c92c328e31f77df3c8f119fede80962152fff4ec3d0c|6784880",
        "v1.4.6|linux_x86_64|ac755e512686b0d6d30fb3894f148cbe1e99a99afd77d2c62e05398802cf87f7|7064830",
        "v1.4.6|macos_arm64|dd6a100437d67d71117687dc24a8f37a116916823e7600c9fce3462145ed0a1a|6331670",
        "v1.4.6|macos_x86_64|522d437f4f4bebf47c1c6bb9194fb28fd61c3e7e550aa8ff2b70b4b7eed8f209|6800984",
    ]

    def generate_url(self, plat: Platform) -> str:
        # https://github.com/cargo-bins/cargo-binstall/releases/download/v1.4.6/cargo-binstall-aarch64-apple-darwin.full.zip
        platform_mapping = {
            "linux_arm64": "aarch64-unknown-linux-gnu",
            "linux_x86_64": "x86_64-unknown-linux-gnu",
            "macos_arm64": "aarch64-apple-darwin",
            "macos_x86_64": "x86_64-apple-darwin",
        }

        extension_mapping = {
            "linux_arm64": "full.tgz",
            "linux_x86_64": "full.tgz",
            "macos_arm64": "full.zip",
            "macos_x86_64": "full.zip",
        }
        plat_str = platform_mapping[plat.value]
        ext = extension_mapping[plat.value]
        repo = "https://github.com/cargo-bins/cargo-binstall"
        return f"{repo}/releases/download/{self.version}/cargo-binstall-{plat_str}.{ext}"

    def generate_exe(self, plat: Platform) -> str:
        return "./cargo-binstall"


def rules():
    return BinstallTool.rules()
