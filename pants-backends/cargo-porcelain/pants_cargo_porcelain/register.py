from . import subsystems
from .goals import package, tailor


def rules():
    return [
        *subsystems.rules(),
        *tailor.rules(),
        *package.rules(),
    ]
