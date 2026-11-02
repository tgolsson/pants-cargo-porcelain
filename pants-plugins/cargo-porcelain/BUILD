# pants_backend_cc and pants_backend_platforms are unpublished, so pyproject.toml pins them to a
# pants-backends commit. pex identifies a VCS artifact by its URL without the fragment, which
# would lock two subdirectories of one commit as the same artifact; cc spells the commit
# abbreviated and platforms in full. pip fetches an abbreviated SHA only while the commit is
# reachable from a branch, so repin once it is on main.
python_requirements(
    name="reqs",
    source="pyproject.toml",
)

resources(name="package_data", sources=["pyproject.toml", "LICENSE-APACHE"])

# The clippy sub-backend is enabled on its own, so nothing imports it: listed by hand.
python_distribution(
    name="package",
    dependencies=[
        ":package_data",
        "./pants_cargo_porcelain",
        "./pants_cargo_porcelain/backends/clippy",
        "./pants_cargo_porcelain/backends/clippy/goals",
    ],
    provides=python_artifact(name="pants_cargo_porcelain", version="0.4.0"),
)
