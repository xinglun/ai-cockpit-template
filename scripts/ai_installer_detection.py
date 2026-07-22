"""Detection boundary for supported installer inputs."""


def missing_runtime_scripts(names: set[str], available: set[str]) -> list[str]:
    return sorted(names - available)
