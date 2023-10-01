from dataclasses import dataclass
from pants.engine.rules import collect_rules, rule, Get
from pants_cargo_porcelain.subsystems import RustupTool
from pants.engine.process import Process, ProcessResult
from pants.util.logging import LogLevel
from pants.util.frozendict import FrozenDict
from pants.core.util_rules.external_tool import (
    DownloadedExternalTool,
    ExternalToolRequest,
)
from pants.engine.platform import Platform

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


@dataclass(frozen=True)
class RustupBinary:
    path: str


@dataclass(frozen=True)
class RustupBinaryRequest:
    pass


@rule(desc="Get Rust toolchain", level=LogLevel.DEBUG)
def get_rustup_binary(
    req: RustupBinaryRequest, rustup: RustupTool, platform: Platform
) -> RustupBinary:
    rustup_tool = await Get(
        DownloadedExternalTool, ExternalToolRequest, rustup.get_request(platform)
    )
    res = await Get(
        ProcessResult,
        Process(
            argv=[rustup_tool.path, "--no-update-default-toolchain", "--no-modify-path"],
            input_digest=rustup_tool.digest,
            description="Installing Rustup",
            level=LogLevel.DEBUG,
            append_only_caches=BOTH_CACHES,
            env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
        ),
    )

    return RustupBinary(path=f"{CARGO_NAMED_CACHE}/bin/rustup")


@rule(desc="Get Rust toolchain", level=LogLevel.DEBUG)
def get_rust_toolchain(request: RustToolchainRequest) -> RustToolchain:
    rustup_binary = Get(RustupBinary, RustupBinaryRequest())

    _ = await Get(
        ProcessResult,
        Process(
            argv=[rustup_binary.path, "toolchain", "install", request.version],
            input_digest=(),
            description="Installing Rustup",
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
            input_digest=(),
            description="Installing Rustup",
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
            input_digest=(),
            description="Installing Rustup",
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
                "component",
                "add",
                f"--toolchain={request.version}",
                *request.components,
            ],
            input_digest=(),
            description="Installing Rustup",
            level=LogLevel.DEBUG,
            append_only_caches=BOTH_CACHES,
            env={"RUSTUP_HOME": RUSTUP_NAMED_CACHE, "CARGO_HOME": CARGO_NAMED_CACHE},
        ),
    )


def rules():
    return [
        *collect_rules(),
    ]
