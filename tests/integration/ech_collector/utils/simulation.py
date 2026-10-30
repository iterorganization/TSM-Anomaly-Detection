"""
Thermal simulation primitives for synthetic ECH collector pulses.
"""

import numpy as np
from scipy.integrate import solve_ivp


def simulate_radial_thermal_lumps(
    N=10,
    t_begin=0.0,
    t_end=60.0,
    heat_duration=20.0,
    frequency=10.0,
    T_initial=20.0,
    T_coolant=20.0,
    C=None,
    R_radial=None,
    R_cooling=None,
    Q_total=1000.0,
    heat_sigma=0.25,
    heat_shift=None,
    heat_fluctuation=None,
    cooling_degradation=None,
    coolant_ramp=None,
    local_cooling_fault=None,
    radial_resistance_change=None,
):
    """
    Simulate a radial multi-lump thermal system with optional process-level behavior changes.

    Temperatures are in degrees Celsius.

    Parameters
    ----------
    N : int
        Number of radial regions. Region 0 is the center, region N-1 is the edge.
    t_begin : float
        Heat-source start time [s].
    t_end : float
        Final simulation time [s].
    heat_duration : float
        Duration of heat input after t_begin [s].
    frequency : float
        Output sampling frequency [Hz].
    T_initial : float or array-like
        Initial temperature [degC]. Scalar or length-N array.
    T_coolant : float
        Nominal coolant temperature [degC].
    C : array-like or None
        Heat capacity of each region [J/K], length N.
    R_radial : array-like or None
        Thermal resistance between neighboring regions [K/W], length N-1.
    R_cooling : array-like or None
        Thermal resistance from each region to coolant [K/W], length N.
    Q_total : float
        Nominal total heat input while active [W].
    heat_sigma : float
        Width of Gaussian heat input as a fraction of radius.
    heat_shift : dict or None
        Optional radial heat-source displacement.
        Example::
            {
                "t_start": 40.0,
                "t_stop": 120.0,
                "shift": 0.25
            }
        shift=0.0 means centered at region 0.
        shift=0.25 means Gaussian centered at 25% of radius.
    heat_fluctuation : dict or None
        Optional sinusoidal fluctuation of total heat input.
        Example::
            {
                "amplitude": 0.15,
                "frequency": 0.08,
                "phase": 0.0
            }
        This gives:
            Q(t) = Q_total * (1 + amplitude * sin(2*pi*f*t + phase))
    cooling_degradation : dict or None
        Optional global cooling degradation.
        Example::
            {
                "t_start": 80.0,
                "factor_final": 2.0,
                "tau": 30.0
            }
        This gradually multiplies R_cooling by up to factor_final.
        Larger R_cooling means weaker cooling.
    coolant_ramp : dict or None
        Optional coolant temperature ramp.
        Example::
            {
                "t_start": 60.0,
                "rate": 0.03
            }
        Coolant temperature changes by rate [degC/s] after t_start.
    local_cooling_fault : dict or None
        Optional local increase in R_cooling for selected regions.
        Example::
            {
                "channels": [0, 1, 2],
                "t_start": 70.0,
                "t_stop": 140.0,
                "factor": 1.8
            }
    radial_resistance_change : dict or None
        Optional change in radial conduction.
        Example::
            {
                "interfaces": [0, 1, 2],
                "t_start": 70.0,
                "t_stop": 140.0,
                "factor": 1.5
            }
        interfaces are indices of R_radial.
        interface 0 is between region 0 and region 1.
        Larger factor means weaker radial conduction.

    Returns
    -------
    result : dict
        {
            "t": time array [s],
            "T": true physical temperatures [degC], shape (n_times, N),
            "Q_regions_nominal": nominal Gaussian heat distribution [W],
            "heat_start": heat start time [s],
            "heat_stop": heat stop time [s],
            "success": solver success flag,
            "message": solver message
        }
    """
    if N < 1:
        raise ValueError("N must be at least 1.")
    if t_begin < 0:
        raise ValueError("t_begin must be non-negative.")
    if t_end <= 0:
        raise ValueError("t_end must be positive.")
    if t_begin >= t_end:
        raise ValueError("t_begin must be smaller than t_end.")
    if heat_duration < 0:
        raise ValueError("heat_duration must be non-negative.")
    if frequency <= 0:
        raise ValueError("frequency must be positive.")
    if heat_sigma <= 0:
        raise ValueError("heat_sigma must be positive.")

    heat_start = float(t_begin)
    heat_stop = float(t_begin + heat_duration)

    dt_save = 1.0 / frequency
    t_eval = np.arange(0.0, t_end + 0.5 * dt_save, dt_save)
    t_eval = t_eval[t_eval <= t_end]
    if len(t_eval) == 0 or t_eval[-1] < t_end:
        t_eval = np.append(t_eval, t_end)

    if C is None:
        C = np.full(N, 500.0)
    else:
        C = np.asarray(C, dtype=float)
        if C.shape != (N,):
            raise ValueError("C must have length N.")

    if R_cooling is None:
        R_cooling = np.full(N, 0.5)
    else:
        R_cooling = np.asarray(R_cooling, dtype=float)
        if R_cooling.shape != (N,):
            raise ValueError("R_cooling must have length N.")

    if N == 1:
        R_radial = np.array([])
    elif R_radial is None:
        R_radial = np.full(N - 1, 0.2)
    else:
        R_radial = np.asarray(R_radial, dtype=float)
        if R_radial.shape != (N - 1,):
            raise ValueError("R_radial must have length N - 1.")

    if np.isscalar(T_initial):
        T0 = np.full(N, float(T_initial))
    else:
        T0 = np.asarray(T_initial, dtype=float)
        if T0.shape != (N,):
            raise ValueError("T_initial must be a scalar or an array of length N.")

    r = np.linspace(0.0, 1.0, N)

    def in_window(t, t_start=None, t_stop=None):
        if t_start is not None and t < t_start:
            return False
        if t_stop is not None and t > t_stop:
            return False
        return True

    def gaussian_heat_distribution(center_shift):
        weights = np.exp(-0.5 * ((r - center_shift) / heat_sigma) ** 2)
        return Q_total * weights / np.sum(weights)

    Q_regions_nominal = gaussian_heat_distribution(center_shift=0.0)

    def current_heat_shift(t):
        if heat_shift is None:
            return 0.0

        if in_window(
            t,
            heat_shift.get("t_start", None),
            heat_shift.get("t_stop", None),
        ):
            return float(heat_shift.get("shift", 0.0))

        return 0.0

    def current_heat_multiplier(t):
        multiplier = 1.0

        if heat_fluctuation is not None:
            amplitude = float(heat_fluctuation.get("amplitude", 0.0))
            freq = float(heat_fluctuation.get("frequency", 0.0))
            phase = float(heat_fluctuation.get("phase", 0.0))
            multiplier += amplitude * np.sin(2.0 * np.pi * freq * t + phase)

        return max(multiplier, 0.0)

    def current_coolant_temperature(t):
        temperature = float(T_coolant)

        if coolant_ramp is not None:
            t_start = float(coolant_ramp.get("t_start", 0.0))
            rate = float(coolant_ramp.get("rate", 0.0))
            if t >= t_start:
                temperature += rate * (t - t_start)

        return temperature

    def current_R_cooling(t):
        resistance = R_cooling.copy()

        if cooling_degradation is not None:
            t_start = float(cooling_degradation.get("t_start", 0.0))
            factor_final = float(cooling_degradation.get("factor_final", 1.0))
            tau = float(cooling_degradation.get("tau", 1.0))

            if factor_final <= 0:
                raise ValueError("cooling_degradation factor_final must be positive.")
            if tau <= 0:
                raise ValueError("cooling_degradation tau must be positive.")

            if t >= t_start:
                progress = 1.0 - np.exp(-(t - t_start) / tau)
                factor = 1.0 + (factor_final - 1.0) * progress
                resistance *= factor

        if local_cooling_fault is not None:
            channels = local_cooling_fault.get("channels", [])
            t_start = local_cooling_fault.get("t_start", None)
            t_stop = local_cooling_fault.get("t_stop", None)
            factor = float(local_cooling_fault.get("factor", 1.0))

            if factor <= 0:
                raise ValueError("local_cooling_fault factor must be positive.")

            if in_window(t, t_start, t_stop):
                for channel in channels:
                    if channel < 0 or channel >= N:
                        raise ValueError(f"Invalid cooling fault channel: {channel}")
                    resistance[channel] *= factor

        return resistance

    def current_R_radial(t):
        resistance = R_radial.copy()

        if radial_resistance_change is not None and N > 1:
            interfaces = radial_resistance_change.get("interfaces", [])
            if interfaces == "all":
                interfaces = range(N - 1)
            t_start = radial_resistance_change.get("t_start", None)
            t_stop = radial_resistance_change.get("t_stop", None)
            factor = float(radial_resistance_change.get("factor", 1.0))

            if factor <= 0:
                raise ValueError("radial_resistance_change factor must be positive.")

            if in_window(t, t_start, t_stop):
                for index in interfaces:
                    if index < 0 or index >= N - 1:
                        raise ValueError(f"Invalid radial interface index: {index}")
                    resistance[index] *= factor

        return resistance

    def rhs(t, T):
        dTdt = np.zeros(N)

        if heat_start <= t <= heat_stop:
            center_shift = current_heat_shift(t)
            Q_regions = gaussian_heat_distribution(center_shift=center_shift)
            Q_regions *= current_heat_multiplier(t)
        else:
            Q_regions = np.zeros(N)

        Rcw = current_R_cooling(t)
        Rr = current_R_radial(t)
        Tc = current_coolant_temperature(t)

        for i in range(N):
            heat_balance = Q_regions[i]

            if i > 0:
                heat_balance += (T[i - 1] - T[i]) / Rr[i - 1]
            if i < N - 1:
                heat_balance += (T[i + 1] - T[i]) / Rr[i]

            heat_balance -= (T[i] - Tc) / Rcw[i]
            dTdt[i] = heat_balance / C[i]

        return dTdt

    sol = solve_ivp(
        rhs,
        t_span=(0.0, t_end),
        y0=T0,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-6,
        atol=1e-8,
    )

    return {
        "t": sol.t,
        "T": sol.y.T,
        "Q_regions_nominal": Q_regions_nominal,
        "heat_start": heat_start,
        "heat_stop": heat_stop,
        "success": sol.success,
        "message": sol.message,
    }


