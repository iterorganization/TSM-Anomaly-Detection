"""
State helpers for reference data, history manifests, and derived cache files.

This module keeps the on-disk reference-state files used by anomaly detectors
consistent with the algorithm configuration and the raw history samples.
"""

from hashlib import sha256
from os.path import relpath
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict

from tsmadkit.io import read_hdf5_input_data, read_json, write_json
from tsmadkit.signals import SignalSet, SignalSpec
from tsmadkit.types import NonEmptyStr


def file_sha256(path: str | Path) -> str:
    """
    Compute the SHA-256 hash of a file.

    Parameters
    ----------
    path : str or Path
        Path to the file to hash.

    Returns
    -------
    str
        Hexadecimal SHA-256 digest of the file contents.
    """
    digest = sha256()
    with Path(path).open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class StateFileConfig(BaseModel):
    """
    Hash declaration for a referenced state file.
    """

    model_config = ConfigDict(extra="forbid")

    path: NonEmptyStr
    hash: NonEmptyStr


class CacheFileConfig(BaseModel):
    """
    Manifest entry for one cache file and its history dependency.
    """

    model_config = ConfigDict(extra="forbid")

    hash: NonEmptyStr
    depends_on: NonEmptyStr
    dependency_hash: NonEmptyStr


class ReferenceStateFileConfig(BaseModel):
    """
    Schema for the top-level reference state JSON file.
    """

    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr
    version: NonEmptyStr
    config_hash: NonEmptyStr
    history: StateFileConfig
    cache: StateFileConfig


class State:
    """
    Hash-tracked file on disk.

    ``State`` stores the path to a file and an optional hash declared by a
    manifest. It can then compare the declared hash against the current file
    contents.
    """

    def __init__(self, path: str | Path, declared_hash: str | None = None) -> None:
        """
        Parameters
        ----------
        path : str or Path
            Path to the tracked file.
        declared_hash : str, optional
            Expected hash recorded by a reference state or manifest.
        """
        self.path = Path(path)
        self.declared_hash = declared_hash

    @property
    def exists(self) -> bool:
        """
        Whether the tracked file exists on disk.
        """
        return self.path.is_file()

    @property
    def current_hash(self) -> str:
        """
        Current SHA-256 hash of the tracked file.

        Returns
        -------
        str
            Hexadecimal SHA-256 digest of the file contents.

        Raises
        ------
        FileNotFoundError
            If the tracked file does not exist.
        """
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self.path}")
        return file_sha256(self.path)

    @property
    def matches_declared_hash(self) -> bool:
        """
        Whether the current file hash matches the declared hash.

        Returns
        -------
        bool
            ``True`` when the file exists and its current SHA-256 hash equals
            the declared hash, otherwise ``False``.
        """
        return self.exists and self.declared_hash == self.current_hash

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"path={str(self.path)!r}, "
            f"declared_hash={self.declared_hash!r}"
            f")"
        )


