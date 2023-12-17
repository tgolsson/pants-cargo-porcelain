from pants.build_graph.build_file_aliases import BuildFileAliases

from . import targets


def rules():
    return [*targets.rules()]


def target_types():
    return [
        targets.PythonExtensionsTarget,
    ]


def build_file_aliases():
    return BuildFileAliases(
        objects={
            "rust_python_extension_settings": targets.CargoLibraryPythonExtensionSettings,
        }
    )
