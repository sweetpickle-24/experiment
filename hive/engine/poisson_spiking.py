"""
Poisson Spiking Layer — Stage 2.5
===================================

**Date**: 2026-03-23
**Status**: New — optional stochastic layer on top of wave-field brain

ARCHITECTURE
------------
The wave-field brain has two deterministic stages:
  Stage 1: Sensory transduction (photoreceptors, glomerular mapping)
           → deterministic biochemical kinetics, mean-field valid at >10^6 molecules
  Stage 2: SparseProbabilisticBrain (wave oscillators, mean-field)
           → deterministic given seed; Δφ/Δt = omega + coupling + noise
  Stage 2.5: PoissonSpikingWrapper (THIS MODULE)
           → stochastic spiking on top of mean-field wave amplitudes
           → amplitude A_i ≈ mean firing rate r_i (spikes/sec)
           → spike count in window Δt: k_i ~ Poisson(r_i × Δt)

BIOLOGICAL MOTIVATION
---------------------
The Juusola (2003) "quantum bump" phenomenon requires stochastic single-photon
absorption events — each photon activates 1 rhodopsin → 1 G-protein cascade
→ 1 bump (~1-2 mV, 20-50 ms). At low light:
  - Bumps arrive as rare discrete events (Poisson arrivals)
  - PSD shows flat (white noise) spectrum from individual bumps
At high light:
  - Many overlapping bumps → mean-field signal + noise
  - PSD shows 12 Hz peak from the deterministic G-protein–Ca²⁺ feedback loop

The current deterministic phototransduction (Stage 1) captures the 12 Hz
oscillation correctly but cannot produce the Poisson quantum bumps (they
require shot noise, not mean-field ODEs). Stage 2.5 adds that stochastic layer.

This module is also useful for:
  - Measuring neural code variability (CV of spike counts)
  - Computing power spectral density (PSD) of neural activity
  - Simulating downstream reading of spike trains (not just amplitudes)

USAGE
-----
    from hive.engine.poisson_spiking import PoissonSpikingWrapper

    # Wrap an existing brain
    wrapper = PoissonSpikingWrapper(brain, rate_scale_hz=500.0, seed=42)

    # Sample spikes at current brain state
    spikes = wrapper.sample_spikes(dt_ms=1.0)

    # Get Poisson activity for a region
    activity = wrapper.get_poisson_activity('KC')

    # Estimate CV of spike counts
    cv = wrapper.estimate_cv('KC', n_windows=50, window_ms=10.0)

    # Compute PSD of spike train
    freqs, psd = wrapper.get_spike_psd(neuron_ids, n_windows=100, window_ms=10.0, dt_ms=1.0)
"""

import numpy as np
from typing import List, Optional, Tuple, Union

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None


