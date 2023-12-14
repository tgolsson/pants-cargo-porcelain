python_extension(
    name="native",
    package=["//examples/python-package/native-component#library"],
    module_name="native_component.so",
    output_path="examples/python-package/src/python_package",
)

pex_binary(
    name="pex",
    entry_point="python_package.main",
    dependencies=[":native"],
)

python_sources(
    run_goal_use_sandbox=True,
    dependencies=[":native"],
)
