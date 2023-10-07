pants_requirements(name="pants", resolve="pants-plugins")

# name_to_constraint = {
#     "pants-216": ">=2.16.0a0,<2.17.0",
#     "pants-217": ">=2.17.0a0,<2.18.0",
#     "pants-218": "==2.18.0rc0",
# }

# pants_requirements(name="pants-plugins")

# for name, constraint in name_to_constraint.items():
#     pants_requirements(
#         name=name,
#         resolve=name,
#         version_spec=constraint,
#     )

# all_targets = ("pants-plugins", *tuple(name_to_constraint.keys()))

# __defaults__(
#     {
#         python_sources: dict(resolve=parametrize(*all_targets)),
#         python_tests: dict(
#             resolve=parametrize(all_targets[3]),
#         ),
#     }
# )


TOOLS = {
    "pytest": [
        "pytest-cov!=2.12.1,<3.1,>=2.12",
        "pytest-xdist<3,>=2.5",
        "pytest==7.0.*",
        "pytest-platform-markers",
        "pytest-rerunfailures",
    ],
    "black": ["black>=22.6.0,<24"],
    "ipython": ["ipython>=7.27.0,<8"],
    "isort": ["isort[pyproject,colors]>=5.9.3,<6.0"],
}

python_requirement(
    name="pytest-base",
    requirements=TOOLS["pytest"],
    resolve="pants-plugins",
)

for tool, reqs in TOOLS.items():
    python_requirement(
        name=tool,
        requirements=reqs,
        resolve=tool,
    )
