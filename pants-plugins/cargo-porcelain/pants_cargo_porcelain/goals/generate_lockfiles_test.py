# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import pytest
from pants.build_graph.address import Address
from pants.core.goals.generate_lockfiles import rules as goal_rules
from pants.core.util_rules import external_tool, source_files
from pants.engine.fs import Digest
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain import register, subsystems, target_types
from pants_cargo_porcelain.goals.generate_lockfiles import (
    GenerateCargoPackageLockfileRequest,
    GenerateCargoWorkspaceLockfileRequest,
    GenerateLockfileResult,
)
from pants_cargo_porcelain.goals.generate_lockfiles import rules as generate_lockfiles_rules
from pants_cargo_porcelain.target_generator import rules as target_generator_rules
from pants_cargo_porcelain.tool import rules as tool_rules
from pants_cargo_porcelain.tool_rules import rules as tool_rules_rules
from pants_cargo_porcelain.tools.mtime import rules as mtime_rules
from pants_cargo_porcelain.util_rules import cargo, dependency_inference, rustup, workspace
from pants_cargo_porcelain.util_rules.sandbox import rules as sandbox_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *subsystems.rules(),
            *target_types.rules(),
            *source_files.rules(),
            *external_tool.rules(),
            *cargo.rules(),
            *rustup.rules(),
            *workspace.rules(),
            *generate_lockfiles_rules(),
            *dependency_inference.rules(),
            *goal_rules(),
            *sandbox_rules(),
            *target_generator_rules(),
            *tool_rules(),
            *tool_rules_rules(),
            *mtime_rules(),
            QueryRule(GenerateLockfileResult, [GenerateCargoPackageLockfileRequest]),
            QueryRule(GenerateLockfileResult, [GenerateCargoWorkspaceLockfileRequest]),
        ],
        target_types=register.target_types(),
        preserve_tmpdirs=True,
    )
    rule_runner.set_options(
        ["--keep-sandboxes=always", "--rustup-rust-version=1.72.1"], env_inherit={"PATH"}
    )
    return rule_runner


def test_lock_workspace(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "with_root/Cargo.toml": '[workspace]\n[package]\nname="foobar"\nversion = "0.1.0"',
        "with_root/BUILD": 'cargo_workspace(name="workspace")\ncargo_package()',
        "with_root/src/lib.rs": "",
    })

    ws = rule_runner.get_target(Address("with_root", target_name="workspace"))
    generate_lockfile_result = rule_runner.request(
        GenerateLockfileResult,
        [
            GenerateCargoWorkspaceLockfileRequest(
                workspace=ws,
                resolve_name=str(ws.address),
                lockfile_dest=f"{ws.address.spec_path}/Cargo.lock",
                diff=True,
            )
        ],
    )

    assert generate_lockfile_result == GenerateLockfileResult(
        digest=Digest("056d417693d004475d6bf861087e02bb1d67c8a76beec304d30339bd2fd52126", 83),
        resolve_name="with_root:workspace",
        path="with_root/Cargo.lock",
        diff=None,
    )
