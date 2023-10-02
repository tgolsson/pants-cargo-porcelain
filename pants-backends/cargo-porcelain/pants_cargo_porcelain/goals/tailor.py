from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from pants.core.goals.tailor import (
    AllOwnedSources,
    PutativeTarget,
    PutativeTargets,
    PutativeTargetsRequest,
)
from pants.engine.fs import EMPTY_DIGEST, Digest, PathGlobs, Paths
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.source.filespec import FilespecMatcher
from pants.util.dirutil import group_by_dir
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import CargoPackageTarget
from pants_cargo_porcelain.util_rules.rustup import BOTH_CACHES, RustToolchain, RustToolchainRequest


@dataclass(frozen=True)
class PutativeCargoTargetsRequest(PutativeTargetsRequest):
    pass


@dataclass(frozen=True)
class CargoProcessRequest:
    toolchain: RustToolchain
    command: str

    digest: Digest = EMPTY_DIGEST


@dataclass(frozen=True)
class CargoProcess:
    request: Process


@rule(level=LogLevel.DEBUG, desc="Determine candidate Cargo targets to create")
async def make_cargo_process(
    req: CargoProcessRequest,
) -> CargoProcess:
    command = req.command
    toolchain = req.toolchain
    return CargoProcess(
        Process(
            argv=(toolchain.cargo, *command),
            input_digest=req.digest,
            description=f"Run {command} with {toolchain}",
            append_only_caches=BOTH_CACHES,
            level=LogLevel.DEBUG,
        )
    )


@rule(level=LogLevel.DEBUG, desc="Determine candidate Cargo targets to create")
async def find_putative_targets(
    req: PutativeCargoTargetsRequest,
    all_owned_sources: AllOwnedSources,
    rust: RustSubsystem,
    rustup: RustupTool,
) -> PutativeTargets:
    if not rust.tailor:
        return PutativeTargets()

    all_cargo_files, toolchain = await MultiGet(
        Get(Paths, PathGlobs, req.path_globs("Cargo.toml")),
        Get(
            RustToolchain,
            RustToolchainRequest(
                "1.72.1", "x86_64-unknown-linux-gnu", ("rustfmt", "cargo", "clippy")
            ),
        ),
    )

    unowned_cargo_files = set(all_cargo_files.files) - set(all_owned_sources)

    pts = []

    for dirname, filenames in group_by_dir(unowned_cargo_files).items():
        digest = await Get(
            Digest,
            PathGlobs(
                [
                    f"{dirname}/src/**/*",
                ]
                + [f"{dirname}/{f}" for f in filenames]
            ),
        )

        proc = await Get(
            CargoProcess,
            CargoProcessRequest(
                toolchain,
                ("metadata", f"--manifest-path={dirname}/Cargo.toml", "--no-deps"),
                digest,
            ),
        )
        process_result = await Get(ProcessResult, Process, proc.request)
        print(process_result.stdout.decode("utf-8"))
        print(process_result.stderr.decode("utf-8"))

        pts.append(
            PutativeTarget.for_target_type(
                CargoPackageTarget, path=dirname, name=None, triggering_sources=sorted(filenames)
            )
        )

    return PutativeTargets(pts)


def rules():
    return [
        *collect_rules(),
        UnionRule(PutativeTargetsRequest, PutativeCargoTargetsRequest),
    ]
