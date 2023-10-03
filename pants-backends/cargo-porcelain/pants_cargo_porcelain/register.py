from . import subsystems
from . import target_types as tt
from .goals import fmt, package, tailor
from .internal import build
from .util_rules import cargo, rustup


def rules():
    return [
        *subsystems.rules(),
        *tailor.rules(),
        #        *package.rules(),
        *rustup.rules(),
        *tt.rules(),
        *cargo.rules(),
        *build.rules(),
        *package.rules(),
        *fmt.rules(),
    ]


def target_types():
    return tt.target_types()
