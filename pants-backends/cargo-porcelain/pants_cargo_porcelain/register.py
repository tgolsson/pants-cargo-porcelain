from . import subsystems
from . import target_types as tt
from .goals import tailor
from .util_rules import rustup


def rules():
    return [
        *subsystems.rules(),
        *tailor.rules(),
        #        *package.rules(),
        *rustup.rules(),
    ]


def target_types():
    return tt.target_types()
