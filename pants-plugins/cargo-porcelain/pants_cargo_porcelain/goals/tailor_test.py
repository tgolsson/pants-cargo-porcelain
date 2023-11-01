# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import pytest
from pants.core.goals.tailor import AllOwnedSources, PutativeTarget, PutativeTargets
from pants.core.goals.tailor import rules as core_tailor_rules
from pants.core.util_rules import external_tool, source_files
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain import subsystems, target_types
from pants_cargo_porcelain.goals.tailor import PutativeCargoTargetsRequest
from pants_cargo_porcelain.goals.tailor import rules as cargo_tailor_rules
from pants_cargo_porcelain.target_types import CargoPackageTarget, CargoWorkspaceTarget
from pants_cargo_porcelain.util_rules import cargo, rustup


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *subsystems.rules(),
            *cargo_tailor_rules(),
            *core_tailor_rules(),
            *target_types.rules(),
            *source_files.rules(),
            *external_tool.rules(),
            *cargo.rules(),
            *rustup.rules(),
            QueryRule(PutativeTargets, [PutativeCargoTargetsRequest, AllOwnedSources]),
        ],
        target_types=[CargoPackageTarget],
    )
    rule_runner.set_options([], env_inherit={"PATH"})
    return rule_runner


def test_find_cargo_package_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "unowned/Cargo.toml": '[package]\nname="foobar"\nversion = "0.1.0"\n',
            "unowned/src/lib.rs": "",
            "owned/Cargo.toml": '[package]\nname="foobar"\nversion = "0.1.0"',
            "owned/BUILD": "cargo_package()",
            "owned/src/lib.rs": "",
        }
    )
    putative_targets = rule_runner.request(
        PutativeTargets,
        [PutativeCargoTargetsRequest(("unowned", "owned")), AllOwnedSources(["owned/Cargo.toml"])],
    )
    assert putative_targets == PutativeTargets(
        [
            PutativeTarget.for_target_type(
                CargoPackageTarget, path="unowned", name=None, triggering_sources=["Cargo.toml"]
            )
        ]
    )


def test_workspace_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "unowned/Cargo.toml": "[workspace]",
            "owned/Cargo.toml": '[package]\nname="foobar"\nversion = "0.1.0"',
            "owned/BUILD": "cargo_package()",
            "owned/src/lib.rs": "",
        }
    )

    putative_targets = rule_runner.request(
        PutativeTargets,
        [PutativeCargoTargetsRequest(("unowned", "owned")), AllOwnedSources(["owned/Cargo.toml"])],
    )
    assert putative_targets == PutativeTargets(
        [
            PutativeTarget.for_target_type(
                CargoWorkspaceTarget,
                path="unowned",
                name="workspace",
                triggering_sources=["Cargo.toml"],
            )
        ]
    )
