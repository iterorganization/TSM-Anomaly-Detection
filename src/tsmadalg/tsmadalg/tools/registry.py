"""
Algorithm discovery and registry.

Algorithm packages are discovered in the :mod:`tsmadalg.algorithms` package
directory. Additional local/developer algorithm folders can be discovered by
setting ``TSMADALG_EXT_PATH`` to a list of directories, separated by the
platform path separator (``:`` on Linux/macOS, ``;`` on Windows). Each
directory listed there is treated like an additional algorithms root.
"""

from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
import inspect
import os

from tsmadalg import algorithms
from tsmadkit import AnomalyDetection

ENV_ALGORITHM_PATH = "TSMADALG_EXT_PATH"


def _get_algorithm_roots() -> list[Path]:
    roots = [Path(algorithms.__file__).parent]

    for raw_path in os.environ.get(ENV_ALGORITHM_PATH, "").split(os.pathsep):
        raw_path = raw_path.strip()
        if not raw_path:
            continue

        path = Path(raw_path).expanduser().resolve()
        if path.is_dir() and path not in roots:
            roots.append(path)

    return roots


def _discover_algorithms() -> dict[str, Path]:
    """Return the discovered algorithm packages, as a mapping from name to directory."""
    found = {}
    for root in _get_algorithm_roots():
        if (root / "main.py").exists():
            candidates = [(root.name, root)]
        else:
            candidates = [
                (m.name, root / m.name)
                for m in iter_modules([str(root)])
                if m.ispkg
            ]

        for pkg_name, pkg_dir in candidates:
            # Built-in algorithms take precedence, then local roots in path order
            found.setdefault(pkg_name, pkg_dir)

    return found


def _load_algorithm(pkg_name: str, pkg_dir: Path) -> dict[str, object]:
    """Import an algorithm's ``main.py`` and return its registry entry."""
    # Make external algorithm folders importable as children of tsmadalg.algorithms
    path_str = str(pkg_dir.parent)
    if path_str not in algorithms.__path__:
        algorithms.__path__.append(path_str)

    module_name = f"{algorithms.__name__}.{pkg_name}.main"
    meta = {
        "name": pkg_name,
        "module": module_name,
        "class": None,
        "version": None,
        "status": "unavailable",
        "source": str(pkg_dir),
        "error_type": None,
        "error_message": None,
    }

    # One broken algorithm must not break the others
    try:
        algo_mod = import_module(module_name)
        classes = [
            obj for obj in vars(algo_mod).values()
            if inspect.isclass(obj)
            and issubclass(obj, AnomalyDetection)
            and obj.__module__ == module_name
        ]
        if len(classes) != 1:
            raise LookupError(
                f"main.py must define exactly one AnomalyDetection subclass, found {len(classes)}."
            )
    except Exception as exc:
        meta.update({"error_type": type(exc).__name__, "error_message": str(exc)})
        return meta

    meta.update(
        {
            "class": classes[0],
            "version": getattr(classes[0], "__version__", "unknown"),
            "status": "available",
        }
    )
    return meta


def list_algorithms(include_unavailable: bool = True) -> dict[str, dict[str, object]]:
    """
    Discover and import all anomaly detection algorithms, and return their registry entries.

    Parameters
    ----------
    include_unavailable : bool, default=True
        If False, only return algorithms whose implementation imported successfully.

    Returns
    -------
    dict[str, dict[str, object]]
        A dictionary where each key is the algorithm name and each value is
        a dictionary containing:

        - "name": the algorithm name
        - "module": the dotted module path of the algorithm's ``main.py``
        - "class": the algorithm class reference (subclass of AnomalyDetection),
          or ``None`` if discovery failed
        - "version": the algorithm version declared in the class attribute
          ``__version__``, or ``None`` if discovery failed
        - "status": either "available" or "unavailable"
        - "source": path to the directory containing the algorithm's ``main.py``
        - "error_type": the exception type name raised during discovery, or
          ``None`` if discovery succeeded
        - "error_message": the exception message raised during discovery, or
          ``None`` if discovery succeeded
    """
    registry = {
        name: _load_algorithm(name, pkg_dir)
        for name, pkg_dir in _discover_algorithms().items()
    }
    if include_unavailable:
        return registry
    return {
        name: meta
        for name, meta in registry.items()
        if meta["status"] == "available"
    }


def get_algorithm_class(name: str) -> type[AnomalyDetection]:
    """
    Return the algorithm class for a discovered and available algorithm.
    The class should inherit from `AnomalyDetection`.
    Only this algorithm is imported.

    Parameters
    ----------
    name: str
        The name of the algorithm to load.

    Returns
    -------
    type[AnomalyDetection]
        The loaded anomaly detection algorithm class that inherits from `AnomalyDetection`.

    Raises
    ------
    ValueError
        - If the specified algorithm name is not found.
        - If the algorithm is unavailable.
    """
    found = _discover_algorithms()
    if name not in found:
        raise ValueError(
            f"Unknown algorithm '{name}'. Available: {list(found)}"
        )

    meta = _load_algorithm(name, found[name])
    if meta["status"] != "available":
        reason = meta["error_message"] or "algorithm import failed"
        raise ValueError(f"Algorithm '{name}' is unavailable: {reason}")

    return meta["class"]
