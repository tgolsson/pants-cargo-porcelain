import pytest
from pants.core.util_rules import external_tool
from pants.engine.process import rules as process_rules
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.subsystems import rules as subsystem_rules
from pants_cargo_porcelain.tool import InstalledRustTool, RustToolRequest, Sccache
from pants_cargo_porcelain.tool import rules as tool_rules
from pants_cargo_porcelain.tool_rules import rules as tool_rules_rules
from pants_cargo_porcelain.tools.binstall import binstall_rules
from pants_cargo_porcelain.util_rules.cargo import rules as cargo_rules
from pants_cargo_porcelain.util_rules.rustup import rules as rustup_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *external_tool.rules(),
            *subsystem_rules(),
            *tool_rules(),
            *rustup_rules(),
            *process_rules(),
            *cargo_rules(),
            *tool_rules_rules(),
            *binstall_rules(),
            QueryRule(InstalledRustTool, [RustToolRequest]),
            QueryRule(Sccache, []),
        ]
    )


def test_platform_install_sccache(
    rule_runner,
):
    rule_runner.set_options(["--binstall-enable"])
    sccache = rule_runner.request(Sccache, [])
    rule_runner.request(InstalledRustTool, [sccache.as_tool_request()])
