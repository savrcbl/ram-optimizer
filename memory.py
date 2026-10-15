import psutil

_GB = 1024 ** 3


def get_memory_stats() -> dict:
    """Return total/used/available RAM in GB and percent used."""
    vm = psutil.virtual_memory()
    return {
        "total_gb": round(vm.total / _GB, 1),
        "used_gb": round((vm.total - vm.available) / _GB, 1),
        "available_gb": round(vm.available / _GB, 1),
        "percent": round(vm.percent, 1),
    }


def is_memory_tight(threshold_percent: int) -> bool:
    """True when RAM usage is at or above the threshold."""
    return get_memory_stats()["percent"] >= threshold_percent


def get_available_mb() -> float:
    """Available system memory in MB (not rounded, for before/after comparisons)."""
    return psutil.virtual_memory().available / (1024 * 1024)
