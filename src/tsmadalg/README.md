# TSM Anomaly Detection Algorithms

`tsmadalg` is a catalog of anomaly detection algorithms implemented using the `tsmadkit` package and running in TSM. It provides a dynamic registry that automatically discovers and registers new algorithms, and a CLI for listing, scaffolding, and running them.

## Installing the `tsmadalg` package

Install the `tsmadalg` package locally:

```bash
pip install -e .
```

## Optional Dependencies

The CLI (`tsmadalg list`/`create`/`run`) depends on `rich`, which is declared as an optional extra rather than a core dependency:

```bash
pip install -e .[tools]
```

**For development:**
```bash
pip install -e .[dev]
```

**Install both optional dependency groups:**
```bash
pip install -e .[tools,dev]
```

## CLI tools

**List all discovered algorithms:**
```bash
tsmadalg list
```

This command imports each discovered algorithm and reports its version, its availability status, and the import error details when the import fails.

**Create a new algorithm template:**
```bash
tsmadalg create my_detector
```

This generates a new algorithm directory with boilerplate code, including:
- A Python class inheriting from `AnomalyDetection`
- An `example_config.json` file following the required schema
- An `__init__.py` file re-exporting the class

Additional options:
```bash
tsmadalg create my_detector --version 1.0.0 --signals SIGNAL_1 SIGNAL_2
```

Use `tsmadalg create --help` for the full list of options (parameters, model source/path, anomaly classes, artifacts, output directory, etc.).

**Run an algorithm on an input payload:**
```bash
tsmadalg run my_detector --config config.json --input input.json
```

This loads the algorithm from the registry, instantiates and sets it up from `--config`, runs `detect()` on the payload read from `--input` (in the `time`/`values` format supported by the `tsmadkit` package), and writes the resulting `AnomalyResult` to JSON (defaults to `<algo_name>_result.json`, override with `--output`).

## Adding a new algorithm

To add a new algorithm to the `tsmadalg` package, create a new subfolder inside `tsmadalg/algorithms/` that contains the following files:

| File | Purpose |
|------|----------|
| `main.py` | Defines the algorithm's main class, which **must inherit from** `tsmadkit.AnomalyDetection`. This is the entry point automatically discovered and registered. |
| `__init__.py` | Marks the folder as a Python subpackage and re-exports the algorithm class (e.g. `from .main import MyNewAlgo`). |
| `example_config.json` | Shows what a real configuration looks like for the algorithm (parameters, signals, model). It is not loaded at runtime, but it **must follow the required JSON schema** (see `tsmadkit.config.AlgorithmConfig`). |

### Example structure

```
tsmadalg/
└── algorithms/
    └── my_new_algo/
        ├── __init__.py
        ├── main.py
        └── example_config.json
```

When these conditions are met:
- The algorithm will be discovered by the registry (`tsmadalg.tools.registry`), used by `tsmadalg list` and `tsmadalg run`.
- It will be importable from its own package (e.g. `from tsmadalg.algorithms.my_new_algo import MyNewAlgo`), which only imports this algorithm and its dependencies.
- The registry entry stores the availability status and the import error details for unavailable algorithms.

Algorithm folders outside of `tsmadalg/algorithms/` (e.g. for local/developer work) can also be discovered by listing their parent directories in the `TSMADALG_EXT_PATH` environment variable.

### Naming convention

An algorithm is named after the ITER system it monitors, followed by either a subsystem of that system or a phenomenon it detects, in snake_case:

```
<system>_<subsystem or phenomenon>[_<qualifier>]
```

- `system` is the short code of the system where the anomaly shows up (e.g. `ech`, `mag`, `vv`).
  Systems that only provide context signals are not part of the name.
- The subsystem (e.g. `ech_collector`, `mag_power_supply`) or the phenomenon (e.g. `mag_quench`, `vv_stray`) is spelled out, unless its abbreviation is universal.
- The optional `qualifier` is only added to tell apart two algorithms that would otherwise share a name.
  Prefer the monitored quantity or the source (e.g. `ech_collector_thermal`, `vv_stray_ech`), and use the detection method only as a last resort.

The execution mode (intershot or synchronized), the detection method, and the properties declared in the configuration (anomaly classes, model) are not part of the name, so it stays stable across versions.
The class name is the folder name in PascalCase, with the system code in capitals: `ech_collector` defines `ECHCollector`.
