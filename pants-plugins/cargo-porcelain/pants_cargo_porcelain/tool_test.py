import pytest
from pants.core.util_rules import external_tool
from pants.core.util_rules.external_tool import DownloadedExternalTool, ExternalToolRequest
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.subsystems import rules as subsystem_rules
from pants_cargo_porcelain.tool import InstalledRustTool, Machete, RustTool, RustToolRequest
from pants_cargo_porcelain.tool import rules as tool_rules
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest
from pants_cargo_porcelain.util_rules.rustup import rules as rustup_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *external_tool.rules(),
            *subsystem_rules(),
            *tool_rules(),
            *rustup_rules(),
            QueryRule(InstalledRustTool, [RustToolRequest]),
            QueryRule(Machete, []),
        ]
    )


def test_platform_install_machete(
    rule_runner,
):
    machete = rule_runner.request(Machete, [])
    rule_runner.request(InstalledRustTool, RustToolRequest, machete.as_tool_request())
