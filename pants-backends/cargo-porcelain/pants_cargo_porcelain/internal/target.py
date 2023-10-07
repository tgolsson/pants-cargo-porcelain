from pants.engine.platform import Platform


def platform_to_target(platform: Platform):
    """Convert a Platform to a Rust target triple."""
    if platform == Platform.linux_x86_64:
        return "x86_64-unknown-linux-gnu"
    elif platform == Platform.linux_arm64:
        return "aarch64-unknown-linux-gnu"
    elif platform == Platform.macos_x86_64:
        return "x86_64-apple-darwin"
    elif platform == Platform.macos_arm64:
        return "aarch64-apple-darwin"
    else:
        raise Exception("Unknown platform")
