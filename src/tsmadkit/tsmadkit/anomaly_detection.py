from abc import ABC, abstractmethod
import importlib
import json
from pathlib import Path
from typing import Any

from tsmadkit.config import AlgorithmConfig
from tsmadkit.anomaly_result import AnomalyResult
from tsmadkit.io import read_json
from tsmadkit.signals import SignalSpec, SignalSet
from tsmadkit.state import ReferenceState

class AnomalyDetection(ABC):
    """
    Abstract base class for anomaly detection algorithms.

    The purpose of this class is to provide a common interface and configuration-
    driven setup for anomaly detectors. It handles parsing a JSON configuration,
    exposing the algorithm name and user parameters as attributes, and offering a
    hook (:meth:`setup`) for model loading or other pre-execution setup.

    Subclasses must define a ``__version__`` class attribute (e.g. ``"0.1.0"``)
    and implement :meth:`detect` to define the anomaly detection logic and
    return an :class:`AnomalyResult`. The TSM POZ application (C++) calls
    :meth:`_tsm_poz_execute` instead, which wraps :meth:`detect` and returns
    EPICS-compatible, serializable values.

    Typical usage:
        1. Instantiate with a configuration file or dictionary.
        2. Call :meth:`setup` once to load the model (if any).
        3. Call :meth:`detect` with input data in :class:`SignalSet` format or call
           :meth:`_tsm_poz_execute` with a plain input dictionary.
    """

    # Dynamic import of heavy packages at runtime
    __model_loaders = {
        "scikit-learn": lambda: importlib.import_module("joblib").load,
        "keras": lambda: importlib.import_module("tensorflow").keras.models.load_model,
        "tensorflow": lambda: importlib.import_module("tensorflow").keras.models.load_model,
        # TODO: add ONNX support
    }

    # Default classes for normal and anomalous behaviors
    DEFAULT_NORMAL_CLASS = "OK"
    DEFAULT_ANOMALY_CLASS = "anomaly"

    def __init__(self, configuration: str | Path | dict) -> None:
        """
        Parameters
        ----------
        configuration : str | Path | dict
            Configuration dictionary or path to a JSON file containing the
            algorithm configuration. Relative paths within a configuration file
            are resolved from the directory containing that file. Relative paths
            within a configuration dictionary are resolved from the current
            working directory. Absolute paths are used unchanged in both cases.

        Notes
        -----
        The configuration should have the following format::

            {
                "name": "algorithm-name",
                "parameters": {"threshold": 0.5},
                "model": {
                    "source": "scikit-learn",
                    "path": "model.joblib"
                },
                "signals": {
                    "targets": ["signal-a"],
                    "context": ["signal-b"]
                },
                "artifacts": ["additional-data.npz"],
                "anomaly_classes": ["anomaly"],
                "reference_state": {
                    "path": "reference_state.json",
                    "check": "fast"
                }
            }

        All nullable top-level fields are optional: ``model``, ``parameters``,
        ``artifacts``, ``anomaly_classes``, and ``reference_state``.
        ``signals.context`` may also be omitted.

        The 'name' key in the configuration is a string that identifies the algorithm.
        The 'parameters' key in the configuration is a dictionary where each item becomes an attribute of the instance.
        The configuration content is hashed into ``config_hash``, which is the same
        whether the configuration comes from a file or a dictionary.

        Raises
        ------
        TypeError
            If the subclass does not define ``__version__`` as a non-empty string.
        """
        # The algorithm version identifies results and invalidates reference state caches
        version = getattr(type(self), "__version__", None)
        if not isinstance(version, str) or not version.strip():
            raise TypeError(
                f"{type(self).__name__} must define a non-empty string class "
                'attribute __version__ (e.g. __version__ = "0.1.0").'
            )

        if isinstance(configuration, dict):
            self._configuration_dir = Path.cwd()
            raw_config = configuration
        else:
            configuration_path = Path(configuration).expanduser().resolve()
            self._configuration_dir = configuration_path.parent
            raw_config = read_json(configuration_path)

        # Validate the configuration
        self.__config = AlgorithmConfig.model_validate(raw_config)

        # Configuration hash, identical for a file or a dict with the same content
        self.config_hash = self.__config.sha256()

        # Algorithm name
        self.name = self.__config.name

        # Signals covered by the anomaly detection
        self.signal_spec = SignalSpec(
            targets=tuple(self.__config.signals.targets),
            context=tuple(self.__config.signals.context),
        )

        # Model configuration (loading, if any, is delegated to `setup`)
        self.model = None
        self.__model_config = None
        if self.__config.model is not None:
            self.__model_config = self.__config.model.model_dump()
            self.__model_config["path"] = self._resolve_config_path(
                self.__model_config["path"],
                must_exist=True,
                field_name="model.path",
            )

        # Convert dict items to instance attributes        
        self.__pnames = []
        if self.__config.parameters is not None:
            for param, value in self.__config.parameters.items():
                if hasattr(self, param):
                    raise ValueError(
                        f"Parameter '{param}' specified in the configuration "
                        "already exists in the instance. Please choose a different name."
                    )
                self.__setattr__(param, value)
                self.__pnames.append(param)

        # Anomaly classes
        self.__anomaly_classes = self.__config.anomaly_classes or [self.DEFAULT_ANOMALY_CLASS]

        # Artifacts (optional additional files)
        self.__artifacts = None
        if self.__config.artifacts is not None:
            self.__artifacts = [
                self._resolve_config_path(path, must_exist=True, field_name="artifacts")
                for path in self.__config.artifacts
            ]

        # Reference state
        self.reference_state = None
        self.__reference_state_path = None
        self.__reference_state_check_mode = None
        if self.__config.reference_state is not None:
            self.__reference_state_path = self._resolve_config_path(
                path=self.__config.reference_state.path,
                must_exist=False,
                field_name="reference_state",
            )
            self.__reference_state_check_mode = self.__config.reference_state.check
            self.reference_state = ReferenceState(
                self.__reference_state_path,
                name=self.name,
                version=self.__version__,
                config_hash=self.config_hash,
                signal_spec=self.signal_spec,
            )

    @property
    def parameters(self) -> dict[str, Any]:
        """
        Custom algorithm parameters declared in the configuration.
        """
        return {p: self.__getattribute__(p) for p in self.__pnames}

    @property
    def model_config(self) -> dict[str, Any] | None:
        """
        Resolved model configuration, or ``None`` if no model is configured.
        """
        return self.__model_config

    @property
    def anomaly_classes(self) -> list[str]:
        """
        Configured anomaly class names.
        """
        return self.__anomaly_classes

    @property
    def classes(self) -> list[str]:
        """
        All class names, with the normal class first followed by the anomaly classes.
        """
        return [self.DEFAULT_NORMAL_CLASS] + self.anomaly_classes

    @property
    def is_multiclass(self) -> bool:
        """
        Whether the algorithm declares more than one anomaly class.
        """
        return len(self.anomaly_classes) >= 2

    @property
    def artifacts(self) -> list[str] | None:
        """
        Resolved paths to additional artifact files, or ``None`` if none are configured.
        """
        return self.__artifacts

    @property
    def has_artifacts(self) -> bool:
        """
        Whether any artifacts are configured.
        """
        return bool(self.__artifacts)

    @property
    def cache_data(self):
        """
        Convenience view over the reference state's cache data, or ``None`` if
        no reference state is configured.
        """
        if self.reference_state is None:
            return None
        return self.reference_state.cache.data

    def setup(self) -> None:
        """
        Hook for loading the model (if any) and performing any pre-execution setup.
        The main role of this method is to ensure `self.model` is correctly set and
        the reference state (if any) is ready before :meth:`detect()` or 
        :meth:`_tsm_poz_execute()` are called.
        
        Default behavior:
        
        - If "model" is null, do nothing.
        - If "source" is one of the supported loaders ('scikit-learn', 'keras', 'tensorflow'),
          load the model from "path".
        - If "source" is "custom" or None, raise NotImplementedError. In this case,
          subclasses must override :meth:`setup()` to implement their own loading logic.
        - If "reference_state" is configured, prepare its history/cache using
          the configured "check" mode.

        Notes
        -----
        - This method is not called automatically. It is the caller's responsibility
          to call :meth:`setup()` once after construction and before using :meth:`_tsm_poz_execute()`.
        - Subclasses should override :meth:`setup()` only when non-standard loading
          or additional setup is required.
        - Overriding subclasses should call ``super().setup()`` if they need the
          default model loading or reference state validation.
        - On first use, when the reference state's manifests and JSON file do
          not exist yet, this call bootstraps all of them from the raw
          ``*.h5`` files under ``history/``; see :doc:`/guides/reference-state`.

        Raises
        ------
        NotImplementedError
            If no custom initialization is provided for a model with a 'source' of
            'custom' or unspecified, or if a reference state is configured but the
            subclass does not implement :meth:`transform`.
        ValueError
            If an unknown model 'source' is specified. Valid sources are:
            'scikit-learn', 'keras', 'tensorflow', 'custom', or None.
        TypeError
            If the subclass's :meth:`transform` does not return a ``dict``.
        """
        # Model loading
        if self.__model_config is not None:
            model_source = self.__model_config["source"]
            model_path = self.__model_config["path"]
            if model_source in self.__model_loaders:
                model_reader = self.__model_loaders[model_source]()
                self.model = model_reader(model_path)
            elif model_source in ["custom", None]:
                raise NotImplementedError(
                "Custom or unspecified model 'source'. Override 'setup()' in your "
                "subclass to load the model (and perform any other required setup)."
            )
            else:
                sources = list(self.__model_loaders.keys()) + ["custom", None]
                raise ValueError(f"Unknown model 'source'. Must be one of {sources}.")

        # Reference state
        if self.reference_state is not None:
            transformer = getattr(self, "transform", None)
            if transformer is None:
                raise NotImplementedError(
                    "Algorithms with reference_state must implement transform()."
                )
            self.reference_state.setup(
                check=self.__reference_state_check_mode,
                transformer=transformer,
            )


    @abstractmethod
    def detect(self, signals: SignalSet) -> AnomalyResult:
        """
        Abstract method to perform anomaly detection on the provided data.
        This method must be implemented by child classes and should return
        an :class:`AnomalyResult`.

        Parameters
        ----------
        signals : SignalSet
            A SignalSet containing signals used for detecting anomalies.

        Returns
        -------
        AnomalyResult
            The result of the anomaly detection algorithm.
        """
        pass

    def _tsm_poz_execute(self, data_dict: dict[str, Any]) -> tuple[bool, dict, str, str]:
        """
        Entry point for the TSM POZ application.

        The TSM application running in the Plant Operation Zone (POZ) is the C++
        orchestrator that executes every TSM algorithm. It calls this method,
        which runs :meth:`detect` and converts its :class:`AnomalyResult` into an
        EPICS-compatible format. Algorithm developers should implement
        :meth:`detect` and leave this method unchanged.

        The full result also identifies what produced it: the algorithm name
        and version, the configuration hash, and the reference state hash
        (``None`` when no reference state is configured or prepared).

        Parameters
        ----------
        data_dict : dict
            Input payload with one common time grid and all signal series::

                {
                    "time": [...],
                    "values": {
                        "sig_a": [...],
                        "sig_b": [...],
                        ...
                    }
                }

        Returns
        -------
        tuple[bool, dict, str, str]
            A tuple containing the anomaly flag, scores, details, and string
            representation of the full result.
        """
        # Convert input dict to a dataframe-like structure
        # for easier downstream processing by the detection logic
        data = SignalSet(data_dict, self.signal_spec)
        
        # Run the detection
        anomaly_result = self.detect(data)
        anomaly_result_dict = anomaly_result.to_dict()
        
        # Identify the algorithm, configuration and reference data behind the result
        anomaly_result_dict["algorithm_name"] = self.name
        anomaly_result_dict["algorithm_version"] = self.__version__
        anomaly_result_dict["config_hash"] = self.config_hash
        anomaly_result_dict["reference_state_hash"] = (
            None if self.reference_state is None else self.reference_state.hash
        )

        # Fill defaults for fields left empty by detect()
        if not anomaly_result_dict["time_min"]:
            anomaly_result_dict["time_min"] = min(data.time)
        if not anomaly_result_dict["time_max"]:
            anomaly_result_dict["time_max"] = max(data.time)
        if not anomaly_result_dict["details"]:
            anomaly_result_dict["details"] = {} # TODO: check if OK for C++ as a default value
        
        # Unpack and convert to string for EPICS processing
        is_anomaly = anomaly_result_dict["is_anomaly"]
        scores = anomaly_result_dict["scores"]
        details_str = json.dumps(anomaly_result_dict["details"], sort_keys=True)
        anomaly_result_str = json.dumps(anomaly_result_dict, sort_keys=True)
        return is_anomaly, scores, details_str, anomaly_result_str

    @classmethod
    def validate_config(cls, config: dict) -> None:
        """
        Validate the configuration structure and types against the expected schema.

        Parameters
        ----------
        config : dict
            The configuration dictionary to validate.

        Raises
        ------
        ValidationError
            If the configuration does not conform to the schema.
        """
        AlgorithmConfig.model_validate(config)

    @classmethod
    def validate_config_from_json(cls, filepath: str) -> None:
        """
        Validate a configuration JSON file against the schema.

        Parameters
        ----------
        filepath : str
            Path to the JSON configuration file.

        Raises
        ------
        ValidationError
            If the configuration does not conform to the schema.
        """
        config = read_json(filepath)
        cls.validate_config(config)

    def _resolve_config_path(
        self,
        path: str,
        must_exist: bool = False,
        field_name: str = "path",
    ) -> str:
        """
        Resolve a configuration path to an absolute path.

        Parameters
        ----------
        path : str
            Path value read from the configuration.
        must_exist : bool, default=False
            Whether to require that the resolved path exists.
        field_name : str, default="path"
            Configuration field name used in error messages.

        Returns
        -------
        str
            Absolute path corresponding to ``path``. Relative paths are interpreted
            with respect to the configuration file directory.

        Raises
        ------
        FileNotFoundError
            If ``must_exist`` is ``True`` and the resolved path does not exist.
        """
        candidate = Path(path).expanduser()
        resolved = candidate if candidate.is_absolute() else (self._configuration_dir / candidate)

        if must_exist and not resolved.exists():
            raise FileNotFoundError(
                f"Configuration field '{field_name}' points to a missing path: "
                f"'{resolved}' (declared as '{path}')"
            )

        return str(resolved)

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return (
            f"{cls_name}(name={self.name!r}, "
            f"signals={self.signal_spec!r}, "
            f"parameters={self.parameters!r}, "
            f"model={'loaded' if self.model is not None else 'None'}, "
            f"artifacts={self.artifacts!r}, "
            f"classes={self.classes!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()
