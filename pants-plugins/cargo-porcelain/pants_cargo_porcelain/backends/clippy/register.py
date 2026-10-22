from pants_cargo_porcelain.backends.clippy import subsystem
from pants_cargo_porcelain.backends.clippy.goals import lint


def rules():
    return [*subsystem.rules(), *lint.rules()]
