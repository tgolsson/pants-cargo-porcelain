resources(name="package_data", sources=["pyproject.toml", "README.md"])


python_distribution(
    name="package",
    dependencies=[
        ":package_data",
        "./native-component#library",
        "./src/python_package",
    ],
    provides=python_artifact(
        name="pants_backend_k8s",
        version="0.3.0",
        long_description_content_type="markdown",
    ),
    wheel_config_settings={"--global-option": ["--python-tag", "py38.py39"]},
)

shunit2_tests(
    name="tests",
    runtime_package_dependencies=[
        "./src/python_package:pex",
    ],
)
