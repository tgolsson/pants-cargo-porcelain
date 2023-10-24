from __future__ import annotations

import os
from dataclasses import dataclass

from pants.core.goals.tailor import (
    AllOwnedSources,
    PutativeTarget,
    PutativeTargets,
    PutativeTargetsRequest,
)
from pants.engine.fs import DigestContents, PathGlobs
from pants.engine.internals.selectors import Get
from pants.engine.rules import collect_rules, rule
from pants.engine.unions import UnionRule
from pants.util.dirutil import group_by_dir
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import CargoPackageTarget


@dataclass(frozen=True)
class PutativeCargoTargetsRequest(PutativeTargetsRequest):
    pass


@rule(level=LogLevel.DEBUG, desc="Determine candidate Cargo targets to create")
async def find_putative_targets(
    req: PutativeCargoTargetsRequest,
    all_owned_sources: AllOwnedSources,
    rust: RustSubsystem,
    rustup: RustupTool,
) -> PutativeTargets:
    if not rust.tailor:
        return PutativeTargets()

    all_cargo_contents = await Get(DigestContents, PathGlobs, req.path_globs("Cargo.toml"))

    unowned_cargo_files = set(fc.path for fc in all_cargo_contents) - set(all_owned_sources)
    unowned_cargo_contents = {
        fc.path: fc.content for fc in all_cargo_contents if fc.path in unowned_cargo_files
    }

    pts = []

    for dirname, filenames in group_by_dir(unowned_cargo_files).items():
        if b"[package]" in unowned_cargo_contents[os.path.join(dirname, "Cargo.toml")]:
            pts.append(
                PutativeTarget.for_target_type(
                    CargoPackageTarget,
                    path=dirname,
                    name=None,
                    triggering_sources=sorted(filenames),
                )
            )

    return PutativeTargets(pts)


def rules():
    return [
        *collect_rules(),
        UnionRule(PutativeTargetsRequest, PutativeCargoTargetsRequest),
    ]