class ManifestState(State):
    """
    JSON manifest stored next to the files it describes.

    Manifest states are regular :class:`State` objects with a JSON body. The
    manifest directory is treated as the root for related files, so subclasses
    can resolve history and cache entries relative to that location.
    """

    @property
    def root(self) -> Path:
        """
        Directory containing the manifest.
        """
        return self.path.parent

    @property
    def entries(self) -> dict[str, Any]:
        """
        Manifest entries loaded from disk.

        Returns
        -------
        dict
            Parsed manifest contents, or an empty dictionary if the manifest does
            not exist.
        """
        if not self.exists:
            return {}
        return read_json(self.path)

    def write(self, entries: dict[str, Any]) -> None:
        """
        Write manifest entries to disk.

        Parameters
        ----------
        entries : dict
            JSON-serializable manifest contents.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        write_json(entries, self.path)


class HistoryState(ManifestState):
    """
    Manifest for raw HDF5 history samples.

    The history manifest maps each ``*.h5`` file in the history directory to its
    current SHA-256 hash. It also knows how to load those files as
    :class:`SignalSet` instances using the configured signal specification.
    """

    def __init__(
        self,
        path: str | Path,
        declared_hash: str | None = None,
        signal_spec: SignalSpec | None = None,
    ) -> None:
        """
        Parameters
        ----------
        path : str or Path
            Path to the history manifest.
        declared_hash : str, optional
            Expected hash of the history manifest.
        signal_spec : SignalSpec, optional
            Signal specification used when loading HDF5 samples as
            :class:`SignalSet` instances.
        """
        super().__init__(path, declared_hash)
        self.signal_spec = signal_spec

    def update(self) -> None:
        """
        Refresh the history manifest from HDF5 files in the history directory.

        The manifest maps each ``*.h5`` file name to its current SHA-256 hash.
        """
        entries = {
            file.name: file_sha256(file)
            for file in sorted(self.root.glob("*.h5"))
            if file.is_file()
        }
        self.write(entries)

    def read(self, name: str, signal_spec: SignalSpec | None = None) -> SignalSet:
        """
        Read a history sample as a :class:`SignalSet`.

        Parameters
        ----------
        name : str
            File name declared in the history manifest.
        signal_spec : SignalSpec, optional
            Signal specification to use for this read. If omitted, the signal
            specification stored on the history state is used.

        Returns
        -------
        SignalSet
            Loaded history sample using this history state's signal
            specification.
        """
        signal_spec = signal_spec or self.signal_spec
        if signal_spec is None:
            raise ValueError("HistoryState requires a signal_spec to read samples.")
        data = read_hdf5_input_data(self.root / name)
        return SignalSet(data, signal_spec)

    @property
    def data(self) -> dict[str, SignalSet]:
        """
        Loaded history samples.

        Returns
        -------
        dict[str, SignalSet]
            Mapping from history file name to loaded sample.
        """
        return {
            name: self.read(name)
            for name in self.entries
        }


class CacheState(ManifestState):
    """
    Cache manifest and feature files derived from history samples.

    Each cache file stores the dictionary returned by an algorithm's
    ``transform()`` method for one history sample. The cache manifest records
    both the cache file hash and the hash of the history file it depends on, so
    stale cache files can be rebuilt without rewriting valid entries.
    """

    def __init__(
        self,
        path: str | Path,
        declared_hash: str | None = None,
        history: HistoryState | None = None,
    ) -> None:
        """
        Parameters
        ----------
        path : str or Path
            Path to the cache manifest.
        declared_hash : str, optional
            Expected hash of the cache manifest.
        history : HistoryState, optional
            History state from which cache files are derived.
        """
        super().__init__(path, declared_hash)
        self.history = history
        self._data: dict[str, np.ndarray] | None = None

    @property
    def entries(self) -> dict[str, CacheFileConfig]:
        """
        Cache manifest entries loaded from disk.

        Returns
        -------
        dict[str, CacheFileConfig]
            Mapping from cache file name to validated cache metadata.
        """
        return {
            name: CacheFileConfig.model_validate(config)
            for name, config in super().entries.items()
        }

    def update(self, transformer, *, rebuild_all: bool = False) -> None:
        """
        Update cache files and rewrite the cache manifest.

        Parameters
        ----------
        transformer : callable
            Function that converts a history :class:`SignalSet` into a dictionary
            of array-like cached data.
        rebuild_all : bool, default=False
            Whether to rebuild every cache file regardless of dependency hashes.
        """
        if self.history is None:
            raise ValueError("CacheState requires a history to update.")

        # Prepare cache bookkeeping from the previous manifest
        self.root.mkdir(parents=True, exist_ok=True)
        entries = {}
        old_entries = self.entries

        # Walk the current history manifest and decide which cache files are stale
        for history_name, history_hash in self.history.entries.items():
            cache_name = self._cache_name(history_name)
            cache_path = self.root / cache_name
            old = old_entries.get(cache_name)

            needs_rebuild = (
                rebuild_all
                or old is None
                or not cache_path.is_file()
                or old.dependency_hash != history_hash
                or old.hash != file_sha256(cache_path)
            )

            if needs_rebuild:
                # Rebuild only missing or stale cache files unless a full rebuild is required
                data = transformer(self.history.read(history_name))
                if not isinstance(data, dict):
                    raise TypeError("transform() must return a dict.")
                np.savez(cache_path, **data)

            # Record the cache hash and its exact history dependency
            entries[cache_name] = {
                "hash": file_sha256(cache_path),
                "depends_on": Path(
                    relpath(self.history.root / history_name, start=self.root)
                ).as_posix(),
                "dependency_hash": history_hash,
            }

        # Publish the refreshed manifest and invalidate the in-memory cache view.
        self.write(entries)
        self._data = None

    @property
    def data(self) -> dict[str, np.ndarray]:
        """
        Cached data loaded from cache files.

        Returns
        -------
        dict[str, ndarray]
            Mapping from cached field name to arrays stacked across all cache
            files.
        """
        if self._data is None:
            rows = []
            for cache_name in sorted(self.entries):
                with np.load(self.root / cache_name, allow_pickle=False) as loaded:
                    rows.append({key: loaded[key] for key in loaded.files})
            self._data = stack_cache_rows(rows)

        return self._data

    def _cache_name(self, history_name: str) -> str:
        """
        Return the cache file name derived from a history file name.
        """
        return f"{Path(history_name).stem}.npz"


class ReferenceState:
    """
    Top-level reference state for one configured algorithm.

    A reference state ties the algorithm identity, algorithm configuration,
    history manifest, and cache manifest together. It owns the lifecycle that
    creates missing manifests, refreshes history in full-check mode, rebuilds
    stale cache files, and records the hashes that make later fast checks cheap.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        name: str,
        version: str,
        config_hash: str,
        signal_spec: SignalSpec,
    ) -> None:
        """
        Parameters
        ----------
        path : str or Path
            Path to the reference state JSON file.
        name : str
            Current algorithm name.
        version : str
            Current algorithm version.
        config_hash : str
            Current algorithm configuration hash.
        signal_spec : SignalSpec
            Signal specification used to load history samples.
        """
        self.path = Path(path)
        self.root = self.path.parent
        self.name = name
        self.version = version
        self.config_hash = config_hash
        self.signal_spec = signal_spec

        # Hash of the reference state file, only known once setup() has written it
        self.hash = None

        # Bootstrap conventional manifest paths when no reference state exists yet
        config = self._read_config()
        if config is None:
            history_path = self.root / "history" / "manifest.json"
            cache_path = self.root / "cache" / "manifest.json"
            history_hash = None
            cache_hash = None
        else:
            history_path = self.root / config.history.path
            cache_path = self.root / config.cache.path
            history_hash = config.history.hash
            cache_hash = config.cache.hash

        self.history = HistoryState(
            history_path,
            declared_hash=history_hash,
            signal_spec=signal_spec,
        )
        self.cache = CacheState(
            cache_path,
            declared_hash=cache_hash,
            history=self.history,
        )

    def setup(self, *, check: Literal["fast", "full"], transformer) -> None:
        """
        Prepare the reference state, history manifest, and cache manifest.

        Parameters
        ----------
        check : {"fast", "full"}
            Check mode. ``"full"`` refreshes the history manifest from HDF5 files;
            ``"fast"`` trusts an existing history manifest.
        transformer : callable
            Function used to derive cache entries from history samples.

        Notes
        -----
        On first use, when no reference state file, history manifest, or
        cache manifest exists yet, this method creates all three: the
        history manifest is built from the ``*.h5`` files under
        ``history/``, the cache manifest and its ``.npz`` files are built by
        calling `transformer` once per history sample, and the reference
        state file is written last to record what was just built.
        """
        if check not in ("fast", "full"):
            raise ValueError("Reference state check must be either 'fast' or 'full'.")

        # Algorithm identity/configuration changes invalidate all derived cache files
        config = self._read_config()
        rebuild_all = self._requires_full_cache_rebuild(config)

        # Full checks refresh raw history hashes; fast checks trust an existing manifest
        if check == "full" or not self.history.exists:
            self.history.update()

        # Cache updates still skip valid files unless the algorithm state changed
        self.cache.update(transformer, rebuild_all=rebuild_all)
        self.write()

    def write(self) -> None:
        """
        Write the reference state JSON file.

        The written state records the current algorithm name, version,
        configuration hash, history manifest hash, and cache manifest hash.
        The hash of the written file is then stored in :attr:`hash`, which
        identifies the whole reference state.
        """
        self.root.mkdir(parents=True, exist_ok=True)
        state = {
            "name": self.name,
            "version": self.version,
            "config_hash": self.config_hash,
            "history": {
                "path": Path(
                    relpath(self.history.path, start=self.root)
                ).as_posix(),
                "hash": file_sha256(self.history.path),
            },
            "cache": {
                "path": Path(
                    relpath(self.cache.path, start=self.root)
                ).as_posix(),
                "hash": file_sha256(self.cache.path),
            },
        }
        write_json(state, self.path)

        self.hash = file_sha256(self.path)
        self.history.declared_hash = state["history"]["hash"]
        self.cache.declared_hash = state["cache"]["hash"]

    def _read_config(self) -> ReferenceStateFileConfig | None:
        """
        Read the reference state file if it exists.

        Returns
        -------
        ReferenceStateFileConfig or None
            Parsed reference state configuration, or ``None`` when the file does
            not exist yet.
        """
        if not self.path.is_file():
            return None
        return ReferenceStateFileConfig.model_validate(read_json(self.path))

    def _requires_full_cache_rebuild(
        self,
        config: ReferenceStateFileConfig | None,
    ) -> bool:
        """
        Determine whether all cache files should be rebuilt.

        Parameters
        ----------
        config : ReferenceStateFileConfig or None
            Previously recorded reference state.

        Returns
        -------
        bool
            ``True`` when the algorithm name, version, or configuration hash has
            changed since the previous reference state was written.
        """
        if config is None:
            return False
        return (
            config.name != self.name
            or config.version != self.version
            or config.config_hash != self.config_hash
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"path={str(self.path)!r}, "
            f"name={self.name!r}, "
            f"version={self.version!r}, "
            f"config_hash={self.config_hash!r}, "
            f"history_path={str(self.history.path)!r}, "
            f"cache_path={str(self.cache.path)!r}"
            f")"
        )


def stack_cache_rows(rows: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    """
    Stack cached data rows by field name.

    Parameters
    ----------
    rows : list of dict[str, ndarray]
        Per-cache-file dictionaries loaded from ``.npz`` files.

    Returns
    -------
    dict[str, ndarray]
        Mapping from cached field name to arrays stacked along axis 0.

    Raises
    ------
    ValueError
        If cache files do not all contain the same field names.
    """
    if not rows:
        return {}

    keys = tuple(sorted(rows[0]))
    if any(set(row) != set(keys) for row in rows):
        raise ValueError("Cache files do not all contain the same fields.")

    return {
        key: np.stack([row[key] for row in rows], axis=0)
        for key in keys
    }
