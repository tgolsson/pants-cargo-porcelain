import pytest
from pants.core.util_rules import external_tool
from pants.core.util_rules.external_tool import DownloadedExternalTool, ExternalToolRequest
from pants.engine.platform import Platform
from pants.engine.rules import QueryRule
from pants.testutil.rule_runner import RuleRunner

from pants_cargo_porcelain.tools.binstall import BinstallTool
from pants_cargo_porcelain.tools.binstall import rules as binstall_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *external_tool.rules(),
            *binstall_rules(),
            QueryRule(DownloadedExternalTool, [ExternalToolRequest]),
            QueryRule(BinstallTool, []),
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
    binstall = rule_runner.request(BinstallTool, [])
    rule_runner.request(DownloadedExternalTool, [binstall.get_request(platform)])
