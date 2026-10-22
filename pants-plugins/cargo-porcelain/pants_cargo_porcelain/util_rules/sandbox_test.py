"""What a cargo sandbox holds: packageable dependencies staged but not walked through, and
the merged `env`."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pants.build_graph.address import Address
from pants.core.goals.package import BuiltPackage, BuiltPackageArtifact, PackageFieldSet
from pants.engine.fs import CreateDigest, Digest, DigestContents, FileContent
from pants.engine.internals.scheduler import ExecutionError
from pants.engine.intrinsics import create_digest
from pants.engine.rules import QueryRule, rule
from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies, Target
from pants.engine.unions import UnionRule
from pants.testutil.rule_runner import RuleRunner
from pants.util.frozendict import FrozenDict

from pants_cargo_porcelain.testing import make_rule_runner, package_fixture
from pants_cargo_porcelain.util_rules.sandbox import CargoSources, CargoSourcesRequest

LIBRARY = "build/libfake.a"


class FakeLibDependencies(Dependencies):
    pass


class FakeLibTarget(Target):
    """Stands in for another backend's library: packageable, with inputs."""

    alias = "fake_lib"
    core_fields = (*COMMON_TARGET_FIELDS, FakeLibDependencies)


@dataclass(frozen=True)
class FakeLibFieldSet(PackageFieldSet):
    required_fields = (FakeLibDependencies,)

    dependencies: FakeLibDependencies


@rule
async def package_fake_lib(field_set: FakeLibFieldSet) -> BuiltPackage:
    digest = await create_digest(CreateDigest([FileContent(LIBRARY, b"fake")]))
    return BuiltPackage(digest, (BuiltPackageArtifact(LIBRARY),))


@pytest.fixture
def rule_runner() -> RuleRunner:
    return make_rule_runner(
        [QueryRule(CargoSources, [CargoSourcesRequest]), QueryRule(DigestContents, [Digest])],
        rules=[package_fake_lib, UnionRule(PackageFieldSet, FakeLibFieldSet)],
        target_types=[FakeLibTarget],
    )


def _sources(rule_runner: RuleRunner, include_packages: bool) -> tuple[CargoSources, list[str]]:
    address = Address("hello", generated_name="package")
    sources = rule_runner.request(
        CargoSources, [CargoSourcesRequest(frozenset([address]), include_packages)]
    )
    contents = rule_runner.request(DigestContents, [sources.digest])
    return sources, [fc.path for fc in contents]


def test_packageable_dependency_is_staged_not_walked(rule_runner: RuleRunner) -> None:
    files = package_fixture("hello")
    files["hello/BUILD"] = (
        'cargo_package(dependencies=["lib", "data"], env=["LIB_DIR={chroot}/build"])'
    )
    files["lib/BUILD"] = 'fake_lib(dependencies=["third"])'
    files["third/BUILD"] = 'files(sources=["*.h"])'
    files["third/header.h"] = ""
    files["data/BUILD"] = 'files(sources=["*.txt"])'
    files["data/greeting.txt"] = "hello\n"
    rule_runner.write_files(files)

    sources, paths = _sources(rule_runner, include_packages=True)
    assert "data/greeting.txt" in paths
    assert LIBRARY in paths
    # The library's own inputs stay its backend's business.
    assert "third/header.h" not in paths
    assert sources.env == FrozenDict({"LIB_DIR": "{chroot}/build"})

    sources, paths = _sources(rule_runner, include_packages=False)
    assert "data/greeting.txt" in paths
    assert LIBRARY not in paths
    assert "third/header.h" not in paths
    assert sources.env == FrozenDict({"LIB_DIR": "{chroot}/build"})


@pytest.mark.parametrize("key", ["PATH", "RUSTFLAGS", "KACHE_BASE_DIR"])
def test_reserved_env_is_rejected(rule_runner: RuleRunner, key: str) -> None:
    files = package_fixture("hello")
    files["hello/BUILD"] = f'cargo_package(env=["{key}=x"])'
    rule_runner.write_files(files)
    with pytest.raises(ExecutionError, match=rf"hello.* sets `{key}` in `env`"):
        _sources(rule_runner, include_packages=False)
