"""
Visual Pathway Connectome Extraction

Extract visual processing neurons from full FlyWire connectome:
- Photoreceptors (R1-R8): ~800 neurons
- Lamina neurons (L1-L5, C2, C3, T1): ~5,000 neurons
- Medulla neurons (Mi, Tm, Dm, Pm, etc.): ~40,000 neurons
- Lobula neurons (T4, T5, LC, LPLC): ~5,000 neurons
- Lobula Plate neurons (LPi, HS, VS): ~3,000 neurons

Total: ~53,000 neurons vs. ~10,900 olfactory
"""

import numpy as np
from typing import Dict, List, Set, Tuple
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from hive.substrate.connectome import Connectome, Neuron, Synapse


# Visual neuron type keywords (based on FlyWire cell type annotations)
VISUAL_NEURON_TYPES = {
    # Photoreceptors
    'PHOTORECEPTOR': ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 
                      'photoreceptor', 'retina'],
    
    # Lamina - first synaptic layer
    'LAMINA': ['L1', 'L2', 'L3', 'L4', 'L5',  # Lamina monopolar cells
               'C2', 'C3',                     # Centrifugal cells
               'T1',                           # Tangential cells
               'Lawf', 'Lai',                  # Amacrine cells
               'lamina'],
    
    # Medulla - main processing layer
    'MEDULLA': ['Mi1', 'Mi2', 'Mi3', 'Mi4', 'Mi9', 'Mi10', 'Mi11', 'Mi14', 'Mi15',
                'Tm1', 'Tm2', 'Tm3', 'Tm4', 'Tm5', 'Tm9', 'Tm16', 'Tm20', 'Tm28',
                'TmY', 'Tm-Y',
                'Dm1', 'Dm2', 'Dm3', 'Dm4', 'Dm5', 'Dm6', 'Dm7', 'Dm8', 'Dm9',
                'Dm10', 'Dm11', 'Dm12',
                'Pm1', 'Pm2', 'Pm3',
                'DM', 'DM1', 'DM2', 'DM3', 'DM4',
                'LC', 'LC4', 'LC6', 'LC9', 'LC10', 'LC11', 'LC12', 'LC13', 'LC14',
                'LCVI', 'LC16', 'LC17', 'LC18', 'LC20', 'LC21', 'LC22', 'LC24', 'LC25',
                'Sm', 'serpentine',
                'medulla'],
    
    # Lobula - motion detection
    'LOBULA': ['T4', 'T5',                   # Elementary motion detectors
               'LC', 'LPLC',                 # Lobula columnar
               'LT', 'Li',                   # Lobula tangential/intrinsic
               'lobula'],
    
    # Lobula Plate - wide-field motion
    'LOBULA_PLATE': ['LPi', 'LPi1', 'LPi2', 'LPi3', 'LPi4',
                     'HS', 'HSE', 'HSN', 'HSS',  # Horizontal system
                     'VS', 'VS1', 'VS2', 'VS3',  # Vertical system
                     'CH',                       # Centrifugal horizontal
                     'lobula plate', 'optic glomeruli'],
}

# Neuropil regions for spatial filtering
VISUAL_NEUROPILS = [
    'lamina', 'La', 'LAM',
    'medulla', 'Me', 'MED',
    'lobula', 'Lo', 'LOB',
    'lobula plate', 'LOP', 'LOPL',
    'optic lobe', 'optic',
    'retina', 'RET'
]


