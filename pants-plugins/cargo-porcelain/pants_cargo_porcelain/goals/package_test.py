"""`package` of a binary, with the sandbox env and a staged `files` dependency."""

from __future__ import annotations

import pytest
from pants.build_graph.address import Address
from pants.core.goals.package import BuiltPackage
from pants.engine.fs import Digest, DigestContents
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.goals.package import CargoBinaryFieldSet
from pants_cargo_porcelain.target_types import CargoBinaryTarget, CargoLibraryTarget
from pants_cargo_porcelain.testing import make_rule_runner, package_fixture
from pants_cargo_porcelain.util_rules.sandbox import CargoSources, CargoSourcesRequest


@pytest.fixture
def rule_runner() -> RuleRunner:
    return make_rule_runner([
        QueryRule(BuiltPackage, [CargoBinaryFieldSet]),
        QueryRule(DigestContents, [Digest]),
        QueryRule(CargoSources, [CargoSourcesRequest]),
    ])


def test_package_binary(rule_runner: RuleRunner) -> None:
    files = package_fixture(
        "hello",
        main=(
            'fn main() { println!("{} {}", include_str!("../../data/greeting.txt").trim(), '
            'env!("WHO")); }'
        ),
    )
    files["hello/BUILD"] = 'cargo_package(dependencies=["data:data"], env=["WHO=world"])'
    files["data/BUILD"] = 'files(name="data", sources=["*.txt"])'
    files["data/greeting.txt"] = "hello\n"
    rule_runner.write_files(files)

    assert isinstance(
        rule_runner.get_target(Address("hello", generated_name="hello")), CargoBinaryTarget
    )
    assert isinstance(
        rule_runner.get_target(Address("hello", generated_name="library")), CargoLibraryTarget
    )

    tgt = rule_runner.get_target(Address("hello", generated_name="hello"))
    assert CargoBinaryFieldSet.is_applicable(tgt)

    # The `files` dependency is staged next to the package's own sources.
    sources = rule_runner.request(
        CargoSources, [CargoSourcesRequest(frozenset([tgt.address]), include_packages=True)]
    )
    assert "data/greeting.txt" in sources.files, sources.files
    assert not CargoBinaryFieldSet.is_applicable(
        rule_runner.get_target(Address("hello", generated_name="library"))
    )

    built = rule_runner.request(BuiltPackage, [CargoBinaryFieldSet.create(tgt)])
    assert [a.relpath for a in built.artifacts] == ["hello/hello"]
    contents = rule_runner.request(DigestContents, [built.digest])
    assert [fc.path for fc in contents] == ["hello/hello"]
    assert contents[0].is_executable


def test_output_path_is_the_directory(rule_runner: RuleRunner) -> None:
    files = package_fixture("hello", main="fn main() {}")
    files["hello/BUILD"] = 'cargo_package(output_path="tools/hello")'
    rule_runner.write_files(files)
    tgt = rule_runner.get_target(Address("hello", generated_name="hello"))
    built = rule_runner.request(BuiltPackage, [CargoBinaryFieldSet.create(tgt)])
    assert [a.relpath for a in built.artifacts] == ["tools/hello/hello"]
