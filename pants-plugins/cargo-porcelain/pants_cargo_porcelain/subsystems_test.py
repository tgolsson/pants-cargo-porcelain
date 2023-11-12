import pytest
from pants.core.util_rules import external_tool
from pants.core.util_rules.external_tool import DownloadedExternalTool, ExternalToolRequest
from pants.engine.platform import Platform
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.subsystems import RustupTool
from pants_cargo_porcelain.subsystems import rules as subsystem_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *external_tool.rules(),
            *subsystem_rules(),
            QueryRule(DownloadedExternalTool, [ExternalToolRequest]),
            QueryRule(RustupTool, []),
        ]
    )


@pytest.mark.parametrize(
    "platform",
    (
        Platform.linux_arm64,
        Platform.linux_x86_64,
        Platform.macos_arm64,
        Platform.macos_x86_64,
    ),
)
def test_platform_download_rustup(
    rule_runner,
    platform,
):
    rustup = rule_runner.request(RustupTool, [])
    rustup_binary = rule_runner.request(DownloadedExternalTool, [rustup.get_request(platform)])
