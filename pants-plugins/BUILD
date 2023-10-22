pants_requirements(name="pants", resolve="pants-plugins")

python_requirements(
    name="python-requirements-pants-plugins",
        source="cargo-porcelain/pyproject.toml",
        resolve="pants-plugins",
    )

python_requirement(
    name="pytest-base",
    requirements=[
        "pytest-cov!=2.12.1,<3.1,>=2.12",
        "pytest-xdist<3,>=2.5",
        "pytest==7.0.*",
    ],
    resolve="pants-plugins",
)

name_to_constraint = {
    "pants-current": "==2.18.0rc3", # TBD[TSolberg]: Developing against 2.18 until 2.18.0 is released.
    "pants-next": "==2.19.0.dev0",
}

for name, constraint in name_to_constraint.items():
    pants_requirements(
        name=name,
        resolve=name,
        version_spec=constraint,
    )

    python_requirements(
        name=f"python-requirements-{name}",
        source="cargo-porcelain/pyproject.toml",
        resolve=name,
    )

    python_requirement(
        name=f"pytest-{name}",
        requirements=[
            "pytest-cov!=2.12.1,<3.1,>=2.12",
            "pytest-xdist<3,>=2.5",
            "pytest==7.0.*",
        ],
        resolve=name,
    )

all_targets = ("pants-plugins", *tuple(name_to_constraint.keys()))

__defaults__(
    {
        (python_sources, python_tests): dict(resolve=parametrize(*all_targets)),
    }
)
