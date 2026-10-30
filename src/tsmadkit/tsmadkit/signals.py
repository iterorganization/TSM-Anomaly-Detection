"""
Signal specifications and runtime containers for detector inputs.

This module defines the signal roles declared in algorithm configuration and
wraps time-aligned signal arrays in a container with convenient name, index, and
role based access.
"""

from dataclasses import dataclass
from typing import Iterable, Any

import numpy as np


@dataclass(frozen=True, slots=True)
class SignalSpec:
    """
    Immutable specification of signal roles declared in configuration.

    ``SignalSpec`` records which signals are detection targets and which are
    context signals. It also defines the canonical ordering used by
    :class:`SignalSet`: all targets first, followed by all context signals.
    """

    targets: tuple[str, ...]
    context: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        overlap = set(self.targets) & set(self.context)
        if overlap:
            overlap_sorted = sorted(overlap)
            raise ValueError(
                f"'targets' and 'context' must be disjoint; overlapping names: {overlap_sorted}"
            )

    @property
    def all(self) -> tuple[str, ...]:
        """
        Signal names in canonical target-then-context order.
        """
        return self.targets + self.context

    @property
    def has_context(self) -> bool:
        """
        Whether any context signals are declared.
        """
        return len(self.context) > 0

    def is_target(self, name: str) -> bool:
        """
        Return whether ``name`` is a target signal.
        """
        return name in self.targets
    
    def is_context(self, name: str) -> bool:
        """
        Return whether ``name`` is a context signal.
        """
        return name in self.context

    def role_of(self, name: str) -> str | None:
        """
        Return the role of ``name`` if it is declared.
        """
        if name in self.targets:
            return "target"
        if name in self.context:
            return "context"
        return None

    def to_dict(self) -> dict[str, list[str]]:
        """
        Convert the signal specification to a JSON-serializable dictionary.
        """
        return {
            "targets": list(self.targets),
            "context": list(self.context),
        }

    def __iter__(self):
        return iter(self.all)

    def __len__(self) -> int:
        return len(self.all)

    def __getitem__(self, idx):
        return self.all[idx]

    def __contains__(self, name: object) -> bool:
        return name in self.targets or name in self.context


