![Pants](https://img.shields.io/badge/Pants-2.24.1-%2355acee)

# Cargo porcelain for Pants

This repository is a plugin for Pants providing support for Rust. It does so by wrapping Cargo,
providing a very thin layer above the workflows you already know and love. This is a
work-in-progress and not feature complete. Contributions are very welcome. Please check out the
project issues to avoid double work!

The goal of this project is to maximize *utility* for adopters of Rust inside Pants, or Rust users
integrating other languages into the same repository. It is better to do an 80 % solution in one day
than to spend months waiting for the perfect design.

By extension, this package makes no stability guarantees until we start nearing feature completion,
but will attempt to follow semantic versioning when releasing new versions.
