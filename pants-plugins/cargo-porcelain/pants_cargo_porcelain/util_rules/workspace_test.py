from __future__ import annotations

import pytest
from pants.build_graph.address import Address
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.testing import make_rule_runner, package_fixture
from pants_cargo_porcelain.util_rules.workspace import (
    AllCargoTargets,
    CargoPackageMapping,
    CargoWorkspaceMember,
)


@pytest.fixture
def rule_runner() -> RuleRunner:
    return make_rule_runner([QueryRule(AllCargoTargets, []), QueryRule(CargoPackageMapping, [])])


def test_find_package_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(package_fixture("foobar"))
    targets = rule_runner.request(AllCargoTargets, [])
    package = rule_runner.get_target(Address("foobar", generated_name="package"))
    assert targets == AllCargoTargets(packages=(package,), workspaces=())


def test_find_workspace_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "ws/Cargo.toml": "[workspace]\nmembers = []\n",
        "ws/BUILD": 'cargo_workspace(name="workspace")',
    })
    targets = rule_runner.request(AllCargoTargets, [])
    ws = rule_runner.get_target(Address("ws", target_name="workspace"))
    assert targets == AllCargoTargets(packages=(), workspaces=(ws,))


def test_workspace_members(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "ws/Cargo.toml": '[workspace]\nresolver = "2"\nmembers = ["a", "b"]\n',
        "ws/Cargo.lock": "version = 4\n",
        "ws/BUILD": 'cargo_workspace(name="workspace")',
        **{k.replace("a/", "ws/a/", 1): v for k, v in package_fixture("a").items()},
        **{k.replace("b/", "ws/b/", 1): v for k, v in package_fixture("b").items()},
        **package_fixture("loose"),
    })
    mapping = rule_runner.request(CargoPackageMapping, [])

    ws = Address("ws", target_name="workspace")
    a = rule_runner.get_target(Address("ws/a", generated_name="package"))
    b = rule_runner.get_target(Address("ws/b", generated_name="package"))
    loose = rule_runner.get_target(Address("loose", generated_name="package"))
    assert mapping == CargoPackageMapping(
        FrozenDict({ws: frozenset({CargoWorkspaceMember("a", a), CargoWorkspaceMember("b", b)})}),
        frozenset({loose}),
    )
    assert mapping.workspace_for(a.address) == ws
    assert mapping.workspace_for(loose.address) is None


def test_member_manifests_among_the_sources(rule_runner: RuleRunner) -> None:
    # `0-core/Cargo.toml` sorts before the workspace's own manifest.
    rule_runner.write_files({
        "ws/Cargo.toml": '[workspace]\nresolver = "2"\nmembers = ["0-core"]\n',
        "ws/Cargo.lock": "version = 4\n",
        "ws/BUILD": (
            'cargo_workspace(name="workspace", '
            'sources=["Cargo.toml", "Cargo.lock", "0-core/Cargo.toml"])'
        ),
        **{k.replace("core/", "ws/0-core/", 1): v for k, v in package_fixture("core").items()},
    })
    mapping = rule_runner.request(CargoPackageMapping, [])
    core = rule_runner.get_target(Address("ws/0-core", generated_name="package"))
    assert mapping.workspace_for(core.address) == Address("ws", target_name="workspace")


def test_root_package(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({
        "ws/BUILD": 'cargo_workspace(name="workspace")\ncargo_package()',
        "ws/Cargo.toml": (
            '[workspace]\nmembers = []\n[package]\nname = "root"\nversion = "0.1.0"\n'
            'edition = "2021"\n'
        ),
        "ws/Cargo.lock": 'version = 4\n\n[[package]]\nname = "root"\nversion = "0.1.0"\n',
        "ws/src/lib.rs": "",
    })
    mapping = rule_runner.request(CargoPackageMapping, [])
    ws = Address("ws", target_name="workspace")
    package = rule_runner.get_target(Address("ws", generated_name="package"))
    assert mapping == CargoPackageMapping(
        FrozenDict({ws: frozenset({CargoWorkspaceMember(".", package)})}), frozenset()
    )
