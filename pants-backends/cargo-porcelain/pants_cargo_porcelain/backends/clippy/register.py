from . import subsystem
from .goals import lint


def rules():
    return [
        *lint.rules(),
        *subsystem.rules(),
    ]
