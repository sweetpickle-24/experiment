"""
Map real fly sensory and motor neurons from the connectome.
Identifies input/output neurons for behavioral simulation.
"""

from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class SensoryMotorMap:
    """Maps sensory input and motor output neurons."""
    
    # Visual system neurons
    visual_motion: Dict[str, List[int]]  # direction -> neuron IDs
    
    # Olfactory system
    olfactory: List[int]  # Projection neurons (PNs)
    
    # Mechanosensory
    mechanosensory: List[int]  # JO neurons, etc.
    
    # Motor output
    descending_neurons: List[int]  # DNs controlling behavior
    flight_control: List[int]  # Wing motor neurons
    
    # Other sensory
    gustatory: List[int]
    proprioceptive: List[int]


class SensoryMotorMapper:
    """
    Identify sensory and motor neurons from cell types.
    Uses known cell type annotations from fly connectome literature.
    """
    
    def __init__(self, connectome):
        self.connectome = connectome
        self.sensory_motor_map = None
    
    def build_map(self) -> SensoryMotorMap:
        """Build the complete sensory/motor map."""
        print("Mapping sensory and motor neurons...")
        
        visual_motion = self._find_visual_motion_neurons()
        olfactory = self._find_olfactory_neurons()
        mechanosensory = self._find_mechanosensory_neurons()
        descending = self._find_descending_neurons()
        flight = self._find_flight_neurons()
        gustatory = self._find_gustatory_neurons()
        proprioceptive = self._find_proprioceptive_neurons()
        
        self.sensory_motor_map = SensoryMotorMap(
            visual_motion=visual_motion,
            olfactory=olfactory,
            mechanosensory=mechanosensory,
            descending_neurons=descending,
            flight_control=flight,
            gustatory=gustatory,
            proprioceptive=proprioceptive
        )
        
        self._print_summary()
        return self.sensory_motor_map
    
    def _find_visual_motion_neurons(self) -> Dict[str, List[int]]:
        """
        Find T4/T5 direction-selective neurons in optic lobes.
        T4 (ON motion), T5 (OFF motion), subtypes a/b/c/d for 4 directions.
        """
        directions = {
            'front': [],
            'back': [],
            'upward': [],
            'downward': []
        }
        
        # T4 and T5 neurons with directional subtypes
        for nid, neuron in self.connectome.neurons.items():
            for cell_type in neuron.cell_types:
                if 'T4a' in cell_type or 'T5a' in cell_type:
                    directions['front'].append(nid)
                elif 'T4b' in cell_type or 'T5b' in cell_type:
                    directions['back'].append(nid)
                elif 'T4c' in cell_type or 'T5c' in cell_type:
                    directions['upward'].append(nid)
                elif 'T4d' in cell_type or 'T5d' in cell_type:
                    directions['downward'].append(nid)
        
        return directions
    
    def _find_olfactory_neurons(self) -> List[int]:
        """
        Find projection neurons (PNs) in antennal lobe.
        These receive input from olfactory receptor neurons.
        """
        olfactory = []
        
        # Look for neurons in antennal lobe regions
        for nid, neuron in self.connectome.neurons.items():
            # Antennal lobe groups
            if 'AL' in neuron.group or 'AMMC' in neuron.group:
                olfactory.append(nid)
            
            # Also check for PN cell types
            for cell_type in neuron.cell_types:
                if 'PN' in cell_type or 'adPN' in cell_type or 'lPN' in cell_type:
                    if nid not in olfactory:
                        olfactory.append(nid)
        
        return olfactory
    
    def _find_mechanosensory_neurons(self) -> List[int]:
        """
        Find mechanosensory neurons (JO neurons, touch receptors).
        """
        mechanosensory = []
        
        for nid, neuron in self.connectome.neurons.items():
            for cell_type in neuron.cell_types:
                # Johnston's Organ (antenna) neurons
                if 'JO' in cell_type or 'AMMC' in cell_type:
                    mechanosensory.append(nid)
                    break
        
        return mechanosensory
    
    def _find_descending_neurons(self) -> List[int]:
        """
        Find descending neurons (DNs) - motor command neurons.
        These connect brain to ventral nerve cord.
        """
        descending = []
        
        for nid, neuron in self.connectome.neurons.items():
            for cell_type in neuron.cell_types:
                # DN prefix indicates descending neuron
                if cell_type.startswith('DN'):
                    descending.append(nid)
                    break
        
        return descending
    
    def _find_flight_neurons(self) -> List[int]:
        """
        Find flight-related neurons (subset of DNs).
        """
        flight = []
        
        for nid, neuron in self.connectome.neurons.items():
            for cell_type in neuron.cell_types:
                # Known flight-related DNs
                if any(x in cell_type for x in ['DNp', 'DNa', 'DNb']):
                    flight.append(nid)
                    break
        
        return flight
    
    def _find_gustatory_neurons(self) -> List[int]:
        """Find taste-related neurons."""
        gustatory = []
        
        for nid, neuron in self.connectome.neurons.items():
            # SEZ (subesophageal zone) handles taste
            if 'SEZ' in neuron.group or 'GNG' in neuron.group:
                gustatory.append(nid)
        
        return gustatory
    
    def _find_proprioceptive_neurons(self) -> List[int]:
        """Find proprioceptive (body position) neurons."""
        proprioceptive = []
        
        for nid, neuron in self.connectome.neurons.items():
            for cell_type in neuron.cell_types:
                # Proprioceptive feedback neurons
                if 'PS' in cell_type or 'AN' in cell_type:
                    proprioceptive.append(nid)
                    break
        
        return proprioceptive
    
    def _print_summary(self):
        """Print summary of sensory/motor neurons found."""
        sm = self.sensory_motor_map
        
        print("\nSensory/Motor Neuron Map:")
        print(f"Visual motion neurons:")
        for direction, neurons in sm.visual_motion.items():
            print(f"  {direction}: {len(neurons)}")
        print(f"Olfactory (PNs): {len(sm.olfactory)}")
        print(f"Mechanosensory: {len(sm.mechanosensory)}")
        print(f"Descending neurons (DNs): {len(sm.descending_neurons)}")
        print(f"Flight control: {len(sm.flight_control)}")
        print(f"Gustatory: {len(sm.gustatory)}")
        print(f"Proprioceptive: {len(sm.proprioceptive)}")
        
        total = (sum(len(v) for v in sm.visual_motion.values()) + 
                 len(sm.olfactory) + len(sm.mechanosensory) +
                 len(sm.descending_neurons) + len(sm.flight_control) +
                 len(sm.gustatory) + len(sm.proprioceptive))
        print(f"\nTotal I/O neurons: {total}")
    
    def get_sensory_neurons(self) -> Set[int]:
        """Get all sensory neuron IDs."""
        sensory = set()
        for neurons in self.sensory_motor_map.visual_motion.values():
            sensory.update(neurons)
        sensory.update(self.sensory_motor_map.olfactory)
        sensory.update(self.sensory_motor_map.mechanosensory)
        sensory.update(self.sensory_motor_map.gustatory)
        sensory.update(self.sensory_motor_map.proprioceptive)
        return sensory
    
    def get_motor_neurons(self) -> Set[int]:
        """Get all motor neuron IDs."""
        motor = set()
        motor.update(self.sensory_motor_map.descending_neurons)
        motor.update(self.sensory_motor_map.flight_control)
        return motor
