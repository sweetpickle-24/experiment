"""
Synaptic coupling between oscillators.
Computes coupling forces based on connectome topology and phase relationships.
"""

import numpy as np
from scipy.sparse import csr_matrix, coo_matrix
from typing import Dict, Tuple


class CouplingEngine:
    """
    Manages synaptic coupling between neurons.
    F_ij = w_ij * sin(φ_i - φ_j + θ_ij) * A_i
    """
    
    def __init__(self, connectome, config: dict):
        self.connectome = connectome
        self.config = config
        self.num_neurons = len(connectome.neurons)
        
        # Neuron ID to index mapping
        self.id_to_idx = {nid: i for i, nid in enumerate(connectome.neurons.keys())}
        self.idx_to_id = {i: nid for nid, i in self.id_to_idx.items()}
        
        # Transmission delays (optional)
        self.use_delays = config['oscillator']['use_delays']
        
        # Build coupling matrices
        self._build_coupling_matrices()
    
    def _build_coupling_matrices(self):
        """Build sparse coupling matrices from connectome, keeping ALL synapses as separate entries."""
        print("Building coupling matrices...")
        
        nt_config = self.config['neurotransmitters']
        
        # Collect all synapses as separate entries (COO format lists)
        row_indices = []  # post neurons
        col_indices = []  # pre neurons
        weights = []
        offsets = []
        
        for syn in self.connectome.synapses:
            pre_idx = self.id_to_idx[syn.pre_id]
            post_idx = self.id_to_idx[syn.post_id]
            
            # Each synapse is a separate entry
            row_indices.append(post_idx)
            col_indices.append(pre_idx)
            
            # Weight
            weight = float(syn.weight) / 100.0  # Normalize roughly
            weights.append(weight)
            
            # Phase offset
            nt_lower = syn.nt_type.lower()
            if nt_lower in nt_config:
                phase_offset = nt_config[nt_lower]['phase_offset']
            else:
                phase_offset = 0  # Default
            offsets.append(np.deg2rad(phase_offset))
        
        # Build COO matrices, then convert to CSR
        # Note: COO automatically sums duplicate entries when converting to CSR,
        # but we want to KEEP them separate! So we use sum_duplicates=False implicitly
        # by building from arrays that DON'T have duplicates at the array level
        
        # Actually, CSR WILL sum duplicates. We need a different approach.
        # Solution: Store as list of (pre_indices, weights, offsets) per post neuron
        
        self.post_synapses = [[] for _ in range(self.num_neurons)]
        
        for i, (post_idx, pre_idx, weight, offset) in enumerate(zip(row_indices, col_indices, weights, offsets)):
            self.post_synapses[post_idx].append((pre_idx, weight, offset))
        
        total_synapses = sum(len(syns) for syns in self.post_synapses)
        print(f"Built coupling matrices: {total_synapses} synapses (preserving all individual connections)")
    
    def compute_coupling_forces(self, 
                                phase: np.ndarray, 
                                amplitude: np.ndarray,
                                spatial_index=None) -> np.ndarray:
        """
        Compute coupling forces for all neurons.
        F_j = Σ_i w_ij * sin(φ_i - φ_j + θ_ij) * A_i
        """
        forces = np.zeros(self.num_neurons)
        
        # Iterate over postsynaptic neurons
        for post_idx in range(self.num_neurons):
            if not self.post_synapses[post_idx]:
                continue
            
            # Get all synapses targeting this neuron
            pre_indices, weights_list, offsets_list = zip(*self.post_synapses[post_idx])
            pre_indices = np.array(pre_indices)
            weights_arr = np.array(weights_list)
            offsets_arr = np.array(offsets_list)
            
            # Compute phase differences for all synapses
            phase_diff = phase[pre_indices] - phase[post_idx] + offsets_arr
            
            # Coupling force (sum over all synapses)
            force = np.sum(weights_arr * np.sin(phase_diff) * amplitude[pre_indices])
            forces[post_idx] = force
        
        return forces
    
    def modulate_coupling(self, multiplier: float, neuron_indices: np.ndarray = None):
        """
        Modulate coupling strength (neuromodulator effect).
        If neuron_indices is None, modulate all connections.
        """
        if neuron_indices is None:
            # Modulate all
            for post_idx in range(self.num_neurons):
                for i, (pre_idx, weight, offset) in enumerate(self.post_synapses[post_idx]):
                    self.post_synapses[post_idx][i] = (pre_idx, weight * multiplier, offset)
        else:
            # Modulate incoming connections to specific neurons
            for post_idx in neuron_indices:
                for i, (pre_idx, weight, offset) in enumerate(self.post_synapses[post_idx]):
                    self.post_synapses[post_idx][i] = (pre_idx, weight * multiplier, offset)
    
    def mutate_weights(self, mutation_rate: float, neuron_indices: np.ndarray = None):
        """
        Mutate synaptic weights for evolution.
        mutation_rate: fraction to change (e.g., 0.05 = ±5%)
        """
        if neuron_indices is None:
            # Mutate all
            for post_idx in range(self.num_neurons):
                for i, (pre_idx, weight, offset) in enumerate(self.post_synapses[post_idx]):
                    mutation = np.random.uniform(1 - mutation_rate, 1 + mutation_rate)
                    self.post_synapses[post_idx][i] = (pre_idx, weight * mutation, offset)
        else:
            # Mutate incoming connections to specific neurons
            for post_idx in neuron_indices:
                for i, (pre_idx, weight, offset) in enumerate(self.post_synapses[post_idx]):
                    mutation = np.random.uniform(1 - mutation_rate, 1 + mutation_rate)
                    self.post_synapses[post_idx][i] = (pre_idx, weight * mutation, offset)
    
    def get_connection_strength(self, pre_id: int, post_id: int) -> float:
        """Get total coupling strength between two neurons (sum of all synapses)."""
        pre_idx = self.id_to_idx.get(pre_id)
        post_idx = self.id_to_idx.get(post_id)
        if pre_idx is None or post_idx is None:
            return 0.0
        
        total = 0.0
        for p_idx, weight, offset in self.post_synapses[post_idx]:
            if p_idx == pre_idx:
                total += weight
        return total
    
    def get_outgoing_targets(self, neuron_id: int) -> list:
        """Get list of (target_id, total_weight) for outgoing connections."""
        pre_idx = self.id_to_idx.get(neuron_id)
        if pre_idx is None:
            return []
        
        # Accumulate weights by target
        targets = {}
        for post_idx in range(self.num_neurons):
            for p_idx, weight, offset in self.post_synapses[post_idx]:
                if p_idx == pre_idx:
                    post_id = self.idx_to_id[post_idx]
                    targets[post_id] = targets.get(post_id, 0.0) + weight
        
        return list(targets.items())
    
    def get_incoming_sources(self, neuron_id: int) -> list:
        """Get list of (source_id, total_weight) for incoming connections."""
        post_idx = self.id_to_idx.get(neuron_id)
        if post_idx is None:
            return []
        
        # Accumulate weights by source
        sources = {}
        for pre_idx, weight, offset in self.post_synapses[post_idx]:
            pre_id = self.idx_to_id[pre_idx]
            sources[pre_id] = sources.get(pre_id, 0.0) + weight
        
        return list(sources.items())
    
    def get_all_weights_as_array(self) -> np.ndarray:
        """Get all synaptic weights as a flat array (for mutation/evolution)."""
        all_weights = []
        for post_idx in range(self.num_neurons):
            for pre_idx, weight, offset in self.post_synapses[post_idx]:
                all_weights.append(weight)
        return np.array(all_weights)
    
    def set_all_weights_from_array(self, weight_array: np.ndarray):
        """Set all synaptic weights from a flat array."""
        idx = 0
        for post_idx in range(self.num_neurons):
            for i in range(len(self.post_synapses[post_idx])):
                pre_idx, _, offset = self.post_synapses[post_idx][i]
                self.post_synapses[post_idx][i] = (pre_idx, weight_array[idx], offset)
                idx += 1
    
    def get_weight_modifications_array(self, neuron_indices: np.ndarray) -> np.ndarray:
        """
        Get array of weight modifications to strengthen intra-group connections.
        neuron_indices: Array of neuron INDICES (0..N-1), NOT IDs.
        """
        modifications = np.zeros(self._count_total_synapses())
        neuron_set = set(neuron_indices)
        
        idx = 0
        for post_idx in range(self.num_neurons):
            for pre_idx, weight, offset in self.post_synapses[post_idx]:
                if post_idx in neuron_set and pre_idx in neuron_set:
                    modifications[idx] = 1.0
                idx += 1
        
        return modifications
    
    def apply_weight_modifications(self, modifications: np.ndarray, scale: float = 1.0):
        """Apply weight modifications (for attractor carving, etc.)."""
        idx = 0
        for post_idx in range(self.num_neurons):
            for i in range(len(self.post_synapses[post_idx])):
                pre_idx, weight, offset = self.post_synapses[post_idx][i]
                self.post_synapses[post_idx][i] = (pre_idx, weight + modifications[idx] * scale, offset)
                idx += 1
    
    def _count_total_synapses(self) -> int:
        """Count total number of synapses."""
        return sum(len(syns) for syns in self.post_synapses)
    
    def snapshot_weights(self) -> np.ndarray:
        """Take a snapshot of current weights for later restore."""
        return self.get_all_weights_as_array().copy()
    
    def restore_weights(self, weight_snapshot: np.ndarray):
        """Restore weights from a snapshot."""
        self.set_all_weights_from_array(weight_snapshot)
