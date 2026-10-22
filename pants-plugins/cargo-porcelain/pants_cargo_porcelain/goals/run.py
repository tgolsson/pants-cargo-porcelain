"""`pants run` of a `cargo_binary`: the packaged binary, run from the sandbox with the build's
sources, staged packages and `env`."""

from __future__ import annotations

import os.path

from pants.core.goals.run import RunRequest
from pants.engine.fs import MergeDigests
from pants.engine.intrinsics import merge_digests
from pants.engine.rules import collect_rules, concurrently, implicitly, rule

from pants_cargo_porcelain.goals.package import CargoBinaryFieldSet, package_cargo_binary
from pants_cargo_porcelain.util_rules.sandbox import CargoSourcesRequest, cargo_sources


@rule
async def create_cargo_binary_run_request(field_set: CargoBinaryFieldSet) -> RunRequest:
    built, sources = await concurrently(
        package_cargo_binary(field_set, **implicitly()),
        cargo_sources(CargoSourcesRequest(frozenset([field_set.address]), include_packages=True)),
    )
    relpath = built.artifacts[0].relpath
    assert relpath is not None
    digest = await merge_digests(MergeDigests([built.digest, sources.digest]))
    return RunRequest(
        digest=digest, args=(os.path.join("{chroot}", relpath),), extra_env=sources.env
    )


def rules():
    return [*collect_rules(), *CargoBinaryFieldSet.rules()]
