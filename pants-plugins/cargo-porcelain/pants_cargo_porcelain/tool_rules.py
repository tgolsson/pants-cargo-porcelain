from __future__ import annotations

from pants.core.util_rules.external_tool import DownloadedExternalTool, ExternalToolRequest
from pants.engine.fs import Digest, RemovePrefix
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import Get, collect_rules, rule

from pants_cargo_porcelain.internal.platform import platform_to_target
from pants_cargo_porcelain.subsystems import RustupTool
from pants_cargo_porcelain.tool import InstalledRustTool, RustToolRequest
from pants_cargo_porcelain.tools.binstall import BinstallTool
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


@rule(desc="Installing rust tool")
async def get_rust_tool(
    request: RustToolRequest,
    binstall: BinstallTool,
    rustup: RustupTool,
    platform: Platform,
) -> InstalledRustTool:
    toolchain = await Get(
        RustToolchain,
        RustToolchainRequest(
            rustup.rust_version, platform_to_target(platform), ("cargo", "rustfmt")
        ),
    )

    if binstall.enable:
        binstall_tool = await Get(
            DownloadedExternalTool, ExternalToolRequest, binstall.get_request(platform)
        )

        process_result = await Get(
            ProcessResult,
            CargoProcessRequest(
                toolchain,
                (
                    "binstall",
                    "--install-path=.",
                    f"{request.tool_name}",
                    f"--version={request.version}",
                    "-y",
                ),
                digest=binstall_tool.digest,
                output_files=(request.tool_name,),
            ),
        )

        digest = process_result.output_digest
    else:
        process_result = await Get(
            ProcessResult,
            CargoProcessRequest(
                toolchain,
                (
                    "install",
                    "--root=.",
                    f"{request.tool_name}",
                    f"--version={request.version}",
                ),
                output_files=(request.tool_name,),
            ),
        )

        digest = await Get(
            Digest,
            RemovePrefix(
                process_result.output_digest,
                "bin",
            ),
        )

    return InstalledRustTool(
        exe=request.tool_name,
        digest=digest,
    )


def rules():
    return [*collect_rules()]
