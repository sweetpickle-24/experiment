"""
Wave-based olfactory system for the fly brain.

Biological accuracy notes:
- Real fly has ~50 ORN types, each projecting to one glomerulus (~50 glomeruli)
- Each ORN type responds to multiple molecular features (broad tuning)
- Odors activate overlapping subsets of ORN types - combinatorial code
- PNs in each glomerulus carry the sharpened glomerular output forward
- Concentration changes intensity but partially preserves identity
- Receptor adaptation reduces response to sustained stimuli (~200ms timescale)
- Odors cluster in families: fruit odors share receptors, danger odors share receptors
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ----------------------------
# Real-world note on glomerular channels:
# Fly AL has ~50 glomeruli. We model 20 channels (glomerular units) to keep
# computation manageable while preserving combinatorial structure.
# Each glomerular channel has a preferred molecular feature axis.
# Channels are organized as: [esters/fruit, alcohols/yeast, ketones/sweet,
# amines/social, terpenoids/plant, sulfurous/danger, CO2/stress, misc...]
# ----------------------------
NUM_GLOM_CHANNELS = 20

# Glomerular channel identity labels (conceptual axes only - not mechanistically enforced)
GLOM_LABELS = [
    "ester_fruit",   # 0  - fruit esters (ethyl acetate, isoamyl acetate)
    "ester_floral",  # 1  - floral esters
    "alcohol_short", # 2  - short-chain alcohols (ethanol, propanol)
    "alcohol_long",  # 3  - long-chain alcohols (hexanol, octanol)
    "ketone",        # 4  - ketones (acetone, 2-butanone)
    "sweet_aldehyde",# 5  - sweet-smelling aldehydes
    "yeast_product", # 6  - yeast fermentation products
    "carbon_dioxide",# 7  - CO2 / hypoxia stress cue
    "acid_organic",  # 8  - organic acids (acetic, lactic)
    "amine_small",   # 9  - small amines (putrescine, cadaverine - decay)
    "amine_pheromone",# 10 - pheromone amines (cVA male aggregation pheromone)
    "terpene_plant", # 11 - plant terpenes (limonene, linalool)
    "sulfur_mold",   # 12 - sulfurous/mold compounds (geosmin, DMTS)
    "mold_danger",   # 13 - mold danger / rotting signal
    "social_female", # 14 - female pheromone proxy (7,11-HD)
    "social_male",   # 15 - male aggregation signal
    "humid_organic", # 16 - humid organic background
    "plant_green",   # 17 - green leaf volatiles
    "bitter_rotting",# 18 - bitter / rotting contamination
    "clean_air",     # 19 - near-zero baseline
]


@dataclass
class Odor:
    """
    Represents an odor as a 20-channel glomerular activation pattern.
    
    Real biology: Each odor is a sparse-to-dense vector over ORN types.
    Similar odors (e.g. ripe vs unripe fruit) share most active channels
    but differ in relative weights. Concentration scales all channels equally.
    """
    name: str
    glom_pattern: np.ndarray      # 20-dim vector: activation per glomerular channel (0-1, normalized)
    family: str                    # "fruit", "danger", "social", "background", "control"
    description: str               # Human-readable description


def _norm(v: np.ndarray) -> np.ndarray:
    """Normalize to unit L2 norm so identity is concentration-invariant."""
    n = np.linalg.norm(v)
    return v / n if n > 1e-10 else v


def create_odor_library() -> Dict[str, Odor]:
    """
    Create biologically shaped odor library with 10 odors in 4 families.
    
    Real-world accuracy:
    - Each odor activates a different SUBSET of glomerular channels
    - Odors within a family share active channels (partial overlap)
    - Odors across families have low but non-zero overlap
    - NOT orthogonal: fruit_ferment and fruit_ripe share esters/alcohols
    
    Channel key: see GLOM_LABELS above
    """
    # -------- FRUIT FAMILY --------
    # Fermenting fruit: strong esters, alcohols, some yeast, mild CO2
    fruit_ferment = _norm(np.array([
        0.85, 0.20, 0.70, 0.10, 0.15, 0.05,  # 0-5: ester_fruit, ester_floral, alcohol_short...
        0.65, 0.25, 0.40, 0.00, 0.00, 0.00,  # 6-11: yeast_product, CO2, acid...
        0.00, 0.05, 0.00, 0.00, 0.15, 0.10,  # 12-17: sulfur, mold, social, plant
        0.00, 0.05                            # 18-19: bitter, clean
    ]))
    
    # Ripe fruit: more esters, less yeast than fermenting
    fruit_ripe = _norm(np.array([
        0.90, 0.45, 0.35, 0.15, 0.20, 0.30,
        0.25, 0.05, 0.20, 0.00, 0.00, 0.10,
        0.00, 0.00, 0.00, 0.00, 0.10, 0.20,
        0.00, 0.05
    ]))
    
    # Yeast: dominated by yeast products + alcohols
    yeast = _norm(np.array([
        0.30, 0.05, 0.80, 0.40, 0.35, 0.10,
        0.90, 0.20, 0.55, 0.00, 0.00, 0.00,
        0.00, 0.00, 0.00, 0.00, 0.10, 0.05,
        0.00, 0.05
    ]))
    
    # -------- DANGER FAMILY --------
    # Geosmin / mold danger: sulfurous, mold, organic acids, rotting
    danger_mold = _norm(np.array([
        0.00, 0.00, 0.05, 0.00, 0.00, 0.00,
        0.00, 0.20, 0.60, 0.70, 0.00, 0.05,
        0.90, 0.85, 0.00, 0.00, 0.05, 0.00,
        0.75, 0.00
    ]))
    
    # CO2 / stress cue: CO2 dominant, mild organic acids
    danger_co2 = _norm(np.array([
        0.00, 0.00, 0.00, 0.00, 0.00, 0.00,
        0.00, 0.95, 0.30, 0.40, 0.00, 0.00,
        0.15, 0.30, 0.00, 0.00, 0.00, 0.00,
        0.20, 0.00
    ]))
    
    # -------- SOCIAL FAMILY --------
    # Female pheromone proxy (7,11-HD in real fly: long-chain diene)
    social_female = _norm(np.array([
        0.00, 0.05, 0.00, 0.30, 0.10, 0.00,
        0.00, 0.00, 0.00, 0.20, 0.10, 0.10,
        0.00, 0.00, 0.90, 0.05, 0.05, 0.00,
        0.00, 0.05
    ]))
    
    # Male aggregation pheromone proxy (cVA: vaccenyl acetate - well characterized)
    social_male = _norm(np.array([
        0.25, 0.10, 0.00, 0.20, 0.00, 0.00,
        0.00, 0.00, 0.00, 0.15, 0.85, 0.05,
        0.00, 0.00, 0.10, 0.80, 0.05, 0.00,
        0.00, 0.05
    ]))
    
    # -------- BACKGROUND FAMILY --------
    # Plant leaf volatiles: terpenes, green leaf, mild esters
    background_plant = _norm(np.array([
        0.10, 0.30, 0.05, 0.25, 0.05, 0.15,
        0.00, 0.00, 0.05, 0.00, 0.00, 0.80,
        0.00, 0.00, 0.00, 0.00, 0.40, 0.75,
        0.00, 0.15
    ]))
    
    # Clean air control: near-zero activation across all channels
    clean_air = _norm(np.array([
        0.02, 0.02, 0.02, 0.02, 0.02, 0.02,
        0.02, 0.05, 0.02, 0.00, 0.00, 0.02,
        0.00, 0.00, 0.00, 0.00, 0.05, 0.05,
        0.00, 0.90
    ]))
    
    # -------- MIXTURE (bonus) --------
    # Fruit + danger (rotting fruit): blend of fruit_ferment and danger_mold
    a, b = 0.6, 0.4
    rotting_fruit = _norm(a * fruit_ferment + b * danger_mold)
    
    return {
        "fruit_ferment":    Odor("fruit_ferment",    fruit_ferment,   "fruit",      "Fermenting fruit (ethyl acetate, ethanol, CO2)"),
        "fruit_ripe":       Odor("fruit_ripe",        fruit_ripe,      "fruit",      "Ripe fresh fruit (esters, aldehydes)"),
        "yeast":            Odor("yeast",             yeast,           "fruit",      "Yeast fermentation (alcohols, acetates)"),
        "danger_mold":      Odor("danger_mold",       danger_mold,     "danger",     "Geosmin/mold danger signal"),
        "danger_co2":       Odor("danger_co2",        danger_co2,      "danger",     "CO2/stress cue"),
        "social_female":    Odor("social_female",     social_female,   "social",     "Female pheromone proxy (7,11-HD)"),
        "social_male":      Odor("social_male",       social_male,     "social",     "Male aggregation pheromone (cVA)"),
        "background_plant": Odor("background_plant",  background_plant,"background", "Plant/leaf volatiles"),
        "clean_air":        Odor("clean_air",         clean_air,       "background", "Clean air control"),
        "rotting_fruit":    Odor("rotting_fruit",     rotting_fruit,   "mixture",    "Rotting fruit (fruit+danger mixture)"),
    }


def make_concentration_variants(base_odor: Odor, concentrations: List[float]) -> List[Tuple[float, Odor]]:
    """
    Create concentration variants of one odor.
    
    Real biology: Concentration scales firing rate but preserves IDENTITY.
    At very low concentration, noisy channels may dominate (identity confusion).
    At very high concentration, nearly all channels saturate (compression).
    
    Returns list of (concentration, Odor) tuples.
    """
    variants = []
    for conc in concentrations:
        # Pattern stays the same (identity-invariant), only concentration changes
        variants.append((conc, base_odor))
    return variants


class OdorReceptorArray:
    """
    Glomerular channel input array.
    
    Real biology:
    - Each channel represents one glomerulus (ORN type converging on AL)
    - Forcing frequency is set by the CHANNEL's molecular tuning axis
    - Channels tuned to volatile/light molecules oscillate faster (gamma-like)
    - Channels tuned to heavy/pheromone molecules oscillate slower (theta-like)
    - This emerges from biology, not from an odor label
    
    The forcing is sinusoidal because the ORN → glomerulus input creates
    rhythmic waves at the sniff/breathing frequency (real fly sniffs ~10Hz).
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.num_channels = NUM_GLOM_CHANNELS
        
        # Channel frequencies tuned by molecular axis:
        # Volatile light molecules (fruit esters): higher freq (beta/gamma, 15-40 Hz)
        # Heavy/pheromone molecules: lower freq (theta, 4-10 Hz)
        # This is approximating real sniff-cycle modulation
        self.channel_frequencies = np.array([
            20.0, 18.0, 22.0, 8.0,  12.0, 16.0,  # 0-5: fruit/ester axes → beta
            14.0, 6.0,  10.0, 5.0,   9.0, 12.0,  # 6-11: yeast/CO2/acid/amine → mixed
            7.0,  6.0,  5.0,  5.0,  11.0, 13.0,  # 12-17: danger/social/plant → theta/alpha
            7.0,  4.0                              # 18-19: bitter/clean → theta
        ])  # Hz
        
        # Random phase offsets (simulate different ORN populations arriving at different phases)
        np.random.seed(99)
        self.channel_phases = np.random.uniform(0, 2*np.pi, self.num_channels)
        
        # Current activation (set each step from plume)
        self.activation = np.zeros(self.num_channels)
        
        # Adaptation state per channel
        self.adaptation = np.ones(self.num_channels)  # 1.0 = fully responsive
        self.tau_adapt = 200.0  # ms - receptor adaptation time constant (real: ~200ms)
        self.tau_recover = 500.0  # ms - recovery after odor offset
    
    def set_activation(self, glom_pattern: np.ndarray, concentration: float = 1.0):
        """Set channel activation = odor pattern × concentration."""
        self.activation = np.clip(glom_pattern * concentration, 0.0, 1.0)
    
    def update_adaptation(self, dt: float, odor_on: bool):
        """
        Update adaptation state.
        
        Real biology: ORNs adapt to sustained stimulation (Weber-Fechner law).
        Strong initial response decays over ~200ms of continuous exposure.
        Recovers over ~500ms after odor offset.
        """
        if odor_on:
            # Adaptation decays toward minimum during stimulation
            decay = np.exp(-dt / self.tau_adapt)
            self.adaptation = self.adaptation * decay + (1 - decay) * 0.2  # floor at 0.2
        else:
            # Recovery after offset
            recovery = np.exp(-dt / self.tau_recover)
            self.adaptation = self.adaptation * recovery + (1 - recovery) * 1.0
    
    def compute_forces(self, t: float, amplitude_scale: float) -> np.ndarray:
        """
        Compute sinusoidal forces for each glomerular channel at time t.
        
        Force = activation × adaptation × amplitude_scale × sin(ω_channel × t + φ)
        
        The adaptation term is key: real ORNs fire less as odor persists.

        UNITS DEFECT, unresolved. channel_frequencies is in Hz and t is passed
        in milliseconds, but omega below is formed as 2*pi*f and multiplied by t
        with no ms-to-s conversion, so the carrier advances f whole cycles per
        millisecond instead of per second, i.e. 1000x too fast. Because the
        frequencies are whole numbers of Hz, sampling on a whole-millisecond
        grid lands on an exact multiple of 2*pi every time and the carrier
        returns the same value at every sample: a 7 Hz channel advances exactly
        70 cycles per 10 ms step. Callers stepping in whole milliseconds
        therefore see a constant force, not an oscillation.

        Not corrected here because dividing t by 1000 changes the forcing
        waveform for every consumer of this class, which is a behavioural
        change rather than a reporting one.
        """
        omega = 2 * np.pi * self.channel_frequencies  # rad/ms
        # Carrier wave at channel-intrinsic frequency
        carrier = np.sin(omega * t + self.channel_phases)
        # Force = adapted activation × carrier
        forces = self.activation * self.adaptation * amplitude_scale * carrier
        return forces