class PoissonSpikingWrapper:
    """
    Stage 2.5: Optional Poisson spiking layer on top of SparseProbabilisticBrain.

    Converts continuous wave amplitudes (mean firing rates) to stochastic
    spike counts using a Poisson process, enabling:
      - Quantum bump simulation (Juusola 2003)
      - CV measurement (variability analysis)
      - PSD computation (frequency content of spike trains)

    Args:
        brain: SparseProbabilisticBrain instance
        rate_scale_hz: Conversion from wave amplitude to firing rate (spikes/s).
                       Default: 500.0 means amplitude=1.0 → 500 Hz firing rate.
                       Calibrate to biological range (~50-200 Hz for most neurons).
        seed: Random seed for Poisson sampling. None = unseeded (truly stochastic).
    """

    def __init__(self, brain, rate_scale_hz: float = 500.0, seed: Optional[int] = None):
        self.brain = brain
        self.rate_scale_hz = rate_scale_hz
        self._rng = np.random.default_rng(seed)

        # Cache classify_olfactory_neuron for region lookups
        try:
            from hive.substrate.olfactory_subgraph import classify_olfactory_neuron
            self._classify_fn = classify_olfactory_neuron
        except ImportError:
            self._classify_fn = None

    # ── Core sampling ─────────────────────────────────────────────────────────

    def _get_amplitudes(self) -> np.ndarray:
        """Get current brain amplitudes as float32 numpy array."""
        if MLX_AVAILABLE and hasattr(self.brain.mean_amplitude, 'tolist'):
            return np.array(self.brain.mean_amplitude.tolist(), dtype=np.float64)
        return np.asarray(self.brain.mean_amplitude, dtype=np.float64)

    def sample_spikes(self, dt_ms: float = 1.0) -> np.ndarray:
        """
        Sample spike counts from Poisson process.

        λ_i = amplitude_i × rate_scale_hz × (dt_ms / 1000.0)

        Args:
            dt_ms: Time window in milliseconds (e.g., 1.0 ms per step)

        Returns:
            Integer spike count array, shape (num_neurons,)
        """
        amplitudes = self._get_amplitudes()
        lam = np.clip(amplitudes * self.rate_scale_hz * (dt_ms / 1000.0), 0.0, None)
        return self._rng.poisson(lam).astype(np.int32)

    def sample_spike_rates(self, dt_ms: float = 1.0) -> np.ndarray:
        """
        Sample Poisson spike counts and convert back to instantaneous rates (Hz).

        Returns:
            Float array of instantaneous spike rates (Hz), shape (num_neurons,)
        """
        spikes = self.sample_spikes(dt_ms)
        return spikes.astype(np.float32) * (1000.0 / dt_ms)

    # ── Region activity ────────────────────────────────────────────────────────

    def get_poisson_activity(self, region: str, dt_ms: float = 1.0) -> float:
        """
        Mean Poisson spike count for neurons in a given olfactory region.

        Uses the same classify_olfactory_neuron routing as get_region_activity.

        Args:
            region: 'PN', 'KC', 'MBON', 'DAN', 'LN', 'ORN', 'APL'
            dt_ms: Sampling window in milliseconds

        Returns:
            Mean spike count over the region
        """
        if self._classify_fn is None:
            return 0.0

        indices = [
            self.brain.id_to_idx[nid]
            for nid, neuron in self.brain.connectome.neurons.items()
            if self._classify_fn(neuron) == region and nid in self.brain.id_to_idx
        ]
        if not indices:
            return 0.0

        spikes = self.sample_spikes(dt_ms)
        return float(np.mean(spikes[indices]))

    # ── Variability (CV) ───────────────────────────────────────────────────────

    def estimate_cv(
        self,
        region: str,
        n_windows: int = 50,
        window_ms: float = 10.0,
    ) -> float:
        """
        Estimate coefficient of variation (CV = σ/μ) of spike counts.

        For a pure Poisson process:  CV = 1/√λ  (approaches 1.0 for λ≈1)
        For high rates (λ>>1):       CV → 1/√λ << 1 (sub-Poisson at high rate)

        Args:
            region: Olfactory region (e.g. 'KC', 'PN')
            n_windows: Number of independent samples to take
            window_ms: Sampling window size (ms)

        Returns:
            CV of mean spike count across windows
        """
        counts = []
        for _ in range(n_windows):
            c = self.get_poisson_activity(region, dt_ms=window_ms)
            counts.append(c)

        counts = np.array(counts)
        mu = float(np.mean(counts))
        sigma = float(np.std(counts))
        if mu < 1e-10:
            return float('nan')
        return sigma / mu

    def estimate_cv_per_neuron(
        self,
        neuron_ids: List[int],
        n_windows: int = 50,
        window_ms: float = 10.0,
    ) -> np.ndarray:
        """
        Estimate per-neuron CV of spike counts.

        Args:
            neuron_ids: List of neuron IDs to sample
            n_windows: Number of independent samples
            window_ms: Sampling window size (ms)

        Returns:
            CV array, shape (len(neuron_ids),)
        """
        indices = [self.brain.id_to_idx[nid] for nid in neuron_ids if nid in self.brain.id_to_idx]
        if not indices:
            return np.array([])

        spike_matrix = np.zeros((n_windows, len(indices)), dtype=np.float64)
        for t in range(n_windows):
            spikes = self.sample_spikes(dt_ms=window_ms)
            spike_matrix[t] = spikes[indices]

        mu = np.mean(spike_matrix, axis=0)
        sigma = np.std(spike_matrix, axis=0)
        cv = np.where(mu > 1e-10, sigma / mu, np.nan)
        return cv

    # ── Power Spectral Density ─────────────────────────────────────────────────

    def get_spike_psd(
        self,
        neuron_ids: List[int],
        n_windows: int = 200,
        window_ms: float = 1.0,
        dt_ms: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Record spike train for given neurons and compute PSD via FFT.

        Records a spike train: at each step, calls sample_spikes + brain.evolve(dt_ms),
        then computes one-sided PSD of the mean spike rate across given neurons.

        Args:
            neuron_ids: List of neuron IDs to record from
            n_windows: Number of time steps (total duration = n_windows × dt_ms ms)
            window_ms: Duration of each step (ms)
            dt_ms: Same as window_ms (aliased for clarity)

        Returns:
            (freqs_hz, psd) — frequency axis and power spectral density
        """
        indices = [self.brain.id_to_idx[nid] for nid in neuron_ids if nid in self.brain.id_to_idx]
        if not indices:
            return np.array([0.0]), np.array([0.0])

        # Record mean spike rate per step
        spike_train = np.zeros(n_windows, dtype=np.float64)
        for t in range(n_windows):
            self.brain.evolve(duration=window_ms)
            spikes = self.sample_spikes(dt_ms=window_ms)
            spike_train[t] = np.mean(spikes[indices]) * (1000.0 / window_ms)  # convert to Hz

        # Compute one-sided PSD
        fft = np.fft.rfft(spike_train)
        psd = (np.abs(fft) ** 2) / n_windows
        freqs = np.fft.rfftfreq(n_windows, d=window_ms / 1000.0)  # Hz

        return freqs, psd

    def get_amplitude_psd(
        self,
        neuron_ids: List[int],
        n_windows: int = 200,
        window_ms: float = 1.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Record amplitude (deterministic) time series and compute PSD.

        Unlike get_spike_psd, this uses the raw wave amplitudes (no Poisson sampling).
        Useful for comparing deterministic vs stochastic PSD — the difference
        shows the contribution of Poisson shot noise.

        Args:
            neuron_ids: Neuron IDs to record from
            n_windows: Number of time steps
            window_ms: Duration per step (ms)

        Returns:
            (freqs_hz, psd)
        """
        indices = [self.brain.id_to_idx[nid] for nid in neuron_ids if nid in self.brain.id_to_idx]
        if not indices:
            return np.array([0.0]), np.array([0.0])

        amp_train = np.zeros(n_windows, dtype=np.float64)
        for t in range(n_windows):
            self.brain.evolve(duration=window_ms)
            amp_train[t] = np.mean(self._get_amplitudes()[indices])

        fft = np.fft.rfft(amp_train)
        psd = (np.abs(fft) ** 2) / n_windows
        freqs = np.fft.rfftfreq(n_windows, d=window_ms / 1000.0)

        return freqs, psd

    # ── Quantum bump simulation ────────────────────────────────────────────────

    def simulate_quantum_bumps(
        self,
        neuron_ids: List[int],
        n_steps: int = 500,
        dt_ms: float = 1.0,
        low_rate_scale: float = 50.0,
        high_rate_scale: float = 2000.0,
    ) -> dict:
        """
        Simulate quantum bump regime (dim light) vs high-rate regime (bright light).

        At low rate: Poisson spike arrivals are sparse → individual bumps visible
                     → CV close to 1.0 (pure Poisson)
        At high rate: many overlapping spikes → smooth → CV drops below 0.5
                      → 12 Hz oscillation from phototransduction dominates PSD

        Args:
            neuron_ids: Neuron IDs to record from
            n_steps: Number of time steps
            dt_ms: Step size (ms)
            low_rate_scale: rate_scale_hz for dim-light condition
            high_rate_scale: rate_scale_hz for bright-light condition

        Returns:
            Dict with cv_dim, cv_bright, psd_dim, psd_bright, freqs
        """
        indices = [self.brain.id_to_idx[nid] for nid in neuron_ids if nid in self.brain.id_to_idx]
        if not indices:
            return {}

        results = {}

        for label, scale in [('dim', low_rate_scale), ('bright', high_rate_scale)]:
            orig_scale = self.rate_scale_hz
            self.rate_scale_hz = scale

            spike_train = []
            for _ in range(n_steps):
                self.brain.evolve(duration=dt_ms)
                spikes = self.sample_spikes(dt_ms=dt_ms)
                mean_rate = float(np.mean(spikes[indices])) * (1000.0 / dt_ms)
                spike_train.append(mean_rate)

            spike_train = np.array(spike_train)
            mu = float(np.mean(spike_train))
            sigma = float(np.std(spike_train))
            cv = sigma / mu if mu > 1e-10 else float('nan')

            fft = np.fft.rfft(spike_train)
            psd = (np.abs(fft) ** 2) / n_steps
            freqs = np.fft.rfftfreq(n_steps, d=dt_ms / 1000.0)

            results[label] = {
                'rate_scale_hz': scale,
                'mean_rate_hz': float(mu),
                'cv': float(cv),
                'spike_train': spike_train.tolist(),
                'psd': psd.tolist(),
            }
            results['freqs_hz'] = freqs.tolist()

            self.rate_scale_hz = orig_scale

        return results
