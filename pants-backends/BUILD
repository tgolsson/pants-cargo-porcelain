pants_requirements(name="pants", resolve="pants-plugins")

name_to_constraint = {
    "pants-215": ">=2.15.0a0,<2.16.0",
    "pants-216": ">=2.16.0a0,<2.17.0",
    "pants-217": "==2.17.0rc1",
}

pants_requirements(name="pants-plugins")

for name, constraint in name_to_constraint.items():
    pants_requirements(
        name=name,
        resolve=name,
        version_spec=constraint,
    )

all_targets = ("pants-plugins", *tuple(name_to_constraint.keys()))

__defaults__(
    {
        python_sources: dict(resolve=parametrize(*all_targets)),
        python_tests: dict(
            resolve=parametrize(*all_targets[1:]),
        ),
    }
)
