from . import targets


def rules():
    return [*targets.rules()]


def target_types():
    return [targets.PythonExtensionsTarget]