def inject_temperature_anomalies(t, T, anomalies=None, seed=None):
    """
    Inject synthetic thermocouple measurement anomalies.

    Parameters
    ----------
    t : array-like
        Time array in seconds.
    T : array-like
        Temperature array with shape ``(n_times, n_channels)``.
    anomalies : list of dict, optional
        Measurement-level anomaly specifications.
    seed : int, optional
        Random seed used by stochastic anomalies.

    Returns
    -------
    ndarray
        Corrupted thermocouple measurements in degC.
    """
    rng = np.random.default_rng(seed)

    t = np.asarray(t, dtype=float)
    T_measured = np.asarray(T, dtype=float).copy()

    if T_measured.ndim != 2:
        raise ValueError("T must have shape (n_times, n_channels).")

    n_times, n_channels = T_measured.shape
    if len(t) != n_times:
        raise ValueError("t length must match T.shape[0].")

    if anomalies is None:
        return T_measured

    def resolve_channels(channels):
        if channels == "all":
            return list(range(n_channels))
        if isinstance(channels, int):
            return [channels]

        channels = list(channels)
        for channel in channels:
            if channel < 0 or channel >= n_channels:
                raise ValueError(f"Invalid channel index: {channel}")
        return channels

    def time_mask(t_start=None, t_stop=None):
        mask = np.ones(n_times, dtype=bool)
        if t_start is not None:
            mask &= t >= t_start
        if t_stop is not None:
            mask &= t <= t_stop
        return mask

    def first_order_lag(x, tau):
        if tau <= 0:
            return x.copy()

        y = np.empty_like(x)
        y[0] = x[0]
        dt = np.diff(t)

        for k in range(1, len(x)):
            alpha = dt[k - 1] / (tau + dt[k - 1])
            y[k] = y[k - 1] + alpha * (x[k] - y[k - 1])

        return y

    for anomaly in anomalies:
        kind = anomaly["type"]
        channels = resolve_channels(anomaly.get("channels", "all"))
        t_start = anomaly.get("t_start", None)
        t_stop = anomaly.get("t_stop", None)
        mask = time_mask(t_start, t_stop)

        if kind == "noise":
            std = float(anomaly.get("std", 0.2))
            for channel in channels:
                T_measured[mask, channel] += rng.normal(
                    loc=0.0,
                    scale=std,
                    size=np.sum(mask),
                )
        elif kind == "offset":
            value = float(anomaly.get("value", 0.0))
            for channel in channels:
                T_measured[mask, channel] += value
        elif kind == "drift":
            rate = float(anomaly.get("rate", 0.0))
            reference_time = t_start if t_start is not None else t[0]
            for channel in channels:
                T_measured[mask, channel] += rate * (t[mask] - reference_time)
        elif kind == "gain":
            gain = float(anomaly.get("gain", 1.0))
            reference = float(anomaly.get("reference", 20.0))
            for channel in channels:
                T_measured[mask, channel] = reference + gain * (
                    T_measured[mask, channel] - reference
                )
        elif kind == "lag":
            tau = float(anomaly.get("tau", 2.0))
            for channel in channels:
                lagged = first_order_lag(T_measured[:, channel], tau)
                T_measured[mask, channel] = lagged[mask]
        elif kind == "spike":
            magnitude = float(anomaly.get("magnitude", 10.0))
            spike_time = float(anomaly["time"])
            width = float(anomaly.get("width", 0.0))

            if width <= 0:
                index = np.argmin(np.abs(t - spike_time))
                for channel in channels:
                    T_measured[index, channel] += magnitude
            else:
                spike_shape = magnitude * np.exp(
                    -0.5 * ((t - spike_time) / width) ** 2
                )
                for channel in channels:
                    T_measured[:, channel] += spike_shape
        elif kind == "dropout":
            fill_value = anomaly.get("fill_value", np.nan)
            for channel in channels:
                T_measured[mask, channel] = fill_value
        elif kind == "stuck":
            if t_start is None:
                raise ValueError("A 'stuck' anomaly requires t_start.")
            index = np.argmax(t >= t_start)
            for channel in channels:
                stuck_value = T_measured[index, channel]
                T_measured[mask, channel] = stuck_value
        elif kind == "saturation":
            min_value = anomaly.get("min", -np.inf)
            max_value = anomaly.get("max", np.inf)
            for channel in channels:
                T_measured[mask, channel] = np.clip(
                    T_measured[mask, channel],
                    min_value,
                    max_value,
                )
        elif kind == "channel_swap":
            if len(channels) != 2:
                raise ValueError("channel_swap requires exactly two channels.")
            ch1, ch2 = channels
            T_measured[mask, [ch1, ch2]] = T_measured[mask, [ch2, ch1]]
        else:
            raise ValueError(f"Unknown anomaly type: {kind}")

    return T_measured