class OdorPlume:
    """
    Time-varying odor concentration with turbulent plume dynamics.
    
    Real biology:
    - Odor plumes in nature are highly intermittent
    - Fly encounters odor in discrete whiffs (50-300ms duration)
    - Between whiffs: near-zero concentration
    - Within whiff: fast rise (~5ms), slower decay (~20ms)
    - Turbulence adds noise independent of whiff structure
    """
    
    def __init__(self, odor: Odor, duration_ms: float, concentration: float, config: dict):
        self.odor = odor
        self.duration = duration_ms
        self.concentration = concentration
        
        plume_cfg = config['olfactory']['plume']
        self.whiff_interval_mean = plume_cfg['whiff_interval_mean']
        self.whiff_duration_mean = plume_cfg['whiff_duration_mean']
        self.rise_time    = plume_cfg['rise_time']
        self.decay_time   = plume_cfg['decay_time']
        self.turb_sigma   = plume_cfg['turbulence_sigma']
        self.turb_tau     = plume_cfg['turbulence_tau']
        
        self.dt = config['oscillator']['dt']
        self.num_steps = int(duration_ms / self.dt)
        
        # Pre-generate full plume trace: [num_steps, num_channels]
        self.concentration_trace = self._generate_plume()
    
    def _generate_plume(self) -> np.ndarray:
        """
        Generate realistic plume: whiff train × odor pattern + noise.
        
        The SCALAR whiff envelope multiplies the VECTOR odor pattern.
        So channel ratios are preserved across the whiff - identity is stable.
        Turbulence adds small per-channel noise.
        """
        n_ch = NUM_GLOM_CHANNELS
        trace = np.zeros((self.num_steps, n_ch))
        
        # --- Whiff train ---
        whiff_envelope = np.zeros(self.num_steps)
        t = 0.0
        while t < self.duration:
            t += np.random.exponential(self.whiff_interval_mean)
            if t >= self.duration:
                break
            dur = np.random.exponential(self.whiff_duration_mean)
            n_whiff = int(dur / self.dt)
            start_idx = int(t / self.dt)
            for i in range(n_whiff):
                idx = start_idx + i
                if idx >= self.num_steps:
                    break
                # Exponential rise / decay envelope
                if i < n_whiff // 3:
                    factor = 1.0 - np.exp(-i * self.dt / self.rise_time)
                else:
                    decay_t = (i - n_whiff // 3) * self.dt
                    factor = np.exp(-decay_t / self.decay_time)
                whiff_envelope[idx] += factor * self.concentration
        
        # Clip envelope to concentration
        whiff_envelope = np.clip(whiff_envelope, 0.0, self.concentration)
        
        # Multiply envelope by odor pattern (preserves identity across whiffs)
        for ch in range(n_ch):
            trace[:, ch] = whiff_envelope * self.odor.glom_pattern[ch]
        
        # --- Per-channel Ornstein-Uhlenbeck turbulence noise ---
        # Same noise trajectory per channel (turbulence is spatial, not channel-specific)
        ou = self._ornstein_uhlenbeck(self.num_steps)
        noise_scale = self.turb_sigma * self.concentration
        for ch in range(n_ch):
            trace[:, ch] += ou * noise_scale * self.odor.glom_pattern[ch]
        
        return np.clip(trace, 0.0, 1.0)
    
    def _ornstein_uhlenbeck(self, n: int) -> np.ndarray:
        noise = np.zeros(n)
        x = 0.0
        for i in range(n):
            x += -x / self.turb_tau * self.dt + np.random.normal(0, np.sqrt(2 * self.dt))
            noise[i] = x
        return noise
    
    def get_concentration(self, step_idx: int) -> np.ndarray:
        if 0 <= step_idx < self.num_steps:
            return self.concentration_trace[step_idx]
        return np.zeros(NUM_GLOM_CHANNELS)


class GlomerularMapper:
    """
    Maps glomerular channels to PN clusters using real connectome positions.
    
    Real biology:
    - Each glomerulus = one functional unit in the AL
    - PNs within a glomerulus are all driven by the same ORN type
    - Neighboring glomeruli can influence each other (lateral inhibition - not modeled here)
    - Mapping is STRUCTURED: channel 0 (fruit esters) → spatially proximal PNs
    
    Implementation:
    - Spatially cluster the 5,670 PNs into NUM_GLOM_CHANNELS clusters
    - Each cluster = one glomerular output channel
    - One-to-one clean mapping (no random scatter)
    """
    
    def __init__(self, pn_ids: List[int], connectome, num_channels: int = NUM_GLOM_CHANNELS):
        self.pn_ids = np.array(pn_ids)
        self.connectome = connectome
        self.num_channels = num_channels
        
        self.glomerular_clusters = self._cluster_pns()
        print(f"  {len(self.glomerular_clusters)} glomerular PN clusters built from {len(pn_ids)} PNs")
    
    def _cluster_pns(self) -> List[List[int]]:
        """Cluster PNs spatially into glomerular channels."""
        positions, valid_ids = [], []
        for nid in self.pn_ids:
            if nid in self.connectome.neurons:
                positions.append(self.connectome.neurons[nid].position)
                valid_ids.append(nid)
        
        if not positions:
            return []
        
        positions = np.array(positions, dtype=np.float64)
        valid_ids = np.array(valid_ids)
        n_clusters = min(self.num_channels, len(valid_ids))
        
        # K-means with more iterations for stable clusters
        np.random.seed(42)
        idx = np.random.choice(len(positions), size=n_clusters, replace=False)
        centers = positions[idx].copy()
        
        for _ in range(20):
            # Vectorized distance computation
            diff = positions[:, np.newaxis, :] - centers[np.newaxis, :, :]  # (N, K, 3)
            dists = np.sum(diff**2, axis=-1)  # (N, K)
            labels = np.argmin(dists, axis=1)
            new_centers = np.array([
                positions[labels == k].mean(axis=0) if np.any(labels == k) else centers[k]
                for k in range(n_clusters)
            ])
            if np.allclose(centers, new_centers, atol=1e-6):
                break
            centers = new_centers
        
        return [valid_ids[labels == k].tolist() for k in range(n_clusters) if np.any(labels == k)]
    
    def get_pn_forces(self, channel_forces: np.ndarray) -> Dict[int, float]:
        """
        Map channel forces to individual PN forces.
        Each PN gets the force of its glomerular channel.
        """
        pn_forces = {}
        for ch_idx, force in enumerate(channel_forces):
            if ch_idx < len(self.glomerular_clusters):
                for pn_id in self.glomerular_clusters[ch_idx]:
                    pn_forces[pn_id] = force
        return pn_forces


class OlfactoryStimulus:
    """A single odor presentation with timing and concentration."""
    
    def __init__(self, odor: Odor, duration_ms: float, onset_time: float,
                 concentration: float, config: dict):
        self.odor = odor
        self.duration = duration_ms
        self.onset = onset_time
        self.offset = onset_time + duration_ms
        self.concentration = concentration
        self.plume = OdorPlume(odor, duration_ms, concentration, config)
        self._dt = config['oscillator']['dt']
    
    def is_active(self, t: float) -> bool:
        return self.onset <= t < self.offset
    
    def get_concentration_vector(self, t: float) -> np.ndarray:
        if not self.is_active(t):
            return np.zeros(NUM_GLOM_CHANNELS)
        step_idx = int((t - self.onset) / self._dt)
        return self.plume.get_concentration(step_idx)


class OlfactorySystem:
    """
    Main olfactory coordinator.
    Manages glomerular channels, adaptation, PN forcing.
    
    Biological pipeline:
    Odor plume → glomerular activation(t) → adapted channel forcing → PN waves
    """
    
    def __init__(self, pn_ids: List[int], connectome, config: dict):
        self.pn_ids = pn_ids
        self.connectome = connectome
        self.config = config
        
        olf = config['olfactory']
        self.amplitude_scale = olf['forcing']['amplitude_scale']
        
        self.receptors = OdorReceptorArray(config)
        self.glomerular_mapper = GlomerularMapper(pn_ids, connectome)
        
        self.current_stimulus: Optional[OlfactoryStimulus] = None
        self.current_odor: Optional[Odor] = None
        
        # Pre-built odor library
        self.odor_library = create_odor_library()
        
        print(f"Olfactory system initialized:")
        print(f"  {NUM_GLOM_CHANNELS} glomerular channels")
        print(f"  {len(self.glomerular_mapper.glomerular_clusters)} PN clusters")
        print(f"  {len(pn_ids)} projection neurons")
        print(f"  {len(self.odor_library)} odors in library")
    
    def set_odor(self, odor: Odor, duration_ms: float, onset_time: float,
                 concentration: float = 1.0):
        """Present an odor at a given concentration."""
        self.current_stimulus = OlfactoryStimulus(
            odor, duration_ms, onset_time, concentration, self.config
        )
        self.current_odor = odor
    
    def clear_odor(self):
        self.current_stimulus = None
        self.current_odor = None
    
    def compute_pn_forces(self, current_time: float, dt: float,
                          sensory_gain: float = 1.0) -> Dict[int, float]:
        """
        Compute PN forces at current_time.
        Includes adaptation dynamics.
        """
        odor_on = (self.current_stimulus is not None and
                   self.current_stimulus.is_active(current_time))
        
        # Update adaptation regardless (recovery when off)
        self.receptors.update_adaptation(dt, odor_on)
        
        if not odor_on:
            return {}
        
        # Get plume concentration vector for this timestep
        conc_vector = self.current_stimulus.get_concentration_vector(current_time)
        
        # Set receptor activation (concentration already encoded in conc_vector)
        self.receptors.set_activation(conc_vector)
        
        # Compute sinusoidal forces with adaptation
        channel_forces = self.receptors.compute_forces(current_time, self.amplitude_scale)
        
        # Map to PNs
        pn_forces = self.glomerular_mapper.get_pn_forces(channel_forces)
        
        # Apply sensory gain
        return {nid: f * sensory_gain for nid, f in pn_forces.items()}