def extract_visual_pathway(connectome: Connectome) -> Connectome:
    """
    Extract visual pathway neurons from full FlyWire brain.
    
    Similar to extract_olfactory_pathway() but for vision (~53K neurons).
    
    Args:
        connectome: Full fly brain connectome (139,255 neurons)
    
    Returns:
        Visual connectome with ~53,000 neurons
    """
    print("\n" + "="*70)
    print("EXTRACTING VISUAL PATHWAY FROM FLYWIRE")
    print("="*70)
    
    # Identify visual neurons
    print("Identifying visual neurons...")
    visual_neurons = {}
    type_counts = {key: 0 for key in VISUAL_NEURON_TYPES.keys()}
    
    for nid, neuron in connectome.neurons.items():
        neuron_type = classify_visual_neuron(neuron)
        if neuron_type:
            visual_neurons[nid] = neuron
            type_counts[neuron_type] += 1
    
    print(f"✓ Found {len(visual_neurons):,} visual neurons:")
    for ntype, count in type_counts.items():
        if count > 0:
            print(f"  - {ntype}: {count:,}")
    
    # Extract synapses connecting visual neurons
    print("Extracting visual synapses...")
    visual_synapses = []
    
    for syn in connectome.synapses:
        if syn.pre_id in visual_neurons and syn.post_id in visual_neurons:
            visual_synapses.append(syn)
    
    print(f"✓ Found {len(visual_synapses):,} visual synapses")
    
    # Create visual connectome
    visual_connectome = Connectome(data_dir=connectome.data_dir)
    visual_connectome.neurons = visual_neurons
    visual_connectome.synapses = visual_synapses
    
    # Compute spatial bounds
    if len(visual_neurons) > 0:
        positions = np.array([n.position for n in visual_neurons.values()])
        visual_connectome.min_pos = np.min(positions, axis=0)
        visual_connectome.max_pos = np.max(positions, axis=0)
        visual_connectome.center_pos = np.mean(positions, axis=0)
    
    print(f"✓ Visual pathway extracted:")
    print(f"  - Neurons: {len(connectome.neurons):,} → {len(visual_neurons):,} ({100*len(visual_neurons)/len(connectome.neurons):.1f}%)")
    print(f"  - Synapses: {len(connectome.synapses):,} → {len(visual_synapses):,} ({100*len(visual_synapses)/len(connectome.synapses):.1f}%)")
    if len(visual_neurons) > 0:
        spatial_extent = visual_connectome.max_pos - visual_connectome.min_pos
        print(f"  - Spatial extent: [{spatial_extent[0]:.1f}, {spatial_extent[1]:.1f}, {spatial_extent[2]:.1f}] μm")
    print("="*70)
    
    return visual_connectome


def classify_visual_neuron(neuron: Neuron) -> str:
    """
    Classify neuron as visual type (or None if not visual).
    
    Uses cell type annotations and neuropil location.
    
    Args:
        neuron: Neuron object from FlyWire
    
    Returns:
        Visual type string or None
    """
    # Check cell types (most reliable)
    cell_types_str = ' '.join(neuron.cell_types).upper()
    
    for vis_type, keywords in VISUAL_NEURON_TYPES.items():
        for keyword in keywords:
            if keyword.upper() in cell_types_str:
                return vis_type
    
    # Check neuropil location (group field)
    group_str = neuron.group.upper()
    
    for neuropil in VISUAL_NEUROPILS:
        if neuropil.upper() in group_str:
            # Infer type from neuropil
            if 'LAMINA' in group_str or 'LAM' in group_str:
                return 'LAMINA'
            elif 'MEDULLA' in group_str or 'MED' in group_str:
                return 'MEDULLA'
            elif 'LOBULA PLATE' in group_str or 'LOP' in group_str:
                return 'LOBULA_PLATE'
            elif 'LOBULA' in group_str or 'LOB' in group_str:
                return 'LOBULA'
            elif 'RETINA' in group_str or 'RET' in group_str:
                return 'PHOTORECEPTOR'
    
    return None


def get_visual_region_neurons(
    connectome: Connectome,
    region: str
) -> List[int]:
    """
    Get neuron IDs for a specific visual region.
    
    Args:
        connectome: Visual connectome
        region: 'PHOTORECEPTOR', 'LAMINA', 'MEDULLA', 'LOBULA', 'LOBULA_PLATE'
    
    Returns:
        List of neuron IDs
    """
    neuron_ids = []
    
    for nid, neuron in connectome.neurons.items():
        neuron_type = classify_visual_neuron(neuron)
        if neuron_type == region:
            neuron_ids.append(nid)
    
    return neuron_ids


