from dataclasses import dataclass

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address, Addresses
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import (
    CoarsenedTargets,
    CoarsenedTargetsRequest,
    Dependencies,
    DependenciesRequest,
    Targets,
)

from pants_cargo_porcelain.target_types import CargoPackageSourcesField, CargoWorkspaceSourcesField


@dataclass(frozen=True)
class CargoSourcesRequest:
    addresses: frozenset[Address]


@rule
async def cargo_sources(request: CargoSourcesRequest) -> SourceFiles:
    print(request)
    targets = await Get(Targets, Addresses(request.addresses))
    target = targets[0]
    direct_dependencies = await Get(Targets, DependenciesRequest(target.get(Dependencies)))
    coarsened_targets = await Get(
        CoarsenedTargets,
        CoarsenedTargetsRequest([d.address for d in direct_dependencies]),
    )

    source_fields = []

    for tgt in coarsened_targets.closure():
        if tgt.has_field(CargoPackageSourcesField):
            source_fields.append(tgt[CargoPackageSourcesField])
        elif tgt.has_field(CargoWorkspaceSourcesField):
            source_fields.append(tgt[CargoWorkspaceSourcesField])

    source_fields.append(target[CargoPackageSourcesField])

    source_files = await Get(
        SourceFiles,
        SourceFilesRequest(
            [
                tgt[CargoPackageSourcesField]
                for tgt in transitive_targets.closure
                if tgt.has_field(CargoPackageSourcesField)
            ]
        ),
    )

    return source_files


def rules():
    return collect_rules()
