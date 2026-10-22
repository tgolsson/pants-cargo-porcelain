"""Generated target names: one per cargo target, and none colliding."""

from __future__ import annotations

import pytest
from pants.build_graph.address import Address
from pants.engine.internals.scheduler import ExecutionError
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.target_types import SkipCargoTestsField
from pants_cargo_porcelain.testing import make_rule_runner, package_fixture


@pytest.fixture
def rule_runner() -> RuleRunner:
    return make_rule_runner()


def test_test_false_skips_tests(rule_runner: RuleRunner) -> None:
    files = package_fixture("pkg", main="fn main() {}")
    files["pkg/Cargo.toml"] += '\n[[bin]]\nname = "pkg"\npath = "src/main.rs"\ntest = false\n'
    rule_runner.write_files(files)
    assert rule_runner.get_target(Address("pkg", generated_name="pkg"))[SkipCargoTestsField].value
    library = rule_runner.get_target(Address("pkg", generated_name="library"))
    assert not library[SkipCargoTestsField].value


@pytest.mark.parametrize(
    "extra, message",
    [
        (
            '[[bin]]\nname = "package"\npath = "src/main.rs"\n',
            r"pkg: the bin target `package` would be generated as `#package`, which is "
            r"reserved",
        ),
        (
            '[[test]]\nname = "library"\npath = "tests/it.rs"\n',
            r"pkg: the test target `library` would be generated as `#library`, which is "
            r"reserved",
        ),
        (
            (
                '[[bin]]\nname = "dup"\npath = "src/main.rs"\n\n'
                '[[test]]\nname = "dup"\npath = "tests/it.rs"\n'
            ),
            r"pkg: the bin target and the test target `dup` would both be generated as " r"`#dup`",
        ),
    ],
)
def test_generated_name_collisions(rule_runner: RuleRunner, extra: str, message: str) -> None:
    files = package_fixture("pkg", main="fn main() {}")
    files["pkg/Cargo.toml"] += f"\n{extra}"
    files["pkg/tests/it.rs"] = ""
    rule_runner.write_files(files)
    with pytest.raises(ExecutionError, match=message):
        rule_runner.get_target(Address("pkg", generated_name="library"))
