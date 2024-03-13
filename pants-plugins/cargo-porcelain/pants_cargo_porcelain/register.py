from . import subsystems, target_generator
from . import target_types as tt
from . import tool, tool_rules
from .goals import fmt, generate_lockfiles, package, run, tailor, test
from .internal import build
from .tools import binstall, mtime
from .util_rules import cargo, dependency_inference, rustup, sandbox, workspace


def rules():
    return [
        *subsystems.rules(),
        *tailor.rules(),
        *package.rules(),
        *rustup.rules(),
        *run.rules(),
        *tt.rules(),
        *cargo.rules(),
        *build.rules(),
        *package.rules(),
        *fmt.rules(),
        *test.rules(),
        *dependency_inference.rules(),
        *sandbox.rules(),
        *target_generator.rules(),
        *workspace.rules(),
        *generate_lockfiles.rules(),
        *tool_rules.rules(),
        *tool.rules(),
        *binstall.rules(),
        *mtime.rules(),
    ]


def target_types():
    return tt.target_types()
