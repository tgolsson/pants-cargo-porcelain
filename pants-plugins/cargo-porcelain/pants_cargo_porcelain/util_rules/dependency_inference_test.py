"""

"""

import pytest
from pants.build_graph.address import Address
from pants.core.util_rules import external_tool, source_files
from pants.engine.rules import QueryRule
from pants.engine.target import InferredDependencies
from pants.testutil.rule_runner import RuleRunner
from pants.util.ordered_set import FrozenOrderedSet

from pants_cargo_porcelain import register
from pants_cargo_porcelain.target_generator import rules as target_generator_rules
from pants_cargo_porcelain.util_rules import dependency_inference, sandbox, workspace


@pytest.fixture
def rule_runner():
    rule_runner = RuleRunner(
        rules=[
            *register.rules(),
            *dependency_inference.rules(),
            *source_files.rules(),
            *external_tool.rules(),
            *target_generator_rules(),
            *sandbox.rules(),
            *workspace.rules(),
            QueryRule(workspace.CargoPackageMapping, []),
        ],
        target_types=register.target_types(),
    )

    return rule_runner


def test_infer_dependency(rule_runner) -> None:
    rule_runner.write_files({
        "rust/BUILD": "cargo_package()",
        "rust/Cargo.toml": """
[package]
name = "test-with-path"
version = "0.1.0"
edition = "2021"

[dependencies]
inner-path = { path = "./inner-path" }
""",
        "rust/src/lib.rs": "",
        "rust/inner-path/BUILD": "cargo_package()",
        "rust/inner-path/Cargo.toml": """
[package]
name = "inner-path"
version = "0.1.0"
edition = "2021"
""",
        "rust/inner-path/Cargo.lock": "",
        "rust/inner-path/src/lib.rs": "",
    })

    tgt = rule_runner.get_target(Address("rust", target_name="rust", generated_name="library"))

    inferred_deps = rule_runner.request(
        InferredDependencies,
        [
            dependency_inference.InferCargoDependencies(
                dependency_inference.CargoDependenciesInferenceFieldSet.create(tgt)
            )
        ],
    )

    assert inferred_deps == InferredDependencies(
        FrozenOrderedSet([
            Address("rust/inner-path", generated_name="library"),
        ]),
    )


def test_root_package(rule_runner) -> None:
    rule_runner.write_files({
        "rust/BUILD": 'cargo_workspace(name="workspace")\ncargo_package()',
        "rust/Cargo.toml": """
[workspace]
[package]
name = "root"
version = "0.1.0"
edition = "2021"

[dependencies]
""",
        "rust/src/lib.rs": "",
    })

    rule_runner.request(
        workspace.CargoPackageMapping,
        [],
    )

    tgt = rule_runner.get_target(Address("rust", target_name="workspace"))

    inferred_deps = rule_runner.request(
        InferredDependencies,
        [
            dependency_inference.InferWorkspaceDependencies(
                dependency_inference.CargoWorkspaceDependenciesInferenceFieldSet.create(tgt)
            )
        ],
    )

    assert inferred_deps == InferredDependencies(
        FrozenOrderedSet([
            Address("rust", generated_name="sources"),
        ]),
    )
