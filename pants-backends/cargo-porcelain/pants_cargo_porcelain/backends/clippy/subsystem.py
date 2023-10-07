from pants.option.option_types import ArgsListOption, SkipOption
from pants.option.subsystem import Subsystem


class ClippySubsystem(Subsystem):
    """Settings for clippy."""

    name = "clippy"
    options_scope = "clippy"
    help = "Settings for clippy"

    skip = SkipOption("lint")
    args = ArgsListOption(example="-D warnings")


def rules():
    return [
        *ClippySubsystem.rules(),
    ]
