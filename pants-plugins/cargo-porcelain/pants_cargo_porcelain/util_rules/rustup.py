import fcntl
import os
from dataclasses import dataclass

from pants.base.build_environment import get_pants_cachedir
from pants.core.util_rules.external_tool import DownloadedExternalTool, ExternalToolRequest
from pants.engine.fs import EMPTY_DIGEST
from pants.engine.platform import Platform
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import Get, collect_rules, rule
from pants.util.frozendict import FrozenDict
from pants.util.logging import LogLevel

from pants_cargo_porcelain.subsystems import RustupTool

RUSTUP_NAMED_CACHE = ".rustup"
RUSTUP_APPEND_ONLY_CACHES = FrozenDict({"rustup": RUSTUP_NAMED_CACHE})

CARGO_NAMED_CACHE = ".cargo"
CARGO_APPEND_ONLY_CACHES = FrozenDict({"cargo": CARGO_NAMED_CACHE})

BOTH_CACHES = FrozenDict({**RUSTUP_APPEND_ONLY_CACHES, **CARGO_APPEND_ONLY_CACHES})


@dataclass(frozen=True)
class RustToolchainRequest:
    version: str
    target: str
    components: tuple[str, ...]

    def __str__(self) -> str:
        return f"rust-{self.version}-{self.target}"


@dataclass(frozen=True)
class RustToolchain:
    path: str
    version: str
    target: str

    ok: bool

    @property
    def cargo(self) -> str:
        return f"{self.path}/bin/cargo"


@dataclass(frozen=True)
class RustupBinary:
    path: str


@dataclass(frozen=True)
class RustupBinaryRequest:
    pass


@rule(desc="Get RustUp", level=LogLevel.DEBUG)
async def get_rustup_binary(
    req: RustupBinaryRequest, rustup: RustupTool, platform: Platform
) -> RustupBinary:
    rustup_tool = await Get(
        DownloadedExternalTool, ExternalToolRequest, rustup.get_request(platform)
    )
    _ = await Get(
        ProcessResult,
        Process(
            argv=[rustup_tool.exe, "--no-update-default-toolchain", "--no-modify-path", "-y"],
            input_digest=rustup_tool.digest,
            description="Installing Rustup",
            level=LogLevel.DEBUG,
            append_only_caches=BOTH_CACHES,
            env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
        ),
    )

    return RustupBinary(path=f"{CARGO_NAMED_CACHE}/bin/rustup")


class FileLock:
    def __init__(self, path: str):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        open_mode = os.O_RDWR | os.O_CREAT | os.O_TRUNC
        fd = os.open(path, open_mode)
        self._fd = fd

    def __enter__(self):
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._fd:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)

        self._fd = None


@rule(desc="Get Rust toolchain", level=LogLevel.DEBUG)
async def get_rust_toolchain(request: RustToolchainRequest) -> RustToolchain:
    rustup_binary = await Get(RustupBinary, RustupBinaryRequest())
    lock_file_path = os.path.join(get_pants_cachedir(), "locks", ".rustup")
    with FileLock(lock_file_path):
        _ = await Get(
            ProcessResult,
            Process(
                argv=[
                    rustup_binary.path,
                    "toolchain",
                    "install",
                    "--no-self-update",
                    request.version,
                ],
                input_digest=EMPTY_DIGEST,
                description=f"Installing Rust {request.version}",
                level=LogLevel.DEBUG,
                append_only_caches=BOTH_CACHES,
                env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
            ),
        )

        _ = await Get(
            ProcessResult,
            Process(
                argv=[
                    rustup_binary.path,
                    "target",
                    "add",
                    f"--toolchain={request.version}",
                    request.target,
                ],
                input_digest=EMPTY_DIGEST,
                description=f"Installing target {request.target} for toolchain {request.version}",
                level=LogLevel.DEBUG,
                append_only_caches=BOTH_CACHES,
                env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
            ),
        )

        if request.components:
            _ = await Get(
                ProcessResult,
                Process(
                    argv=[
                        rustup_binary.path,
                        "component",
                        "add",
                        f"--toolchain={request.version}",
                        *request.components,
                    ],
                    input_digest=EMPTY_DIGEST,
                    description=(
                        f"Installing components {request.components} for toolchain"
                        f" {request.version}"
                    ),
                    level=LogLevel.DEBUG,
                    append_only_caches=BOTH_CACHES,
                    env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
                ),
            )

        return RustToolchain(
            path=f"{RUSTUP_NAMED_CACHE}/toolchains/{request.version}-{request.target}",
            version=request.version,
            target=request.target,
            ok=True,
        )


def rules():
    return [
        *collect_rules(),
    ]
