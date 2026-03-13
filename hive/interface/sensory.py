"""
Sensory input interface for the fly brain.
Maps external stimuli to sensory neuron activation.
"""

import numpy as np
from typing import Dict, List, Tuple


class SensoryInterface:
    """
    Translates external stimuli into oscillator forcing.
    """
    
    def __init__(self, sensory_motor_map, spatial_index, config: dict):
        self.sm_map = sensory_motor_map
        self.spatial_index = spatial_index
        self.config = config
        
        # Current input state
        self.visual_motion = {'front': 0.0, 'back': 0.0, 'upward': 0.0, 'downward': 0.0}
        self.compound_eye_forces = {}  # NEW: Detailed per-neuron forces from compound eye
        self.odor_concentration = np.zeros(50)  # 50 olfactory channels (legacy)
        self.touch_intensity = 0.0
        
        # Wave-based olfactory system
        self.olfactory_system = None  # Set externally after initialization
        self.current_time = 0.0  # Track current simulation time
    
    def set_visual_motion(self, direction: str, intensity: float):
        """Set visual motion stimulus (simple mode)."""
        if direction in self.visual_motion:
            self.visual_motion[direction] = np.clip(intensity, 0.0, 1.0)
    
    def apply_compound_eye_input(
        self,
        neuron_forces: Dict[str, List[Tuple[int, float]]]
    ):
        """
        Apply spatially-mapped compound eye input to visual motion neurons.
        
        Args:
            neuron_forces: Dict mapping direction to list of (neuron_id, force) tuples
                          from CompoundEyeSimulator.get_visual_neuron_stimulation()
        """
        # Clear previous compound eye forces
        self.compound_eye_forces = {}
        
        # Accumulate forces from all directions
        for direction in ['front', 'back', 'upward', 'downward']:
            if direction in neuron_forces:
                for neuron_id, force in neuron_forces[direction]:
                    if neuron_id in self.compound_eye_forces:
                        # Multiple ommatidia may target same neuron
                        self.compound_eye_forces[neuron_id] += force
                    else:
                        self.compound_eye_forces[neuron_id] = force
    
    def set_odor(self, channel: int, concentration: float):
        """Set odor stimulus for a specific channel."""
        if 0 <= channel < 50:
            self.odor_concentration[channel] = np.clip(concentration, 0.0, 1.0)
    
    def set_touch(self, intensity: float):
        """Set touch stimulus intensity."""
        self.touch_intensity = np.clip(intensity, 0.0, 1.0)
    
    def compute_sensory_forces(self, sensory_gain: float = 1.0) -> Dict[int, float]:
        """
        Compute external forcing for all sensory neurons.
        Returns dict: neuron_id -> force magnitude
        """
        forces = {}
        
        # NEW: Compound eye forces (spatially-mapped, detailed)
        for neuron_id, force in self.compound_eye_forces.items():
            forces[neuron_id] = force * sensory_gain
        
        # Fallback: Simple visual motion (if compound eye not used)
        if len(self.compound_eye_forces) == 0:
            for direction, intensity in self.visual_motion.items():
                if intensity > 0:
                    neuron_ids = self.sm_map.visual_motion.get(direction, [])
                    for nid in neuron_ids:
                        forces[nid] = intensity * sensory_gain * 10.0
        
        # Wave-based olfactory forcing
        if self.olfactory_system is not None:
            dt = self.config.get('oscillator', {}).get('dt', 1.0)
            odor_forces = self.olfactory_system.compute_pn_forces(
                current_time=self.current_time,
                dt=dt,
                sensory_gain=sensory_gain
            )
            forces.update(odor_forces)
        else:
            # Legacy olfactory (simple)
            for channel, concentration in enumerate(self.odor_concentration):
                if concentration > 0 and channel < len(self.sm_map.olfactory):
                    pn_subset = self.sm_map.olfactory[channel::50]
                    for nid in pn_subset[:5]:
                        forces[nid] = concentration * sensory_gain * 8.0
        
        # Mechanosensory
        if self.touch_intensity > 0:
            for nid in self.sm_map.mechanosensory[:10]:  # Sample
                forces[nid] = self.touch_intensity * sensory_gain * 6.0
        
        return forces
    
    def apply_to_oscillator(self, oscillator_engine, sensory_gain: float = 1.0, current_time: float = 0.0):
        """Apply sensory forces directly to oscillator."""
        # Update current time for olfactory system
        self.current_time = current_time
        
        forces_dict = self.compute_sensory_forces(sensory_gain)
        
        # Convert to array
        force_array = np.zeros(oscillator_engine.num_oscillators)
        
        for neuron_id, force in forces_dict.items():
            try:
                idx = self.spatial_index.neuron_ids.index(neuron_id)
                force_array[idx] = force
            except ValueError:
                continue
        
        oscillator_engine.add_external_force(force_array)
    
    def reset(self):
        """Reset all sensory inputs to zero."""
        self.visual_motion = {k: 0.0 for k in self.visual_motion}
        self.compound_eye_forces = {}
        self.odor_concentration.fill(0.0)
        self.touch_intensity = 0.0


class MotorInterface:
    """
    Reads motor neuron activity to generate behavior.
    """
    
    def __init__(self, sensory_motor_map, spatial_index):
        self.sm_map = sensory_motor_map
        self.spatial_index = spatial_index
    
    def read_motor_output(self, oscillator_engine) -> dict:
        """
        Decode motor commands from descending neurons.
        Returns motor output state.
        """
        # Get DN activity
        dn_activity = []
        for nid in self.sm_map.descending_neurons:
            try:
                idx = self.spatial_index.neuron_ids.index(nid)
                amplitude = oscillator_engine.amplitude[idx]
                phase = oscillator_engine.phase[idx]
                dn_activity.append((amplitude, phase))
            except ValueError:
                continue
        
        if len(dn_activity) == 0:
            return {'wing_left': 0.0, 'wing_right': 0.0, 'movement_direction': 0.0}
        
        # Simple decoding: average amplitude and phase
        amplitudes = [a for a, p in dn_activity]
        phases = [p for a, p in dn_activity]
        
        mean_amplitude = np.mean(amplitudes)
        mean_phase = np.angle(np.mean(np.exp(1j * np.array(phases))))
        
        # Map to motor outputs
        wing_left = mean_amplitude * np.cos(mean_phase)
        wing_right = mean_amplitude * np.sin(mean_phase)
        
        return {
            'wing_left': np.clip(wing_left, -1.0, 1.0),
            'wing_right': np.clip(wing_right, -1.0, 1.0),
            'movement_direction': mean_phase
        }
