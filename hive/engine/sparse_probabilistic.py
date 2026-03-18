"""
Sparse Probabilistic Wave Engine - Memory Efficient

Instead of dense 3D grids, use sparse representation:
- Only track voxels containing neurons
- Direct neuron-to-neuron coupling (no full FFT)
- Still probabilistic (mean + variance)
- 100× less memory

This is the production version for full brain smell testing.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple
import time

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None


@dataclass
class SparseProbabilisticState:
    """Probabilistic state for actual neurons (not grid voxels)."""
    mean_phase: np.ndarray      # E[φ] per neuron
    mean_velocity: np.ndarray   # E[v] per neuron
    mean_amplitude: np.ndarray  # E[A] per neuron
    var_phase: np.ndarray       # Var[φ] per neuron
    var_amplitude: np.ndarray   # Var[A] per neuron
    neuron_ids: list            # Neuron IDs
    time: float


class SparseProbabilisticBrain:
    """
    Memory-efficient probabilistic brain using sparse representation.
    
    Key difference from dense grid:
    - Tracks N neurons directly (not grid voxels)
    - Coupling uses synapse structure (not FFT on full space)
    - Still probabilistic (mean-field theory)
    - ~100× less memory than dense grid
    
    Memory: N neurons × 5 fields × 4 bytes
    - 15K neurons: 300 KB (vs. 30 MB for dense grid)
    - 139K neurons: 2.8 MB (vs. 300 MB for dense grid)
    """
    
    def __init__(self, connectome, config=None, use_mlx=True):
        """
        Initialize sparse probabilistic brain.
        
        Args:
            connectome: Connectome with neurons and synapses
            config: Configuration dict
            use_mlx: Use MLX for GPU acceleration
        """
        print("\n" + "="*70)
        print("SPARSE PROBABILISTIC BRAIN (Memory Efficient)")
        print("="*70)
        
        self.connectome = connectome
        self.config = config or {}
        self.use_mlx = use_mlx and MLX_AVAILABLE
        
        if self.use_mlx:
            print("✓ MLX GPU acceleration enabled")
        
        # Build neuron index
        self.neuron_ids = list(connectome.neurons.keys())
        self.num_neurons = len(self.neuron_ids)
        self.id_to_idx = {nid: idx for idx, nid in enumerate(self.neuron_ids)}
        
        print(f"Neurons: {self.num_neurons:,}")
        print(f"Synapses: {len(connectome.synapses):,}")
        
        # Initialize probability fields
        self._initialize_fields()
        
        # Build coupling structure
        self._build_coupling_structure()
        
        # Physics parameters
        self.dt = 0.1  # 0.1ms (10× faster than before, matches biological timescales)
        self.gamma = 0.1
        self.sigma_noise = 0.1
        self.time = 0.0
        
        # Temporal memory: ring buffer of amplitude snapshots
        # Biological basis: lamina L1/L2 H-current creates ~10-50ms temporal memory
        # T4/T5 direction selectivity requires access to ~20ms past state (Haag et al. 2017)
        self.amplitude_history = []   # List of np.ndarray snapshots
        self.history_max = 10         # Max 10 snapshots
        self.history_interval_ms = 5.0  # Snapshot every 5ms
        self._last_history_time = -999.0
        
        memory_mb = self.num_neurons * 5 * 4 / 1024 / 1024
        print(f"✓ Initialized: {self.num_neurons:,} neurons, {memory_mb:.1f} MB")
        print("="*70)
    
    def _initialize_fields(self):
        """Initialize probabilistic fields for all neurons."""
        # Mean fields
        self.mean_phase = np.random.uniform(-np.pi, np.pi, self.num_neurons).astype(np.float32)
        self.mean_velocity = np.zeros(self.num_neurons, dtype=np.float32)
        self.mean_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        
        # Variance fields
        self.var_phase = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        self.var_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.01
        
        # External force
        self.external_force = np.zeros(self.num_neurons, dtype=np.float32)
        
        # Natural frequencies (default: 10 Hz alpha)
        self.omega0 = np.ones(self.num_neurons, dtype=np.float32) * (2 * np.pi * 10.0 / 1000.0)
        
        # Reset temporal memory on field initialization
        self.amplitude_history = []
        self._last_history_time = -999.0
        self.time = 0.0
        
        # Move to GPU if using MLX
        if self.use_mlx:
            self.mean_phase = mx.array(self.mean_phase)
            self.mean_velocity = mx.array(self.mean_velocity)
            self.mean_amplitude = mx.array(self.mean_amplitude)
            self.var_phase = mx.array(self.var_phase)
            self.var_amplitude = mx.array(self.var_amplitude)
            self.external_force = mx.array(self.external_force)
            self.omega0 = mx.array(self.omega0)
    
    def _build_coupling_structure(self):
        """Build sparse coupling matrix from synapses with layer-specific gains."""
        print("Building coupling structure...")
        
        # Build adjacency lists for fast coupling computation
        synapses = self.connectome.synapses
        
        # Detect if this is a vision network and map neurons to regions
        is_vision = self.num_neurons > 50000
        neuron_regions = {}
        
        if is_vision:
            # Map neurons to visual regions for layer-specific tuning
            print("  Analyzing visual pathway structure...")
            from ..substrate.visual_pathway import VISUAL_NEURON_TYPES
            
            for nid, neuron in self.connectome.neurons.items():
                # Neuron.cell_types is a list of strings
                cell_types_str = ' '.join(neuron.cell_types) if neuron.cell_types else ''
                for region, types in VISUAL_NEURON_TYPES.items():
                    if any(keyword in cell_types_str for keyword in types):
                        neuron_regions[nid] = region
                        break
        
        # Pre-allocate arrays
        pre_indices = []
        post_indices = []
        weights = []
        
        for syn in synapses:
            if syn.pre_id in self.id_to_idx and syn.post_id in self.id_to_idx:
                pre_indices.append(self.id_to_idx[syn.pre_id])
                post_indices.append(self.id_to_idx[syn.post_id])
                weights.append(float(syn.weight))
        
        self.pre_indices = np.array(pre_indices, dtype=np.int32)
        self.post_indices = np.array(post_indices, dtype=np.int32)
        self.syn_weights = np.array(weights, dtype=np.float32)
        
        # Normalize weights WITHOUT attenuation for large networks
        # Biological rationale: Vision networks maintain signal strength through
        # ~1000Hz transmission rates (Olberg 2012) vs ~100Hz in olfaction
        if len(self.syn_weights) > 0:
            max_weight = np.max(self.syn_weights)
            if max_weight > 0:
                # Baseline normalization only (no attenuation)
                # This preserves biological signal strength ratios
                self.syn_weights = self.syn_weights / max_weight
                
                # Apply network-specific gain for vision (>50K neurons)
                # Vision: 10× higher transmission rate than olfaction
                if self.num_neurons > 50000:
                    vision_gain = 10.0
                    self.syn_weights = self.syn_weights * vision_gain
                    print(f"  Vision network detected: {vision_gain}× coupling gain applied")
                else:
                    print(f"  Olfaction network: baseline coupling")
        
        print(f"✓ Coupling: {len(self.syn_weights):,} synapses")
        
        if self.use_mlx:
            self.pre_indices = mx.array(self.pre_indices)
            self.post_indices = mx.array(self.post_indices)
            self.syn_weights = mx.array(self.syn_weights)
    
    def evolve(self, duration=100.0):
        """Evolve for specified duration."""
        num_steps = int(duration / self.dt)
        history_interval_steps = max(1, int(self.history_interval_ms / self.dt))
        
        for step in range(num_steps):
            self._step()
            
            # Clear MLX graph every 100 steps to avoid memory buildup
            if self.use_mlx and step % 100 == 0:
                mx.eval(self.mean_phase)
                mx.eval(self.mean_velocity)
                mx.eval(self.var_phase)
            
            # Update temporal memory: snapshot amplitude every history_interval_ms
            # Biological basis: lamina L1/L2 H-current creates ~5-50ms temporal memory
            # Required for T4/T5 direction selectivity (Haag et al. 2017, Borst 2024)
            if step % history_interval_steps == 0:
                if self.use_mlx:
                    mx.eval(self.mean_amplitude)
                    snap = np.array(self.mean_amplitude).copy()
                else:
                    snap = self.mean_amplitude.copy()
                self.amplitude_history.append(snap)
                if len(self.amplitude_history) > self.history_max:
                    self.amplitude_history.pop(0)
            
            # if step % 10 == 0:
            #     print(f"  Step {step}/{num_steps}, time={self.time:.1f}ms", end='\r')
        
        # print(f"  ✓ Evolution complete: {self.time:.1f}ms")
    
    def get_amplitude_delayed(self, delay_ms: float) -> np.ndarray:
        """
        Return amplitude snapshot from delay_ms ago.
        
        Biological basis: T4 receives slow inhibitory inputs (~20ms delay)
        from trailing-side Mi4/C3/CT1 neurons (Haag et al. 2017).
        
        Args:
            delay_ms: How far back in time (ms)
        
        Returns:
            numpy array of amplitude values, or current amplitude if no history
        """
        if not self.amplitude_history:
            if self.use_mlx:
                return np.array(self.mean_amplitude)
            return self.mean_amplitude.copy()
        
        # Calculate which history index corresponds to delay_ms
        steps_back = int(delay_ms / self.history_interval_ms)
        idx = max(0, len(self.amplitude_history) - 1 - steps_back)
        return self.amplitude_history[idx]
    
    def _step(self):
        """Single integration step."""
        if self.use_mlx:
            self._step_mlx()
        else:
            self._step_numpy()
        
        self.time += self.dt
    
    def _step_mlx(self):
        """MLX GPU step with analytical coupling."""
        # Compute coupling force using analytical expectation
        coupling_force = self._compute_coupling_mlx()
        
        # Update mean velocity
        accel = (-2.0 * self.gamma * self.mean_velocity 
                - self.omega0**2 * self.mean_phase 
                + coupling_force 
                + self.external_force)
        
        self.mean_velocity = self.mean_velocity + accel * self.dt
        
        # Update mean phase
        self.mean_phase = self.mean_phase + self.mean_velocity * self.dt
        self.mean_phase = mx.arctan2(mx.sin(self.mean_phase), mx.cos(self.mean_phase))
        
        # Update variance
        self.var_phase = self.var_phase * (1.0 - 2.0 * self.gamma * self.dt) + self.sigma_noise**2 * self.dt
        self.var_phase = mx.clip(self.var_phase, 0.01, 10.0)
        
        # Amplitude (driven by velocity magnitude)
        amp_drive = mx.abs(self.mean_velocity) * 0.1
        self.mean_amplitude = self.mean_amplitude * (1.0 - self.gamma * self.dt) + amp_drive * self.dt
        self.mean_amplitude = mx.clip(self.mean_amplitude, 0.001, 10.0)
    
    def _step_numpy(self):
        """NumPy CPU step."""
        coupling_force = self._compute_coupling_numpy()
        
        accel = (-2.0 * self.gamma * self.mean_velocity 
                - self.omega0**2 * self.mean_phase 
                + coupling_force 
                + self.external_force)
        
        self.mean_velocity += accel * self.dt
        self.mean_phase += self.mean_velocity * self.dt
        self.mean_phase = np.arctan2(np.sin(self.mean_phase), np.cos(self.mean_phase))
        
        self.var_phase = self.var_phase * (1.0 - 2.0 * self.gamma * self.dt) + self.sigma_noise**2 * self.dt
        self.var_phase = np.clip(self.var_phase, 0.01, 10.0)
        
        # Amplitude (driven by velocity magnitude)
        amp_drive = np.abs(self.mean_velocity) * 0.1
        self.mean_amplitude = self.mean_amplitude * (1.0 - self.gamma * self.dt) + amp_drive * self.dt
        self.mean_amplitude = np.clip(self.mean_amplitude, 0.001, 10.0)
    
    def _compute_coupling_mlx(self):
        """Compute coupling using sparse synapse structure (MLX)."""
        # Get phase differences for all synapses
        phase_pre = self.mean_phase[self.pre_indices]
        phase_post = self.mean_phase[self.post_indices]
        amp_pre = self.mean_amplitude[self.pre_indices]
        
        # Phase difference
        delta_phi = phase_pre - phase_post
        
        # Analytical expectation: ⟨sin(Δφ)⟩ ≈ sin(⟨Δφ⟩) · exp(-Var[Δφ]/2)
        # Approximate Var[Δφ] as average variance
        var_correction = mx.exp(-0.1 / 2.0)  # Simplified
        
        # Synapse forces
        syn_forces = self.syn_weights * mx.sin(delta_phi) * amp_pre * var_correction
        
        # Accumulate to postsynaptic neurons
        forces = mx.zeros(self.num_neurons, dtype=mx.float32)
        forces = forces.at[self.post_indices].add(syn_forces)
        
        return forces
    
    def _compute_coupling_numpy(self):
        """Compute coupling using sparse synapse structure (NumPy)."""
        phase_pre = self.mean_phase[self.pre_indices]
        phase_post = self.mean_phase[self.post_indices]
        amp_pre = self.mean_amplitude[self.pre_indices]
        
        delta_phi = phase_pre - phase_post
        var_correction = np.exp(-0.1 / 2.0)
        
        syn_forces = self.syn_weights * np.sin(delta_phi) * amp_pre * var_correction
        
        forces = np.zeros(self.num_neurons, dtype=np.float32)
        np.add.at(forces, self.post_indices, syn_forces)
        
        return forces
    
    def inject_odor(self, glom_pattern, strength=50.0):
        """
        Inject odor as external force to actual PNs.
        
        Args:
            glom_pattern: 20-dim glomerular pattern
            strength: Injection strength multiplier (default 50.0 for stronger response)
        """
        from ..substrate.olfactory_subgraph import classify_olfactory_neuron
        
        # Find actual PN neurons
        pn_ids = []
        if hasattr(self.connectome, 'neurons'):
            for nid, neuron in self.connectome.neurons.items():
                if classify_olfactory_neuron(neuron) == 'PN':
                    pn_ids.append(nid)
        
        if not pn_ids:
            # Fallback: use first 20%
            num_pns = int(self.num_neurons * 0.2)
            pn_indices = list(range(num_pns))
        else:
            # Get indices of PNs in our neuron list
            pn_indices = [i for i, nid in enumerate(self.neuron_ids) if nid in pn_ids]
        
        # Distribute glomerular pattern across PNs
        # Each glomerular channel maps to ~110 PNs (2198 PNs / 20 channels)
        pns_per_channel = max(1, len(pn_indices) // len(glom_pattern))
        
        if self.use_mlx:
            self.external_force = mx.zeros(self.num_neurons, dtype=mx.float32)
            for i, channel_strength in enumerate(glom_pattern):
                # Inject to PNs corresponding to this glomerular channel
                start_idx = i * pns_per_channel
                end_idx = min(start_idx + pns_per_channel, len(pn_indices))
                for pn_idx in pn_indices[start_idx:end_idx]:
                    self.external_force = self.external_force.at[pn_idx].add(channel_strength * strength)
        else:
            self.external_force = np.zeros(self.num_neurons, dtype=np.float32)
            for i, channel_strength in enumerate(glom_pattern):
                start_idx = i * pns_per_channel
                end_idx = min(start_idx + pns_per_channel, len(pn_indices))
                for pn_idx in pn_indices[start_idx:end_idx]:
                    self.external_force[pn_idx] = channel_strength * strength
    
    def reset(self, deterministic=False):
        """
        Reset to initial state.
        
        Args:
            deterministic: If True, use fixed initial conditions for reproducibility.
                         If False, randomize phases (default behavior).
        """
        if deterministic:
            # Fixed initial conditions for concentration invariance testing
            self.mean_phase = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_velocity = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        else:
            # Random initialization (original behavior)
            self.mean_phase = np.random.uniform(-np.pi, np.pi, self.num_neurons).astype(np.float32)
            self.mean_velocity = np.zeros(self.num_neurons, dtype=np.float32)
            self.mean_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        
        # Always reset variances and external force
        self.var_phase = np.ones(self.num_neurons, dtype=np.float32) * 0.1
        self.var_amplitude = np.ones(self.num_neurons, dtype=np.float32) * 0.01
        self.external_force = np.zeros(self.num_neurons, dtype=np.float32)
        
        # Clear amplitude history ring buffer
        self.amplitude_history = []
        self._last_history_time = 0.0
        
        # Move to GPU if using MLX
        if self.use_mlx:
            self.mean_phase = mx.array(self.mean_phase)
            self.mean_velocity = mx.array(self.mean_velocity)
            self.mean_amplitude = mx.array(self.mean_amplitude)
            self.var_phase = mx.array(self.var_phase)
            self.var_amplitude = mx.array(self.var_amplitude)
            self.external_force = mx.array(self.external_force)
        
        self.time = 0.0
    
    def get_region_activity(self, region='PN', normalize_kc=False, target_sparsity=0.06):
        """
        Extract activity for region.
        
        Args:
            region: 'PN', 'KC', 'LN', or 'MBON'
            normalize_kc: If True and region='KC', apply APL-like normalization  
            target_sparsity: Target fraction of active KCs (default 0.06 = 6%)
        """
        # Filter neurons by type using olfactory classification
        from ..substrate.olfactory_subgraph import classify_olfactory_neuron
        
        if hasattr(self.connectome, 'neurons'):
            # Get neuron IDs matching the region
            region_ids = []
            for nid, neuron in self.connectome.neurons.items():
                neuron_type = classify_olfactory_neuron(neuron)
                if neuron_type == region:
                    region_ids.append(nid)
            
            if not region_ids:
                # Fallback: return all activity
                if self.use_mlx:
                    return np.array(self.mean_amplitude)
                else:
                    return self.mean_amplitude.copy()
            
            # Find indices in our neuron list
            indices = [i for i, nid in enumerate(self.neuron_ids) if nid in region_ids]
            
            if not indices:
                # No matching neurons, return zeros
                return np.zeros(20)  # Default to 20 for glomerular pattern
            
            # Extract subset
            if self.use_mlx:
                activity = np.array(self.mean_amplitude)[indices]
            else:
                activity = self.mean_amplitude[indices]
            
            # If PN region, aggregate to 20 channels (glomerular code)
            if region == 'PN' and len(activity) > 20:
                # Reshape to 20 bins
                n_bins = 20
                bin_size = len(activity) // n_bins
                binned = []
                for i in range(n_bins):
                    start = i * bin_size
                    end = start + bin_size if i < n_bins - 1 else len(activity)
                    binned.append(activity[start:end].mean())
                return np.array(binned)
            
            # Apply normalization if requested for KC region
            if normalize_kc and region == 'KC':
                activity = self._apply_kc_normalization(activity, target_sparsity)
            
            return activity
        else:
            # No neuron metadata, return all
            if self.use_mlx:
                return np.array(self.mean_amplitude)
            else:
                return self.mean_amplitude.copy()
    
    def _apply_kc_normalization(self, kc_activity, target_sparsity=0.06):
        """
        Apply winner-take-all normalization to maintain stable KC sparsity.
        
        Mimics APL (Anterior Paired Lateral) neuron feedback inhibition in Drosophila.
        The APL neuron monitors total KC activity and provides divisive normalization
        to maintain ~5-7% sparsity regardless of input strength.
        
        Reference: Lin et al. (2014) Nature Neuroscience
        
        Args:
            kc_activity: KC activity pattern (continuous amplitudes)
            target_sparsity: Target fraction of active KCs (default 0.06 = 6%)
        
        Returns:
            normalized_activity: Activity with adaptive threshold applied
        """
        if len(kc_activity) == 0:
            return kc_activity
        
        # Compute adaptive threshold to achieve target sparsity
        sorted_activity = np.sort(kc_activity)[::-1]  # Sort descending
        threshold_idx = int(len(kc_activity) * target_sparsity)
        
        if threshold_idx >= len(sorted_activity):
            threshold = 0.0
        else:
            threshold = sorted_activity[threshold_idx]
        
        # Apply soft threshold (subtract and clip to zero)
        normalized = np.maximum(0.0, kc_activity - threshold)
        
        return normalized
    
    def get_state(self):
        """Get current state."""
        if self.use_mlx:
            mean_phase = np.array(self.mean_phase)
            mean_velocity = np.array(self.mean_velocity)
            mean_amplitude = np.array(self.mean_amplitude)
            var_phase = np.array(self.var_phase)
            var_amplitude = np.array(self.var_amplitude)
        else:
            mean_phase = self.mean_phase
            mean_velocity = self.mean_velocity
            mean_amplitude = self.mean_amplitude
            var_phase = self.var_phase
            var_amplitude = self.var_amplitude
        
        return SparseProbabilisticState(
            mean_phase=mean_phase,
            mean_velocity=mean_velocity,
            mean_amplitude=mean_amplitude,
            var_phase=var_phase,
            var_amplitude=var_amplitude,
            neuron_ids=self.neuron_ids,
            time=self.time
        )


if __name__ == "__main__":
    print("\nSparse Probabilistic Brain - Memory Efficient")
    print("Tracks neurons directly, not grid voxels")
    print("100× less memory than dense grid approach")
