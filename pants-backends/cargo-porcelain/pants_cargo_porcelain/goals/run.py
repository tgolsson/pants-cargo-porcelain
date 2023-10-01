import os.path

from pants.backend.go.goals.package_binary import CargoBinaryFieldSet
from pants.core.goals.package import BuiltPackage, PackageFieldSet
from pants.core.goals.run import RunRequest
from pants.engine.internals.selectors import Get
from pants.engine.rules import collect_rules, rule


@rule
async def create_cargo_binary_run_request(field_set: CargoBinaryFieldSet) -> RunRequest:
    binary = await Get(BuiltPackage, PackageFieldSet, field_set)
    artifact_relpath = binary.artifacts[0].relpath
    assert artifact_relpath is not None
    return RunRequest(digest=binary.digest, args=(os.path.join("{chroot}", artifact_relpath),))


def rules():
    return [
        *collect_rules(),
        *CargoBinaryFieldSet.rules(),
    ]