class SignalSet:
    """
    Runtime container for multiple signals on a shared time grid.

    ``SignalSet`` arranges incoming data according to a :class:`SignalSpec`, stores
    values in the spec's canonical order, and provides convenient access by
    signal name, positional index, and role. Signals with matching trailing
    dimensions are stacked into one numeric array; heterogeneous signal shapes
    are stored in an object array so each signal can keep its own shape.

    Expected input payload::

        {
            "time": [...],
            "values": {
                "sig_a": [...],              # shape: (n_samples,)
                "sig_b": [[...], [...]],     # shape: (n_samples, d)
                ...
            }
        }

    All signals must share the same first axis length as ``time`` (sample axis).
    Trailing dimensions may differ between signals.
    """

    __slots__ = (
        "time",
        "values",          # stacked ndarray or object array (canonical order = spec.all)
        "_signal_spec",
        "_names",
        "_name_to_idx",
        "_targets_idx",
        "_context_idx",
        "_is_stacked",
    )

    def __init__(
            self,
            data_dict: dict[str, Any],
            signal_spec: SignalSpec,
            *,
            dtype: np.dtype = np.float64) -> None:
        """
        Parameters
        ----------
        data_dict : dict[str, Any]
            Input payload with ``time`` and ``values`` keys.
        signal_spec : SignalSpec
            Signal roles and canonical signal ordering.
        dtype : np.dtype, default=np.float64
            Data type used when converting time and signal values to arrays.
        """
        self._signal_spec = signal_spec

        # Normalize the input payload and build the name lookup table
        time = np.asarray(data_dict["time"], dtype=dtype) # TODO: consider keeping time in original dtype if as integer (i.e. nanosecond timestamps)
        values_map = data_dict["values"]
        names = signal_spec.all
        n_signals = len(names)

        # Convert each declared signal in canonical target-then-context order
        name_to_idx = {name: i for i, name in enumerate(names)}
        rows: list[np.ndarray] = []
        for name in names:
            row = np.asarray(values_map[name], dtype=dtype)
            rows.append(row)

        # Use a dense stack when shapes allow it, otherwise preserve heterogeneity
        can_stack = all(row.shape[1:] == rows[0].shape[1:] for row in rows)
        if can_stack:
            values: np.ndarray = np.stack(rows, axis=0)
            is_stacked = True
        else:
            # Keep heterogeneous trailing shapes without forcing ragged numeric arrays
            values = np.empty((n_signals,), dtype=object)
            for i, row in enumerate(rows):
                values[i] = row
            is_stacked = False

        self.time = time
        self.values = values
        self._names = names
        self._name_to_idx = name_to_idx
        self._targets_idx = slice(0, len(signal_spec.targets))
        self._context_idx = slice(len(signal_spec.targets), n_signals)
        self._is_stacked = is_stacked

    @property
    def n_samples(self) -> int:
        """
        Number of samples on the shared time grid.
        """
        return int(self.time.shape[0])

    @property
    def n_signals(self) -> int:
        """
        Number of signals in the set.
        """
        return int(self.values.shape[0])
    
    @property
    def signal_spec(self) -> SignalSpec:
        """
        Signal specification used by this set.
        """
        return self._signal_spec

    @property
    def names(self) -> np.ndarray[str]:
        """
        Signal names in canonical target-then-context order.
        """
        return np.asarray(self._names)

    @property
    def n_targets(self) -> int:
        """
        Number of target signals.
        """
        return len(self._signal_spec.targets)
    
    @property
    def n_context(self) -> int:
        """
        Number of context signals.
        """
        return len(self._signal_spec.context)

    @property
    def target_names(self) -> np.ndarray[str]:
        """
        Target signal names.
        """
        return np.asarray(self._signal_spec.targets)

    @property
    def context_names(self) -> np.ndarray[str]:
        """
        Context signal names.
        """
        return np.asarray(self._signal_spec.context)

    @property
    def target_values(self) -> np.ndarray:
        """
        Values for target signals.
        """
        return self.values[self._targets_idx]

    @property
    def context_values(self) -> np.ndarray:
        """
        Values for context signals.
        """
        return self.values[self._context_idx]

    @property
    def has_context(self) -> bool:
        """
        Whether this set includes context signals.
        """
        return self._signal_spec.has_context
    
    def is_target(self, name: str) -> bool:
        """
        Return whether ``name`` is a target signal.
        """
        return self._signal_spec.is_target(name)
    
    def is_context(self, name: str) -> bool:
        """
        Return whether ``name`` is a context signal.
        """
        return self._signal_spec.is_context(name)

    def value_of(self, name: str) -> np.ndarray:
        """
        Return values for a signal by name.
        """
        return self.values[self._name_to_idx[name]]

    def values_of(self, names: Iterable[str]) -> np.ndarray:
        """
        Return values for multiple signals by name.
        """
        idxs = [self._name_to_idx[name] for name in names]
        if self._is_stacked:
            return self.values[idxs]
        values = np.empty((len(idxs),), dtype=object)
        for out_i, src_i in enumerate(idxs):
            values[out_i] = self.values[src_i]
        return values
    
    def value_at(self, idx: int) -> np.ndarray:
        """
        Return values for a signal by positional index.
        """
        return self.values[np.intp(idx)]

    def values_at(self, idxs: Iterable[int]) -> np.ndarray[np.intp]:
        """
        Return values for multiple signals by positional index.
        """
        return self.values[np.asarray(idxs, dtype=np.intp)]

    def index_of(self, name: str) -> int:
        """
        Return the positional index of a signal name.
        """
        return self._name_to_idx[name]
    
    def indices_of(self, names: Iterable[str]) -> np.ndarray[np.intp]:
        """
        Return positional indices for multiple signal names.
        """
        return np.array([self._name_to_idx[name] for name in names], dtype=np.intp)

    def role_of(self, name: str) -> str | None:
        """
        Return the role of ``name`` if it is declared.
        """
        return self._signal_spec.role_of(name)

    def roles_of(self, names: Iterable[str]) -> np.ndarray[str | None]:
        """
        Return roles for multiple signal names.
        """
        return np.array([self.role_of(name) for name in names])

    def items(self):
        """
        Iterate over ``(name, values)`` pairs for all signals.
        """
        for i, name in enumerate(self.names):
            yield name, self.values[i]

    def target_items(self):
        """
        Iterate over ``(name, values)`` pairs for target signals.
        """
        for i, name in enumerate(self.target_names):
            yield name, self.values[i]

    def context_items(self):
        """
        Iterate over ``(name, values)`` pairs for context signals.
        """
        offset = self.n_targets
        for j, name in enumerate(self.context_names):
            yield name, self.values[offset + j]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the SignalSet instance to a dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the SignalSet.
        """
        data_dict = {}
        data_dict["time"] = self.time.tolist()
        data_dict["values"] = {name: self.value_of(name).tolist() for name in self.names}
        return data_dict

    @classmethod
    def from_dict(
        cls,
        data_dict: dict[str, Any],
        *,
        targets: Iterable[str] = (),
        context: Iterable[str] = (),
        signal_spec: SignalSpec | None = None,
        dtype: np.dtype = np.float64,
    ) -> "SignalSet":
        """
        Create a SignalSet instance from a dictionary.

        Parameters
        ----------
        data_dict : dict[str, Any]
            Dictionary containing the signal data.
        targets : Iterable[str], optional
            Names of the target signals.
        context : Iterable[str], optional
            Names of the context signals.
        signal_spec : SignalSpec | None, optional
            Signal specification. If provided, 'targets' and 'context' must be empty.
        dtype : np.dtype, optional
            Data type for the signal values.

        Returns
        -------
        SignalSet
            A new SignalSet instance.
        """
        # Normalize iterable inputs before deciding how the specification is provided
        targets_tuple = tuple(targets)
        context_tuple = tuple(context)

        # Use an explicit SignalSpec when supplied, otherwise build one from roles
        if signal_spec is not None:
            if not isinstance(signal_spec, SignalSpec):
                raise TypeError(
                    f"'signal_spec' must be a SignalSpec instance or None, got {type(signal_spec).__name__}"
                )
            if targets_tuple or context_tuple:
                raise ValueError(
                    "Invalid arguments: provide either 'signal_spec' OR 'targets'/'context', not both."
                )
            spec = signal_spec
        else:
            if not targets_tuple:
                raise ValueError(
                    "Missing signal specification: provide 'signal_spec' or a non-empty 'targets'."
                )
            spec = SignalSpec(
                targets=targets_tuple,
                context=context_tuple,
            )
        return cls(data_dict, signal_spec=spec, dtype=dtype)

    def __getitem__(self, key) -> np.ndarray:
        # Name lookup.
        if isinstance(key, str):
            return self.value_of(key)

        # Index lookup.
        if np.isscalar(key):
            return self.value_at(key)

        # Vectorized lookup by names.
        if isinstance(key[0], str):
            return self.values_of(key)

        # Vectorized lookup by indices.
        if np.isscalar(key[0]):
            return self.values_at(key)
    
    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, SignalSet):
            return NotImplemented

        # Compare metadata before walking potentially large signal arrays.
        if self.signal_spec != other.signal_spec:
            return False
        if not np.array_equal(self.time, other.time, equal_nan=True):
            return False

        # Compare each named signal so heterogeneous object-array storage is handled.
        for name in self.names:
            if not np.array_equal(self.value_of(name), other.value_of(name), equal_nan=True):
                return False
        return True

    def __len__(self) -> int:
        return self.n_signals

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        n_targets = self.n_targets
        n_context = self.n_context
        return (
            f"{cls}("
            f"n_samples={self.n_samples}, "
            f"n_signals={self.n_signals}, "
            f"n_targets={n_targets}, "
            f"n_context={n_context}"
            f")"
        )
    
    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}: "
            f"{self.n_signals} signals "
            f"({self.n_targets} target, {self.n_context} context), "
            f"{self.n_samples} samples"
        )
