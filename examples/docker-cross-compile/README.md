# Cross-compilation using Docker

This example uses Docker to cross-compile to a different architecture, in this case, to the Raspberry Pi. To run this,

```console
pants package examples/docker-cross-compile::
```

This will build the docker cross compiler image and then compile the module, with a binary in `dist/examples.docker-cross-compile/hello-cross`. You can then copy this to an ARM64 machine running linux, e.g., a raspberry pi:

```console
export RPI_USER=username
export RPI_HOST=raspberry.local

scp -q dist/examples.docker-cross-compile/hello-cross ${RPI_USER}@${RPI_HOST}:/home/${RPI_USER}
ssh ${RPI_USER}@${RPI_HOST} -t './hello-cross'
```

You should see an output like
```
Successfully compiled for ARM architecture.
```

## Caveats

The code is designed to _not_ be able to compile and run except on a ARM64 / linux machine.  Thus, an attempt to use `pants run` will fail:

```console
pants run examples/docker-cross-compile/:hello-cross
12:36:37.72 [WARN] The `run` goal was called with target `examples/docker-cross-compile:hello-cross#hello-cross`, which specifies the environment `cross-compiler`, which is a `docker_environment`. The `run` goal only runs in the local environment. You may experience unexpected behavior.
12:36:38.43 [ERROR] 1 Exception encountered:

Engine traceback:
  in `run` goal

ProcessExecutionFailure: Process 'Run `cargo build --manifest-path=examples/docker-cross-compile/Cargo.toml --locked --bin=hello-cross`' failed with exit code 101.
stdout:

stderr:
   Compiling hello-cross v0.1.0 (/private/var/folders/rf/rvs4k7vx2c7b7hb0dsymb3nw0000gn/T/pants-sandbox-Fr4AzW/examples/docker-cross-compile)
[2024-10-04T19:36:38Z DEBUG sccache::config] Attempting to read config file at "/Users/michaelmccoy/Library/Application Support/Mozilla.sccache/config"
[2024-10-04T19:36:38Z DEBUG sccache::config] Couldn't open config file: failed to open file `/Users/michaelmccoy/Library/Application Support/Mozilla.sccache/config`
[2024-10-04T19:36:38Z DEBUG sccache::commands] Server sent UnhandledCompile
error: This program only compiles for ARM64 running Linux (e.g., Raspberry Pi).
 --> src/main.rs:2:1
  |
2 | compile_error!("This program only compiles for ARM64 running Linux (e.g., Raspberry Pi).");
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

error: could not compile `hello-cross` (bin "hello-cross") due to previous error



Use `--keep-sandboxes=on_failure` to preserve the process chroot for inspection.
```
