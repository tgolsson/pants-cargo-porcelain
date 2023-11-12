import pytest
from pants.build_graph.address import Address
from pants.core.goals.lint import LintResult, Partitions
from pants.core.util_rules import external_tool, source_files
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain import register
from pants_cargo_porcelain.backends.clippy import register as clippy_register
from pants_cargo_porcelain.backends.clippy.goals.lint import (
    CargoClippyFieldSet,
    CargoClippyRequest,
    PackageMetadata,
)


@pytest.fixture
def rule_runner():
    rule_runner = RuleRunner(
        rules=[
            *register.rules(),
            *clippy_register.rules(),
            *source_files.rules(),
            *external_tool.rules(),
            QueryRule(Partitions, [CargoClippyRequest.PartitionRequest]),
            QueryRule(LintResult, [CargoClippyRequest.Batch]),
        ],
        target_types=register.target_types(),
    )

    return rule_runner


def test_clippy_subsystem_partition(rule_runner) -> None:
    rule_runner.write_files({
        "rust/BUILD": "cargo_package()",
        "rust/Cargo.toml": '[package]\nname = "rust"\nversion = "0.1.0"\n',
        "rust/src/main.rs": 'fn main() { println!("Hello, world!"); }',
    })

    tgt = rule_runner.get_target(Address("rust", target_name="rust", generated_name="package"))
    res = rule_runner.request(
        Partitions[CargoClippyFieldSet, PackageMetadata],
        [CargoClippyRequest.PartitionRequest((CargoClippyFieldSet.create(tgt),))],
    )

    assert len(res) == 1


def test_clippy_subsystem_run_ok(rule_runner) -> None:
    rule_runner.set_options(["--clippy-args=['--', '-Dwarnings']"], env_inherit={"PATH"})

    rule_runner.write_files({
        "rust/BUILD": "cargo_package()",
        "rust/Cargo.toml": '[package]\nname = "rust"\nversion = "0.1.0"\n',
        "rust/Cargo.lock": """version = 3
[[package]]
name = "rust"
version = "0.1.0"
""",
        "rust/src/main.rs": 'fn main() { println!("Hello, world!"); }',
    })

    tgt = rule_runner.get_target(Address("rust", target_name="rust", generated_name="package"))
    partitions = rule_runner.request(
        Partitions[CargoClippyFieldSet, PackageMetadata],
        [CargoClippyRequest.PartitionRequest((CargoClippyFieldSet.create(tgt),))],
    )

    results = []
    for partition in partitions:
        result = rule_runner.request(
            LintResult,
            [CargoClippyRequest.Batch("", partition.elements, partition.metadata)],
        )

        results.append(result)

    assert len(results) == 1
    assert results[0].exit_code == 0


def test_clippy_subsystem_run_warn(rule_runner) -> None:
    rule_runner.set_options([], env_inherit={"PATH"})

    rule_runner.write_files({
        "rust/BUILD": "cargo_package()",
        "rust/Cargo.toml": '[package]\nname = "rust"\nversion = "0.1.0"\n',
        "rust/Cargo.lock": """version = 3
[[package]]
name = "rust"
version = "0.1.0"
""",
        "rust/src/main.rs": "fn main() { let a = 10; }",
    })

    tgt = rule_runner.get_target(Address("rust", target_name="rust", generated_name="package"))
    partitions = rule_runner.request(
        Partitions[CargoClippyFieldSet, PackageMetadata],
        [CargoClippyRequest.PartitionRequest((CargoClippyFieldSet.create(tgt),))],
    )

    results = []
    for partition in partitions:
        result = rule_runner.request(
            LintResult,
            [CargoClippyRequest.Batch("", partition.elements, partition.metadata)],
        )

        results.append(result)

    assert len(results) == 1
    assert results[0].exit_code == 0
    assert "unused variable: `a`" in results[0].stderr


def test_clippy_subsystem_run_error(rule_runner) -> None:
    rule_runner.set_options(["--clippy-args=['--', '-Dwarnings']"], env_inherit={"PATH"})

    rule_runner.write_files({
        "rust/BUILD": "cargo_package()",
        "rust/Cargo.toml": '[package]\nname = "rust"\nversion = "0.1.0"\n',
        "rust/Cargo.lock": """version = 3
[[package]]
name = "rust"
version = "0.1.0"
""",
        "rust/src/main.rs": "fn main() { let a = 10; }",
    })

    tgt = rule_runner.get_target(Address("rust", target_name="rust", generated_name="package"))
    partitions = rule_runner.request(
        Partitions[CargoClippyFieldSet, PackageMetadata],
        [CargoClippyRequest.PartitionRequest((CargoClippyFieldSet.create(tgt),))],
    )

    results = []
    for partition in partitions:
        result = rule_runner.request(
            LintResult,
            [CargoClippyRequest.Batch("", partition.elements, partition.metadata)],
        )

        results.append(result)

    assert len(results) == 1
    assert results[0].exit_code == 101
    assert "unused variable: `a`" in results[0].stderr
