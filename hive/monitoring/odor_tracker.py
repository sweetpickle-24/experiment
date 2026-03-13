"""
Odor processing tracker for the wave-based fly brain.

Tracks:
- PN activity during odor presentation (mean amplitude, coherence)
- MB (Kenyon cell) activity as downstream readout
- LH (lateral horn) activity as innate response readout  
- Offset persistence: does PN activity linger after odor removed?
- Trial-to-trial reproducibility: do repeated presentations converge?
- Concentration invariance: does identity survive concentration scaling?
- Pattern signatures per odor for cross-trial comparison
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class OdorTrialRecord:
    """Single trial of odor presentation."""
    odor_name: str
    odor_family: str
    concentration: float
    onset_time: float
    offset_time: float
    
    # During stimulation
    pn_amplitudes: List[float] = field(default_factory=list)   # mean |x| of PNs per step
    pn_coherence: List[float] = field(default_factory=list)    # phase coherence per step
    mb_amplitudes: List[float] = field(default_factory=list)   # mean |x| of KCs per step
    lh_amplitudes: List[float] = field(default_factory=list)   # mean |x| of LH neurons per step
    
    # After offset (post-odor window)
    pn_persistence: List[float] = field(default_factory=list)  # PN amplitude after offset
    pn_coherence_persistence: List[float] = field(default_factory=list)
    
    # State signature: mean oscillator state over stimulus window
    pn_phase_signature: Optional[np.ndarray] = None  # mean phase of PNs during stim
    pn_amplitude_signature: Optional[np.ndarray] = None  # mean amplitude of PNs during stim


class OdorTracker:
    """
    Tracks odor processing across the antennal lobe → MB → LH pathway.
    
    Measures:
    A. During odor: PN drive strength and phase coherence
    B. After odor: PN trace persistence (offset persistence test)
    C. Across trials: reproducibility of PN state signatures
    D. Across concentrations: identity preservation at different intensities
    E. Glomerular channel activation (what the input actually looks like)
    """
    
    def __init__(self):
        self.pn_ids: List[int] = []
        self.pn_indices: List[int] = []  # 0-indexed positions in oscillator arrays
        self.mb_ids: List[int] = []
        self.mb_indices: List[int] = []
        self.lh_ids: List[int] = []
        self.lh_indices: List[int] = []
        
        self.id_to_idx: Dict[int, int] = {}
        
        # All trial records
        self.trials: List[OdorTrialRecord] = []
        self.current_trial: Optional[OdorTrialRecord] = None
        
        # Post-odor tracking state
        self._post_odor_steps = 0
        self._post_odor_max_steps = 200   # ~200ms post-odor window
        self._tracking_post_odor = False
        
        # Phase signatures per odor name for comparison
        # odor_name → list of signatures from each trial
        self.signatures: Dict[str, List[np.ndarray]] = defaultdict(list)
        
        # Glomerular channel tracking
        self.glom_channel_history: List[np.ndarray] = []  # per-step channel activation
    
    def set_neuron_groups(self, pn_ids: List[int], mb_ids: List[int],
                          lh_ids: List[int], id_to_idx: Dict[int, int]):
        self.pn_ids = pn_ids
        self.mb_ids = mb_ids
        self.lh_ids = lh_ids
        self.id_to_idx = id_to_idx
        
        self.pn_indices  = [id_to_idx[i] for i in pn_ids  if i in id_to_idx]
        self.mb_indices  = [id_to_idx[i] for i in mb_ids  if i in id_to_idx]
        self.lh_indices  = [id_to_idx[i] for i in lh_ids  if i in id_to_idx]
        
        print(f"OdorTracker configured:")
        print(f"  PNs: {len(self.pn_indices)}, MBs: {len(self.mb_indices)}, LH: {len(self.lh_indices)}")
    
    def begin_trial(self, odor_name: str, odor_family: str,
                    concentration: float, onset_time: float):
        """Start recording a new odor trial."""
        self.current_trial = OdorTrialRecord(
            odor_name=odor_name,
            odor_family=odor_family,
            concentration=concentration,
            onset_time=onset_time,
            offset_time=onset_time,  # updated on end_trial
        )
        self._tracking_post_odor = False
        self._post_odor_steps = 0
        self.glom_channel_history.clear()
    
    def update(self, positions: np.ndarray, velocities: np.ndarray,
               current_time: float, odor_active: bool,
               glom_channels: Optional[np.ndarray] = None):
        """
        Update tracker with current oscillator state.
        
        positions, velocities: full oscillator arrays (n_neurons,)
        odor_active: whether odor is currently being presented
        glom_channels: NUM_GLOM_CHANNELS activation vector this step
        """
        if self.current_trial is None:
            return
        
        # Convert GPU arrays to CPU for numpy operations
        from ..gpu_utils import to_cpu, array_index
        positions_cpu = to_cpu(positions)
        velocities_cpu = to_cpu(velocities)
        
        # Record glomerular channel state
        if glom_channels is not None:
            self.glom_channel_history.append(glom_channels.copy())
        
        # Compute PN stats
        if self.pn_indices:
            pn_x = positions_cpu[self.pn_indices]
            pn_v = velocities_cpu[self.pn_indices]
            pn_mean_amp = float(np.mean(np.abs(pn_x)))
            
            # Phase coherence: Kuramoto order parameter
            # Proxy: use sign of velocity × position for phase estimate
            phases = np.arctan2(pn_v, pn_x)
            r = float(np.abs(np.mean(np.exp(1j * phases))))  # 0=incoherent, 1=phase-locked
        else:
            pn_mean_amp = 0.0
            r = 0.0
        
        # Compute MB stats
        mb_mean_amp = 0.0
        if self.mb_indices:
            mb_x = positions_cpu[self.mb_indices]
            mb_mean_amp = float(np.mean(np.abs(mb_x)))
        
        # Compute LH stats
        lh_mean_amp = 0.0
        if self.lh_indices:
            lh_x = positions_cpu[self.lh_indices]
            lh_mean_amp = float(np.mean(np.abs(lh_x)))
        
        if odor_active:
            # Record during stimulation
            self.current_trial.pn_amplitudes.append(pn_mean_amp)
            self.current_trial.pn_coherence.append(r)
            self.current_trial.mb_amplitudes.append(mb_mean_amp)
            self.current_trial.lh_amplitudes.append(lh_mean_amp)
            self._tracking_post_odor = True
            self._post_odor_steps = 0
        elif self._tracking_post_odor and self._post_odor_steps < self._post_odor_max_steps:
            # Record post-odor persistence
            self.current_trial.pn_persistence.append(pn_mean_amp)
            self.current_trial.pn_coherence_persistence.append(r)
            self._post_odor_steps += 1
    
    def end_trial(self, offset_time: float):
        """Finalize trial, compute signatures, store."""
        if self.current_trial is None:
            return
        
        self.current_trial.offset_time = offset_time
        
        # Compute PN phase signature from last 1/3 of stimulation window
        if self.current_trial.pn_amplitudes:
            n = len(self.current_trial.pn_amplitudes)
            n_sig = max(1, n // 3)
            amp_sig = np.array(self.current_trial.pn_amplitudes[-n_sig:])
            coh_sig = np.array(self.current_trial.pn_coherence[-n_sig:])
            
            self.current_trial.pn_amplitude_signature = amp_sig
            self.current_trial.pn_phase_signature = coh_sig
            
            sig_vector = np.array([np.mean(amp_sig), np.mean(coh_sig),
                                    np.std(amp_sig), np.std(coh_sig)])
            self.signatures[self.current_trial.odor_name].append(sig_vector)
        
        self.trials.append(self.current_trial)
        self.current_trial = None
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na < 1e-10 or nb < 1e-10:
            return 0.0
        return float(np.dot(a, b) / (na * nb))
    
    def compute_discrimination_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Compare mean signatures between odor identities.
        Uses PN state signatures (not raw glomerular input) → measures NETWORK computation.
        """
        odor_names = list(self.signatures.keys())
        if len(odor_names) < 2:
            return {}
        
        mean_sigs = {name: np.mean(self.signatures[name], axis=0)
                     for name in odor_names}
        
        matrix = {}
        for a in odor_names:
            matrix[a] = {}
            for b in odor_names:
                matrix[a][b] = round(self._cosine_similarity(mean_sigs[a], mean_sigs[b]), 4)
        return matrix
    
    def compute_offset_persistence(self) -> Dict[str, Dict]:
        """
        For each trial: measure how long PN activity persists after offset.
        Returns per-odor statistics.
        """
        results = defaultdict(list)
        for trial in self.trials:
            if not trial.pn_persistence:
                continue
            
            baseline = np.mean(trial.pn_amplitudes) if trial.pn_amplitudes else 0.0
            persist = np.array(trial.pn_persistence)
            
            # Find when persistence drops below 50% of stimulus-period activity
            threshold = baseline * 0.5
            persistence_steps = int(np.sum(persist > threshold))
            
            results[trial.odor_name].append({
                'concentration': trial.concentration,
                'stimulus_mean_amp': float(baseline),
                'post_mean_amp': float(np.mean(persist)),
                'persistence_steps': persistence_steps,
                'persistence_ms': persistence_steps * 1.0,  # dt=1ms
            })
        
        return dict(results)
    
    def compute_trial_reproducibility(self) -> Dict[str, float]:
        """
        For each odor, compute mean cosine similarity between signatures across trials.
        High value → same odor reliably produces same PN state.
        """
        results = {}
        for odor_name, sigs in self.signatures.items():
            if len(sigs) < 2:
                results[odor_name] = None
                continue
            sims = []
            for i in range(len(sigs)):
                for j in range(i+1, len(sigs)):
                    sims.append(self._cosine_similarity(sigs[i], sigs[j]))
            results[odor_name] = round(float(np.mean(sims)), 4)
        return results
    
    def compute_concentration_invariance(self) -> Dict[str, Dict]:
        """
        For each odor with multiple concentration trials:
        Compare PN state similarity across concentrations.
        If high → identity preserved across concentration axis.
        """
        results = {}
        by_odor = defaultdict(list)
        for trial in self.trials:
            by_odor[trial.odor_name].append(trial)
        
        for odor_name, trials in by_odor.items():
            if len(trials) < 2:
                continue
            concs = [t.concentration for t in trials]
            if len(set(concs)) < 2:
                continue
            
            sigs = self.signatures.get(odor_name, [])
            if len(sigs) < 2:
                continue
            
            sims = []
            for i in range(len(sigs)):
                for j in range(i+1, len(sigs)):
                    sims.append(self._cosine_similarity(sigs[i], sigs[j]))
            
            results[odor_name] = {
                'concentrations': sorted(set(concs)),
                'mean_cross_conc_similarity': round(float(np.mean(sims)), 4),
                'interpretation': 'high=identity_preserved, low=concentration_confused_with_identity'
            }
        return results
    
    def get_summary(self) -> Dict:
        """Generate full analysis summary."""
        return {
            'num_trials': len(self.trials),
            'odors_tested': list(self.signatures.keys()),
            'discrimination_matrix': self.compute_discrimination_matrix(),
            'offset_persistence': self.compute_offset_persistence(),
            'trial_reproducibility': self.compute_trial_reproducibility(),
            'concentration_invariance': self.compute_concentration_invariance(),
        }