def step_signal(t_begin, t_end, duration, frequency, amplitude, time=None):
    """
    Create a sampled rectangular step signal.

    Parameters
    ----------
    t_begin : float
        Step start time in seconds.
    t_end : float
        Final signal time in seconds.
    duration : float
        Step duration in seconds.
    frequency : float
        Sampling frequency in Hz.
    amplitude : float
        Step amplitude.
    time : array-like, optional
        Existing time base. When provided, ``t_end`` and ``frequency`` are not
        used to build a new grid.

    Returns
    -------
    ndarray
        Step signal values.
    """
    if time is None:
        dt = 1.0 / frequency
        t = np.arange(0.0, t_end + dt, dt)
    else:
        t = np.asarray(time, dtype=float)

    y = np.zeros_like(t)
    mask = (t >= t_begin) & (t < t_begin + duration)
    y[mask] = amplitude
    return y


def multivariate_normal_sample(bounds, n, seed=None, sigma_factor=6.0):
    """
    Draw bounded normal samples from named parameter bounds.

    Parameters
    ----------
    bounds : dict[str, sequence[float]]
        Mapping from parameter names to ``(lower, upper)`` bounds.
    n : int
        Number of samples.
    seed : int, optional
        Random seed.
    sigma_factor : float, default=6.0
        Divisor used to convert each bound width into a standard deviation.

    Returns
    -------
    list[dict[str, float]]
        One parameter dictionary per sampled point.

    Raises
    ------
    ValueError
        If ``n`` is negative, ``sigma_factor`` is not positive, or any lower
        bound is greater than its upper bound.
    """
    if n < 0:
        raise ValueError("n must be non-negative.")
    if sigma_factor <= 0:
        raise ValueError("sigma_factor must be positive.")

    names = list(bounds)
    lower = np.array([bounds[name][0] for name in names], dtype=float)
    upper = np.array([bounds[name][1] for name in names], dtype=float)

    if np.any(lower > upper):
        raise ValueError(
            "Each lower bound must be less than or equal to its upper bound."
        )

    center = 0.5 * (lower + upper)
    sigma = (upper - lower) / sigma_factor
    rng = np.random.default_rng(seed)
    sample = np.empty((n, len(names)), dtype=float)

    remaining = np.arange(n)
    while len(remaining):
        draws = rng.normal(
            loc=center,
            scale=sigma,
            size=(len(remaining), len(names)),
        )
        in_bounds = np.all((draws >= lower) & (draws <= upper), axis=1)
        sample[remaining[in_bounds]] = draws[in_bounds]
        remaining = remaining[~in_bounds]

    return [
        dict(zip(names, row))
        for row in sample
    ]


