
from pants.option.subsystem import Subsystem
from pants.option.option_types import StrListOption, StrOption

class RustToolBase(Subsystem):
    '''Base class for a Rust based tool that can be installed from source.'''

    version = StrOption(
        advanced=True,
        default=lambda cls: cls.default_version,
        help=lambda cls: softwrap(
            f"""
            Version of the tool to install.
            """
        ),
    )

class
