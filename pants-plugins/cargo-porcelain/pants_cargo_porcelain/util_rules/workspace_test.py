# Copyright 2021 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import annotations

import pytest
from pants.build_graph.address import Address
from pants.core.util_rules import external_tool, source_files
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain import subsystems, target_types
from pants_cargo_porcelain.target_generator import rules as target_generator_rules
from pants_cargo_porcelain.target_types import (
    CargoPackageTarget,
    CargoPackageTargetImpl,
    CargoWorkspaceTarget,
)
from pants_cargo_porcelain.util_rules import cargo, rustup, workspace
from pants_cargo_porcelain.util_rules.workspace import (
    AllCargoTargets,
    CargoPackageMapping,
    CargoWorkspaceMember,
)


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
            *target_generator_rules(),
            QueryRule(AllCargoTargets, []),
            QueryRule(CargoPackageMapping, []),
        ],
        target_types=[CargoPackageTargetImpl, CargoWorkspaceTarget, CargoPackageTarget],
    )
    rule_runner.set_options([], env_inherit={"PATH"})
    return rule_runner


def test_find_package_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "with_root/Cargo.toml": '[package]\nname="foobar"\nversion = "0.1.0"',
        "with_root/BUILD": "cargo_package()",
        "with_root/src/lib.rs": "",
    })
    rust_targets = rule_runner.request(AllCargoTargets, [])

    package = rule_runner.get_target(
        Address("with_root", target_name="with_root", generated_name="package")
    )
    assert rust_targets == AllCargoTargets(packages=(package,), workspaces=tuple())


def test_find_workspace_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "with_root/Cargo.toml": "[workspace]",
        "with_root/BUILD": 'cargo_workspace(name="workspace")',
    })
    rust_targets = rule_runner.request(AllCargoTargets, [])

    ws = rule_runner.get_target(Address("with_root", target_name="workspace"))
    assert rust_targets == AllCargoTargets(packages=tuple(), workspaces=(ws,))


def test_find_all_rust_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "with_root/Cargo.toml": '[workspace]\n[package]\nname="foobar"\nversion = "0.1.0"',
        "with_root/BUILD": 'cargo_workspace(name="workspace")\ncargo_package()',
        "with_root/src/lib.rs": "",
    })
    rust_targets = rule_runner.request(
        AllCargoTargets,
        [],
    )

    ws = rule_runner.get_target(Address("with_root", target_name="workspace"))
    package = rule_runner.get_target(
        Address("with_root", target_name="with_root", generated_name="package")
    )
    assert rust_targets == AllCargoTargets(packages=(package,), workspaces=(ws,))


def test_root_package(rule_runner) -> None:
    rule_runner.write_files({
        "with_root/BUILD": 'cargo_workspace(name="workspace")\ncargo_package()',
        "with_root/Cargo.toml": """
[workspace]
members = []
[package]
name = "root"
version = "0.1.0"
edition = "2021"

[dependencies]
""",
        "with_root/src/lib.rs": "",
    })

    package_mapping = rule_runner.request(
        CargoPackageMapping,
        [],
    )

    ws = rule_runner.get_target(Address("with_root", target_name="workspace"))
    package = rule_runner.get_target(
        Address("with_root", target_name="with_root", generated_name="package")
    )
    sources = rule_runner.get_target(
        Address("with_root", target_name="with_root", generated_name="sources")
    )
    assert package_mapping == CargoPackageMapping(
        FrozenDict({
            ws.address: frozenset({
                CargoWorkspaceMember(".", package, sources),
            })
        }),
        set(),
    )
