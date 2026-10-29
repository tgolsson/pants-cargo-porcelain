# pants_backend_cc and pants_backend_platforms are unpublished, so pyproject.toml pins them to a
# pants-backends commit. pex identifies a VCS artifact by its URL without the fragment, which
# would lock two subdirectories of one commit as the same artifact; cc spells the commit
# abbreviated and platforms in full. pip fetches an abbreviated SHA only while the commit is
# reachable from a branch, so repin once it is on main.
python_requirements(
    name="reqs",
    source="pyproject.toml",
)
