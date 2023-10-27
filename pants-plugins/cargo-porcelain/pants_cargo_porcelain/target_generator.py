from __future__ import annotations

import json

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import GeneratedTargets, GenerateTargetsRequest
from pants.engine.unions import UnionRule

from pants_cargo_porcelain.internal.build import platform_to_target
from pants_cargo_porcelain.subsystems import RustSubsystem, RustupTool
from pants_cargo_porcelain.target_types import (
    CargoBinaryNameField,
    CargoBinaryTarget,
    CargoLibraryNameField,
    CargoLibraryTarget,
    CargoPackageDependenciesField,
    CargoPackageNameField,
    CargoPackageSourcesField,
    CargoPackageTarget,
    CargoPackageTargetImpl,
    CargoTestNameField,
    CargoTestTarget,
)
from pants_cargo_porcelain.util_rules.cargo import CargoProcessRequest
from pants_cargo_porcelain.util_rules.rustup import RustToolchain, RustToolchainRequest


class GenerateCargoTargetsRequest(GenerateTargetsRequest):
    generate_from = CargoPackageTarget


@rule
async def generate_cargo_generated_target(
    request: GenerateCargoTargetsRequest,
    rust: RustSubsystem,
    rustup: RustupTool,
    platform: Platform,
) -> GeneratedTargets:
    source_files, toolchain = await MultiGet(
        Get(
            SourceFiles,
            SourceFilesRequest(
                [request.generator.get(CargoPackageSourcesField)],
            ),
        ),
        Get(
            RustToolchain,
            RustToolchainRequest(
                rustup.rust_version, platform_to_target(platform), ("cargo", "rustfmt")
            ),
        ),
    )

    process_result = await Get(
        ProcessResult,
        CargoProcessRequest(
            toolchain,
            (
                "metadata",
                f"--manifest-path={request.generator.address.spec_path}/Cargo.toml",
                "--format-version=1",
                "--no-deps",
            ),
            source_files.snapshot.digest,
        ),
    )

    output = json.loads(process_result.stdout)
    targets_meta = output["packages"][0]["targets"]

    libraries = []
    binaries = []
    tests = []

    for target in targets_meta:
        if "bin" in target["kind"]:
            binaries.append(target)

        if "lib" in target["kind"]:
            libraries.append(target)

        if "test" in target["kind"]:
            tests.append(target)

    name = request.generator.address.create_generated("package")
    generated_targets = [
        CargoPackageTargetImpl(
            {
                CargoPackageNameField.alias: output["packages"][0]["name"],
                **request.template,
            },
            name,
        )
    ]
    generated_lib_names = []
    for target in libraries:
        name = request.generator.address.create_generated("library")
        generated_targets.append(
            CargoLibraryTarget(
                {
                    CargoLibraryNameField.alias: target["name"],
                    **request.template,
                },
                name,
            )
        )
        generated_lib_names.append(str(name))

    for target in binaries:
        name = request.generator.address.create_generated(target["name"])
        generated_targets.append(
            CargoBinaryTarget(
                {
                    CargoPackageDependenciesField.alias: generated_lib_names,
                    CargoBinaryNameField.alias: target["name"],
                    **request.template,
                },
                name,
            )
        )

    for target in tests:
        name = request.generator.address.create_generated(target["name"])
        generated_targets.append(
            CargoTestTarget(
                {
                    **request.template,
                    CargoPackageDependenciesField.alias: generated_lib_names,
                    CargoTestNameField.alias: target["name"],
                    CargoPackageSourcesField.alias: [
                        *CargoPackageSourcesField.default,
                        "tests/**/*.rs",
                    ],
                },
                name,
            )
        )

    return GeneratedTargets(
        request.generator,
        generated_targets,
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(GenerateTargetsRequest, GenerateCargoTargetsRequest),
    ]
