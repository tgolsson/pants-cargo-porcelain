from __future__ import annotations

import json

from pants.core.goals.package import OutputPathField
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.internals.selectors import Get, MultiGet
from pants.engine.platform import Platform
from pants.engine.process import ProcessResult
from pants.engine.rules import collect_rules, rule
from pants.engine.target import GeneratedTargets, GenerateTargetsRequest
from pants.engine.unions import UnionMembership, UnionRule

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
    CargoSourcesTarget,
    CargoTestNameField,
    CargoTestTarget,
    _CargoSourcesMarker,
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
    union_membership: UnionMembership,
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

        if "lib" in target["kind"] or "cdylib" in target["kind"]:
            libraries.append(target)

        if "test" in target["kind"]:
            tests.append(target)

    sources = request.generator.address.create_generated("sources")
    sources_address = str(sources)

    package = request.generator.address.create_generated("package")
    package_address = str(package)

    def _filter_target_fields(template, target):
        target_field_names = {t.alias for t in target.class_field_types(union_membership)}
        return {k: v for k, v in template.items() if k in target_field_names}

    generated_targets = [
        CargoSourcesTarget(
            {
                **_filter_target_fields(request.template, CargoSourcesTarget),
                _CargoSourcesMarker.alias: "yes",
            },
            sources,
        ),
        CargoPackageTargetImpl(
            {
                **_filter_target_fields(request.template, CargoPackageTargetImpl),
                CargoPackageNameField.alias: output["packages"][0]["name"],
                CargoPackageDependenciesField.alias: [sources_address],
            },
            package,
        ),
    ]

    generated_lib_names = []
    for target in libraries:
        name = request.generator.address.create_generated("library")
        generated_targets.append(
            CargoLibraryTarget(
                {
                    CargoLibraryNameField.alias: target["name"],
                    CargoPackageDependenciesField.alias: [package_address],
                    **_filter_target_fields(request.template, CargoLibraryTarget),
                    OutputPathField.alias: request.generator.get(OutputPathField).value,
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
                    CargoPackageDependenciesField.alias: [package_address],
                    CargoBinaryNameField.alias: target["name"],
                    OutputPathField.alias: request.generator.get(OutputPathField).value,
                    **_filter_target_fields(request.template, CargoBinaryTarget),
                },
                name,
            )
        )

    for target in tests:
        name = request.generator.address.create_generated(target["name"])
        generated_targets.append(
            CargoTestTarget(
                {
                    **_filter_target_fields(request.template, CargoTestTarget),
                    CargoPackageDependenciesField.alias: [package_address],
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
