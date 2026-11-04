from pants_backend_cc.util_rules import toolchain as cc_toolchain
from pants_backend_platforms import register as platforms

from pants_cargo_porcelain import subsystems, target_generator
from pants_cargo_porcelain import target_types as tt
from pants_cargo_porcelain.goals import fmt, generate_lockfiles, package, run, tailor, test
from pants_cargo_porcelain.internal import build
from pants_cargo_porcelain.util_rules import (
    cargo,
    dependency_inference,
    platform,
    rustup,
    sandbox,
    workspace,
)


def rules():
    return [
        *platforms.rules(),
        *cc_toolchain.rules(),
        *subsystems.rules(),
        *platform.rules(),
        *rustup.rules(),
        *cargo.rules(),
        *sandbox.rules(),
        *workspace.rules(),
        *dependency_inference.rules(),
        *target_generator.rules(),
        *build.rules(),
        *package.rules(),
        *run.rules(),
        *test.rules(),
        *fmt.rules(),
        *tailor.rules(),
        *generate_lockfiles.rules(),
    ]


def target_types():
    return tt.target_types()
