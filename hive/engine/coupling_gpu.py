"""
GPU-accelerated coupling engine.
Computes coupling forces for 5.3M synapses using GPU (MLX/CuPy) or optimized CPU.
"""

import numpy as np
from typing import Dict
from ..gpu_utils import GPU_AVAILABLE, GPU_BACKEND, to_gpu, to_cpu, zeros, get_array_module, scatter_add, synchronize

try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None

if GPU_AVAILABLE and GPU_BACKEND == "CUPY":
    import cupy as cp


class CouplingEngineGPU:
    """
    GPU-accelerated coupling engine using vectorized operations.
    Falls back to optimized CPU if GPU not available.
    """
    
    def __init__(self, connectome, config: dict):
        self.connectome = connectome
        self.config = config
        self.num_neurons = len(connectome.neurons)
        
        # ID mappings
        self.id_to_idx = {nid: i for i, nid in enumerate(connectome.neurons.keys())}
        self.idx_to_id = {i: nid for nid, i in self.id_to_idx.items()}
        
        self.use_delays = config['oscillator']['use_delays']
        
        backend_name = GPU_BACKEND if GPU_AVAILABLE else 'CPU'
        print(f"Initializing coupling engine ({backend_name})...")
        self._build_coupling_matrices_vectorized()
    
    def _build_coupling_matrices_vectorized(self):
        """Build coupling matrices in vectorized form for GPU."""
        print("Building vectorized coupling matrices for GPU...")
        
        nt_config = self.config['neurotransmitters']
        
        # Collect all synapses
        pre_indices = []
        post_indices = []
        weights = []
        offsets = []
        
        for syn in self.connectome.synapses:
            pre_idx = self.id_to_idx[syn.pre_id]
            post_idx = self.id_to_idx[syn.post_id]
            
            pre_indices.append(pre_idx)
            post_indices.append(post_idx)
            
            weight = float(syn.weight) / 100.0
            weights.append(weight)
            
            nt_lower = syn.nt_type.lower()
            if nt_lower in nt_config:
                phase_offset = nt_config[nt_lower]['phase_offset']
            else:
                phase_offset = 0
            offsets.append(np.deg2rad(phase_offset))
        
        # Convert to arrays and move to GPU
        self.pre_indices = to_gpu(np.array(pre_indices, dtype=np.int32))
        self.post_indices = to_gpu(np.array(post_indices, dtype=np.int32))
        self.weights = to_gpu(np.array(weights, dtype=np.float32))
        self.offsets = to_gpu(np.array(offsets, dtype=np.float32))
        
        self.num_synapses = len(pre_indices)
        
        print(f"Built GPU coupling matrices: {self.num_synapses:,} synapses")
        if GPU_AVAILABLE:
            if MLX_AVAILABLE:
                # Estimate memory for MLX
                mem_mb = len(pre_indices) * 4 * 4 / 1024 / 1024  # 4 arrays × 4 bytes
            else:
                mem_mb = (self.pre_indices.nbytes + self.post_indices.nbytes + 
                         self.weights.nbytes + self.offsets.nbytes) / 1024 / 1024
            print(f"GPU memory used: {mem_mb:.1f} MB")
    
    def compute_coupling_forces(self, 
                                phase: np.ndarray, 
                                amplitude: np.ndarray,
                                spatial_index=None) -> np.ndarray:
        """
        Compute coupling forces using GPU-accelerated scatter-add.
        F_j = Σ_i w_ij * sin(φ_i - φ_j + θ_ij) * A_i
        """
        # Move inputs to GPU (handle if already on GPU)
        if MLX_AVAILABLE:
            if isinstance(phase, mx.array):
                phase_gpu = phase
                amplitude_gpu = amplitude
            else:
                phase_gpu = to_gpu(phase.astype(np.float32))
                amplitude_gpu = to_gpu(amplitude.astype(np.float32))
        else:
            phase_gpu = to_gpu(phase.astype(np.float32))
            amplitude_gpu = to_gpu(amplitude.astype(np.float32))
        
        # Vectorized computation for ALL 5.3M synapses at once
        if MLX_AVAILABLE:
            # MLX implementation
            pre_phases = phase_gpu[self.pre_indices]
            pre_amplitudes = amplitude_gpu[self.pre_indices]
            post_phases = phase_gpu[self.post_indices]
            
            # Compute phase differences: φ_i - φ_j + θ_ij
            phase_diffs = pre_phases - post_phases + self.offsets
            
            # Compute forces: w_ij * sin(phase_diff) * A_i
            synapse_forces = self.weights * mx.sin(phase_diffs) * pre_amplitudes
            
            # Accumulate forces per postsynaptic neuron using scatter-add
            forces_gpu = zeros(self.num_neurons, dtype=np.float32)
            forces_gpu = scatter_add(forces_gpu, self.post_indices, synapse_forces)
            
            # Don't sync here - let MLX defer evaluation until forces are used
            
        else:
            # CuPy or NumPy implementation
            xp = get_array_module(phase_gpu)
            
            # Get presynaptic phases and amplitudes
            pre_phases = phase_gpu[self.pre_indices]
            pre_amplitudes = amplitude_gpu[self.pre_indices]
            
            # Get postsynaptic phases
            post_phases = phase_gpu[self.post_indices]
            
            # Compute phase differences: φ_i - φ_j + θ_ij
            phase_diffs = pre_phases - post_phases + self.offsets
            
            # Compute forces: w_ij * sin(phase_diff) * A_i
            synapse_forces = self.weights * xp.sin(phase_diffs) * pre_amplitudes
            
            # Accumulate forces per postsynaptic neuron using scatter-add
            forces_gpu = zeros(self.num_neurons, dtype=np.float32)
            forces_gpu = scatter_add(forces_gpu, self.post_indices, synapse_forces)
        
        # Move result back to CPU
        forces = to_cpu(forces_gpu).astype(np.float64)
        
        return forces
    
    def modulate_coupling(self, multiplier: float, neuron_indices: np.ndarray = None):
        """Modulate coupling strength."""
        if neuron_indices is None:
            self.weights *= multiplier
        else:
            # Modulate only synapses involving specific neurons.
            # MLX has no boolean-mask assignment ("boolean indices are not yet
            # supported"), so select with where() rather than indexing.
            mask = np.isin(to_cpu(self.post_indices), neuron_indices)
            if MLX_AVAILABLE and isinstance(self.weights, mx.array):
                self.weights = mx.where(
                    mx.array(mask), self.weights * multiplier, self.weights
                )
            else:
                self.weights[mask] *= multiplier
    
    def get_all_weights_as_array(self) -> np.ndarray:
        """Get all weights as CPU array."""
        return to_cpu(self.weights)
    
    def set_all_weights_from_array(self, weight_array: np.ndarray):
        """Set all weights from CPU array."""
        self.weights = to_gpu(weight_array.astype(np.float32))
    
    def snapshot_weights(self) -> np.ndarray:
        """Snapshot weights."""
        return self.get_all_weights_as_array().copy()
    
    def restore_weights(self, weight_snapshot: np.ndarray):
        """Restore weights."""
        self.set_all_weights_from_array(weight_snapshot)
    
    # Compatibility methods for old API
    def get_connection_strength(self, pre_id: int, post_id: int) -> float:
        """Get connection strength (CPU operation)."""
        pre_idx = self.id_to_idx.get(pre_id)
        post_idx = self.id_to_idx.get(post_id)
        if pre_idx is None or post_idx is None:
            return 0.0
        
        pre_arr = to_cpu(self.pre_indices)
        post_arr = to_cpu(self.post_indices)
        weights_arr = to_cpu(self.weights)
        
        mask = (pre_arr == pre_idx) & (post_arr == post_idx)
        return float(np.sum(weights_arr[mask]))
    
    def _count_total_synapses(self) -> int:
        """Count total synapses."""
        return self.num_synapses
    
    def get_weight_modifications_array(self, neuron_indices: np.ndarray) -> np.ndarray:
        """Get weight modifications for intra-group connections."""
        pre_arr = to_cpu(self.pre_indices)
        post_arr = to_cpu(self.post_indices)
        
        neuron_set = set(neuron_indices)
        mask = np.array([pre in neuron_set and post in neuron_set 
                        for pre, post in zip(pre_arr, post_arr)])
        
        return mask.astype(np.float32)
    
    def apply_weight_modifications(self, modifications: np.ndarray, scale: float = 1.0):
        """Apply weight modifications."""
        mods_gpu = to_gpu(modifications.astype(np.float32))
        self.weights += mods_gpu * scale
    
    def get_incoming_sources(self, neuron_id: int) -> list:
        """Get incoming sources (CPU operation)."""
        post_idx = self.id_to_idx.get(neuron_id)
        if post_idx is None:
            return []
        
        pre_arr = to_cpu(self.pre_indices)
        post_arr = to_cpu(self.post_indices)
        weights_arr = to_cpu(self.weights)
        
        mask = post_arr == post_idx
        sources = {}
        for pre_idx, weight in zip(pre_arr[mask], weights_arr[mask]):
            pre_id = self.idx_to_id[pre_idx]
            sources[pre_id] = sources.get(pre_id, 0.0) + float(weight)
        
        return list(sources.items())
    
    def get_outgoing_targets(self, neuron_id: int) -> list:
        """Get outgoing targets (CPU operation)."""
        pre_idx = self.id_to_idx.get(neuron_id)
        if pre_idx is None:
            return []
        
        pre_arr = to_cpu(self.pre_indices)
        post_arr = to_cpu(self.post_indices)
        weights_arr = to_cpu(self.weights)
        
        mask = pre_arr == pre_idx
        targets = {}
        for post_idx, weight in zip(post_arr[mask], weights_arr[mask]):
            post_id = self.idx_to_id[post_idx]
            targets[post_id] = targets.get(post_id, 0.0) + float(weight)
        
        return list(targets.items())
