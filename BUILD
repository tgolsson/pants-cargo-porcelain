TOOLS = {
    "pytest": [
        "pytest>=8,<9",
        "pytest-xdist>=3,<4",
        "pytest-cov>=5",
    ],
    "black": ["black>=22.6.0,<24"],
    "ipython": ["ipython>=7.27.0,<8"],
    "isort": ["isort[pyproject,colors]>=5.9.3,<6.0"],
}

for tool, reqs in TOOLS.items():
    python_requirement(
        name=tool,
        requirements=reqs,
        resolve=tool,
    )