def analyze_visual_connectivity(connectome: Connectome):
    """
    Analyze connectivity statistics of visual pathway.
    
    Prints:
    - Inter-region connectivity matrix
    - Convergence/divergence ratios
    - Synaptic density by region
    """
    print("\n" + "="*70)
    print("VISUAL PATHWAY CONNECTIVITY ANALYSIS")
    print("="*70)
    
    # Classify all neurons
    neuron_types = {}
    for nid, neuron in connectome.neurons.items():
        ntype = classify_visual_neuron(neuron)
        neuron_types[nid] = ntype
    
    # Count neurons by type
    type_counts = {}
    for ntype in neuron_types.values():
        if ntype:
            type_counts[ntype] = type_counts.get(ntype, 0) + 1
    
    print("\nNeuron counts by region:")
    for region in ['PHOTORECEPTOR', 'LAMINA', 'MEDULLA', 'LOBULA', 'LOBULA_PLATE']:
        count = type_counts.get(region, 0)
        if count > 0:
            print(f"  {region}: {count:,}")
    
    # Build connectivity matrix
    regions = ['PHOTORECEPTOR', 'LAMINA', 'MEDULLA', 'LOBULA', 'LOBULA_PLATE']
    conn_matrix = {pre: {post: 0 for post in regions} for pre in regions}
    
    for syn in connectome.synapses:
        pre_type = neuron_types.get(syn.pre_id)
        post_type = neuron_types.get(syn.post_id)
        
        if pre_type and post_type:
            conn_matrix[pre_type][post_type] += syn.weight
    
    # Print connectivity matrix
    print("\nInter-region synaptic weights:")
    print(f"{'From \\ To':<15}", end='')
    for region in regions:
        print(f"{region[:10]:>12}", end='')
    print()
    
    for pre in regions:
        print(f"{pre:<15}", end='')
        for post in regions:
            count = conn_matrix[pre][post]
            if count > 0:
                print(f"{count:>12,}", end='')
            else:
                print(f"{'—':>12}", end='')
        print()
    
    # Convergence/divergence analysis
    print("\nConvergence/Divergence (key pathways):")
    
    pathways = [
        ('PHOTORECEPTOR', 'LAMINA'),
        ('LAMINA', 'MEDULLA'),
        ('MEDULLA', 'LOBULA'),
        ('MEDULLA', 'LOBULA_PLATE')
    ]
    
    for pre_region, post_region in pathways:
        pre_neurons = [nid for nid, nt in neuron_types.items() if nt == pre_region]
        post_neurons = [nid for nid, nt in neuron_types.items() if nt == post_region]
        
        if not pre_neurons or not post_neurons:
            continue
        
        # Calculate average fan-out and fan-in
        fan_outs = []
        for nid in pre_neurons:
            fan_out = len([syn for syn in connectome.synapses 
                          if syn.pre_id == nid and syn.post_id in post_neurons])
            fan_outs.append(fan_out)
        
        fan_ins = []
        for nid in post_neurons:
            fan_in = len([syn for syn in connectome.synapses 
                         if syn.post_id == nid and syn.pre_id in pre_neurons])
            fan_ins.append(fan_in)
        
        avg_fan_out = np.mean(fan_outs) if fan_outs else 0
        avg_fan_in = np.mean(fan_ins) if fan_ins else 0
        
        expansion = len(post_neurons) / len(pre_neurons) if len(pre_neurons) > 0 else 0
        
        print(f"\n  {pre_region} → {post_region}:")
        print(f"    Expansion: {len(pre_neurons):,} → {len(post_neurons):,} ({expansion:.1f}×)")
        print(f"    Avg fan-out: {avg_fan_out:.1f}")
        print(f"    Avg fan-in: {avg_fan_in:.1f}")
    
    print("="*70)


def get_pathway_sequence(
    connectome: Connectome,
    start_region: str,
    end_region: str
) -> List[str]:
    """
    Get canonical visual pathway sequence between regions.
    
    Args:
        connectome: Visual connectome
        start_region: Start region (e.g., 'PHOTORECEPTOR')
        end_region: End region (e.g., 'LOBULA')
    
    Returns:
        List of regions in pathway order
    """
    # Canonical visual pathway order
    pathway_order = [
        'PHOTORECEPTOR',
        'LAMINA',
        'MEDULLA',
        'LOBULA',
        'LOBULA_PLATE'
    ]
    
    try:
        start_idx = pathway_order.index(start_region)
        end_idx = pathway_order.index(end_region)
        
        if end_idx >= start_idx:
            return pathway_order[start_idx:end_idx+1]
        else:
            return []
    except ValueError:
        return []


if __name__ == "__main__":
    # Test visual pathway extraction
    print("Testing Visual Pathway Extraction\n")
    
    print("This script requires full FlyWire connectome loaded.")
    print("Run optic_lobe_extractor.py to extract and cache visual pathway.")
    
    # Example usage (when connectome is available)
    example = """
    from hive.substrate.connectome import Connectome
    
    # Load full brain
    full_connectome = Connectome(data_dir="Fly Brain Female")
    full_connectome.load()
    
    # Extract visual pathway
    visual = extract_visual_pathway(full_connectome)
    
    # Analyze connectivity
    analyze_visual_connectivity(visual)
    
    # Get specific regions
    medulla_neurons = get_visual_region_neurons(visual, 'MEDULLA')
    print(f"Medulla neurons: {len(medulla_neurons)}")
    """
    
    print("\nExample usage:")
    print(example)
