from pants.option.option_types import BoolOption
from pants.util.strutil import softwrap

from pants_cargo_porcelain.tool import RustTool


class CargoMtime(RustTool):
    """The `cargo mtime` tool."""

    options_scope = "cargo-mtime"
    help = softwrap("""
    The `cargo mtime` plugin helps manage file modification timestamps
    when files are built in a sandbox. As Pants uses hashes and has a more
    conservative rebuild, restoring the timestamps ensures only the minimal set
    is rebuilt in the sandbox.
    """)

    project_name = "cargo-mtime"
    default_version = "0.1.1"

    enabled = BoolOption(
        default=True,
        help=softwrap("""
            Can be used to enable or disable `cargo mtime`.
            """),
    )


def rules():
    return [
        *CargoMtime.rules(),
    ]