FAULT_PARAMETERS = {
    "cooling_degradation": ("t_start", "factor_final", "tau"),
    "heat_shift": ("t_start", "duration", "shift"),
    "heat_fluctuation": ("amplitude", "frequency", "phase"),
    "coolant_ramp": ("t_start", "rate"),
    "radial_resistance_change": ("t_start", "duration", "factor"),
}


def sample_anomaly_pulses(bounds, faults, count, n_faults=(1, 1), seed=None):
    """
    Sample randomized anomalous pulse specifications.

    Draws base pulse parameters the same way as :func:`multivariate_normal_sample`,
    then injects a random subset of process-level faults into each pulse.

    Parameters
    ----------
    bounds : dict[str, sequence[float]]
        Bounds for the base pulse parameters, as for
        :func:`multivariate_normal_sample`.
    faults : dict[str, dict[str, sequence[float]]]
        Mapping from fault type to bounds for that fault's own parameters.
        Each bound is either a single ``[low, high]`` range or a list of
        ranges, the latter useful to keep a value away from a "no effect"
        point (e.g. two bands around zero for a rate). Supported fault types
        are the keys of ``FAULT_PARAMETERS``: "cooling_degradation",
        "heat_shift", "heat_fluctuation", "coolant_ramp",
        "radial_resistance_change". "heat_shift" and
        "radial_resistance_change" take a "duration" bound instead of
        "t_stop"; the fault's actual ``t_stop`` is derived as
        ``min(t_start + duration, t_end)``.
    count : int
        Number of anomalous pulses to generate.
    n_faults : (int, int), default=(1, 1)
        Inclusive (min, max) number of simultaneous faults per pulse.
    seed : int, optional
        Random seed.

    Returns
    -------
    list[dict]
        One ``{"parameters": {...}}`` pulse spec per sampled anomaly, ready
        to pass to ``make_pulse_data``.

    Raises
    ------
    ValueError
        If `faults` is empty, an unknown fault type is given, or `n_faults`
        exceeds the number of available fault types.
    """
    if not faults:
        raise ValueError("faults must define at least one fault type.")
    for kind in faults:
        if kind not in FAULT_PARAMETERS:
            raise ValueError(f"Unknown fault type: {kind}")

    min_faults, max_faults = n_faults
    if max_faults > len(faults):
        raise ValueError("n_faults cannot exceed the number of fault types.")

    rng = np.random.default_rng(seed)
    fault_names = list(faults)

    base = multivariate_normal_sample(bounds, n=count, seed=seed)
    specs = []
    for parameters in base:
        n_selected = int(rng.integers(min_faults, max_faults + 1))
        for kind in rng.choice(fault_names, size=n_selected, replace=False):
            parameters[kind] = _sample_fault(kind, faults[kind], parameters["t_end"], rng)
        specs.append({"parameters": parameters})

    return specs


def _sample_fault(kind, fault_bounds, t_end, rng):
    """
    Draw one fault's parameter dict, as used by `sample_anomaly_pulses`.

    Each bound may be a single ``[low, high]`` range, or a list of such
    ranges to sample from a band picked uniformly at random. The latter is
    useful to keep a parameter away from a "no effect" value, e.g.
    ``[[-0.12, -0.03], [0.03, 0.12]]`` for a rate that should never be near
    zero.
    """

    def draw(name):
        bands = fault_bounds[name]
        if np.isscalar(bands[0]):
            bands = [bands]
        low, high = bands[int(rng.integers(len(bands)))]
        return float(rng.uniform(low, high))

    values = {name: draw(name) for name in FAULT_PARAMETERS[kind] if name != "duration"}

    if kind in ("heat_shift", "radial_resistance_change"):
        t_stop = min(values["t_start"] + draw("duration"), t_end)
        values["t_stop"] = t_stop

    if kind == "radial_resistance_change":
        values["interfaces"] = "all"

    return values
