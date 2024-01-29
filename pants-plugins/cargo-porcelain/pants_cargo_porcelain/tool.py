from __future__ import annotations

from dataclasses import dataclass

from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import Get, collect_rules, rule
from pants.option.option_types import BoolOption, StrListOption, StrOption
from pants.option.subsystem import Subsystem
from pants.util.strutil import softwrap

from pants_cargo_porcelain.internal.platform import platform_to_target
from pants_cargo_porcelain.subsystems import RustupTool
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


class RustTool(Subsystem):
    """Base class for a Rust based tool that can be installed from source."""

    project_name: str

    version = StrOption(
        advanced=True,
        default=lambda cls: cls.default_version,
        help=lambda cls: softwrap(f"""
            Version of the tool to install.
            """),
    )

    def as_tool_request(self, *, version: str | None = None) -> RustToolRequest:
        """Returns a `RustToolRequest` for this tool."""
        return RustToolRequest(
            tool_name=self.project_name,
            version=version or self.version,
        )


@dataclass(frozen=True)
class RustToolRequest:
    """A request to install a Rust tool."""

    tool_name: str
    version: str


@dataclass(frozen=True)
class InstalledRustTool:
    """The result of installing a Rust tool."""

    exe: str
    digest: Digest


class Sccache(RustTool):
    """Sccache helps with."""

    options_scope = "sccache"
    help = "fff"

    project_name = "sccache"
    default_version = "0.6.0"

    enabled = BoolOption(
        default=None,
        help=softwrap("""
            Can be used to enable or disable `sccache`.
            """),
    )


def rules():
    return [
        *Sccache.rules(),
        *collect_rules(),
    ]
