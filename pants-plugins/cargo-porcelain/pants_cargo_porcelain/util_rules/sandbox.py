from dataclasses import dataclass

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import TransitiveTargets, TransitiveTargetsRequest

from pants_cargo_porcelain.target_types import CargoPackageSourcesField, CargoWorkspaceSourcesField


@dataclass(frozen=True)
class CargoSourcesRequest:
    addresses: frozenset[Address]


@rule
async def cargo_sources(request: CargoSourcesRequest) -> SourceFiles:
    all_targets = await Get(
        TransitiveTargets,
        TransitiveTargetsRequest(request.addresses),
    )

    source_fields = []
    for tgt in all_targets.closure:
        if tgt.has_field(CargoPackageSourcesField):
            source_fields.append(tgt[CargoPackageSourcesField])
        elif tgt.has_field(CargoWorkspaceSourcesField):
            source_fields.append(tgt[CargoWorkspaceSourcesField])

    source_files = await Get(
        SourceFiles,
        SourceFilesRequest(source_fields),
    )

    return source_files


def rules():
    return collect_rules()
