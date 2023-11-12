from dataclasses import dataclass

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import TransitiveTargets, TransitiveTargetsRequest

from pants_cargo_porcelain.target_types import CargoPackageSourcesField


@dataclass(frozen=True)
class CargoSourcesRequest:
    addresses: frozenset[Address]


@rule
async def cargo_sources(request: CargoSourcesRequest) -> SourceFiles:
    transitive_targets = await Get(TransitiveTargets, TransitiveTargetsRequest(request.addresses))

    source_files = await Get(
        SourceFiles,
        SourceFilesRequest([
            tgt[CargoPackageSourcesField]
            for tgt in transitive_targets.closure
            if tgt.has_field(CargoPackageSourcesField)
        ]),
    )

    return source_files


def rules():
    return collect_rules()
