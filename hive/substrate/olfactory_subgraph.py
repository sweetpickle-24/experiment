"""
Olfactory Pathway Extraction: Focus on smell-processing neurons only.

Extract olfactory-specific neurons and synapses from full connectome:
- ORN (Olfactory Receptor Neurons): ~700 neurons
- PN (Projection Neurons): ~5,670 neurons
- LN (Local Neurons): glomerular processing
- KC (Kenyon Cells): ~5,595 neurons (mushroom body)
- APL (Anterior Paired Lateral): inhibitory feedback
- MBON (Mushroom Body Output Neurons): ~2,972 neurons
- DAN (Dopaminergic Neurons): reward/learning

Total: ~15,000 neurons vs. 139K full brain
Synapses: ~500K vs. 5.3M full brain
"""

import numpy as np
from typing import Dict, List, Set
from ..substrate.connectome import Connectome, Neuron, Synapse


# Olfactory neuron type keywords
OLFACTORY_TYPES = {
    'ORN': ['ORN', 'Olfactory Receptor'],
    'PN': ['PN', 'uPN', 'mPN', 'Projection Neuron', 'adPN', 'lPN', 'vPN'],
    'LN': ['LN', 'Local Neuron'],
    'KC': ['KC', 'Kenyon', 'KCab', 'KCg', "KC'"],
    'APL': ['APL'],
    'MBON': ['MBON', 'MB output'],
    'DAN': ['DAN', 'PAM', 'PPL'],
}


def extract_olfactory_pathway(connectome: Connectome) -> Connectome:
    """
    Extract olfactory-only neurons and synapses from full connectome.
    
    Args:
        connectome: Full fly brain connectome
    
    Returns:
        New Connectome with only olfactory pathway
    """
    print("\n" + "="*70)
    print("EXTRACTING OLFACTORY PATHWAY")
    print("="*70)
    
    # Identify olfactory neurons
    print("Identifying olfactory neurons...")
    olfactory_neurons = {}
    type_counts = {key: 0 for key in OLFACTORY_TYPES.keys()}
    
    for nid, neuron in connectome.neurons.items():
        neuron_type = classify_olfactory_neuron(neuron)
        if neuron_type:
            olfactory_neurons[nid] = neuron
            type_counts[neuron_type] += 1
    
    print(f"✓ Found {len(olfactory_neurons):,} olfactory neurons:")
    for ntype, count in type_counts.items():
        if count > 0:
            print(f"  - {ntype}: {count:,}")
    
    # Extract synapses connecting olfactory neurons
    print("Extracting olfactory synapses...")
    olfactory_synapses = []
    
    for syn in connectome.synapses:
        if syn.pre_id in olfactory_neurons and syn.post_id in olfactory_neurons:
            olfactory_synapses.append(syn)
    
    print(f"✓ Found {len(olfactory_synapses):,} olfactory synapses")
    
    # Create new connectome
    olfactory_connectome = Connectome(data_dir=connectome.data_dir)
    olfactory_connectome.neurons = olfactory_neurons
    olfactory_connectome.synapses = olfactory_synapses
    
    # Compute spatial bounds
    positions = np.array([n.position for n in olfactory_neurons.values()])
    olfactory_connectome.min_pos = np.min(positions, axis=0)
    olfactory_connectome.max_pos = np.max(positions, axis=0)
    olfactory_connectome.center_pos = np.mean(positions, axis=0)
    
    print(f"✓ Olfactory pathway extracted:")
    print(f"  - Neurons: {len(connectome.neurons):,} → {len(olfactory_neurons):,} ({100*len(olfactory_neurons)/len(connectome.neurons):.1f}%)")
    print(f"  - Synapses: {len(connectome.synapses):,} → {len(olfactory_synapses):,} ({100*len(olfactory_synapses)/len(connectome.synapses):.1f}%)")
    print(f"  - Spatial extent: {olfactory_connectome.max_pos - olfactory_connectome.min_pos} μm")
    print("="*70)
    
    return olfactory_connectome


def classify_olfactory_neuron(neuron: Neuron) -> str:
    """
    Classify neuron as olfactory type (or None if not olfactory).
    
    Args:
        neuron: Neuron object
    
    Returns:
        Olfactory type string ('ORN', 'PN', etc.) or None
    """
    # Check cell types
    cell_types_str = ' '.join(neuron.cell_types).upper()
    
    for olf_type, keywords in OLFACTORY_TYPES.items():
        for keyword in keywords:
            if keyword.upper() in cell_types_str:
                return olf_type
    
    # Check group (neuropil region)
    group_str = neuron.group.upper()
    
    # Antennal lobe (AL) contains ORNs, PNs, LNs
    if 'AL' in group_str or 'ANTENNAL' in group_str:
        # Further classify by neurotransmitter or morphology
        if 'GLUT' in neuron.nt_type.upper():
            return 'PN'  # PNs are glutamatergic
        elif 'GABA' in neuron.nt_type.upper():
            return 'LN'  # LNs are GABAergic
        else:
            return 'PN'  # Default to PN
    
    # Mushroom body (MB) contains KCs, MBONs
    if 'MB' in group_str or 'MUSHROOM' in group_str:
        if 'OUTPUT' in cell_types_str or 'MBON' in cell_types_str:
            return 'MBON'
        else:
            return 'KC'  # Kenyon cells
    
    # Calyx - MB input region (KCs)
    if 'CA' in group_str and 'CALYX' in group_str:
        return 'KC'
    
    return None


def get_olfactory_region_neurons(connectome: Connectome, region: str) -> List[int]:
    """
    Get neuron IDs for a specific olfactory region.
    
    Args:
        connectome: Olfactory connectome
        region: 'ORN', 'PN', 'LN', 'KC', 'APL', 'MBON', or 'DAN'
    
    Returns:
        List of neuron IDs
    """
    neuron_ids = []
    
    for nid, neuron in connectome.neurons.items():
        neuron_type = classify_olfactory_neuron(neuron)
        if neuron_type == region:
            neuron_ids.append(nid)
    
    return neuron_ids


def analyze_olfactory_connectivity(connectome: Connectome):
    """
    Analyze connectivity statistics of olfactory pathway.
    
    Prints:
    - Inter-region connectivity matrix
    - Convergence/divergence ratios
    - Synapse density by region
    """
    print("\n" + "="*70)
    print("OLFACTORY PATHWAY CONNECTIVITY ANALYSIS")
    print("="*70)
    
    # Classify all neurons
    neuron_types = {}
    for nid, neuron in connectome.neurons.items():
        ntype = classify_olfactory_neuron(neuron)
        neuron_types[nid] = ntype
    
    # Build connectivity matrix
    regions = list(OLFACTORY_TYPES.keys())
    conn_matrix = {pre: {post: 0 for post in regions} for pre in regions}
    
    for syn in connectome.synapses:
        pre_type = neuron_types.get(syn.pre_id)
        post_type = neuron_types.get(syn.post_id)
        
        if pre_type and post_type:
            conn_matrix[pre_type][post_type] += syn.weight
    
    # Print connectivity matrix
    print("\nInter-region synaptic weights:")
    print(f"{'From \\ To':<10}", end='')
    for region in regions:
        print(f"{region:>10}", end='')
    print()
    
    for pre in regions:
        print(f"{pre:<10}", end='')
        for post in regions:
            count = conn_matrix[pre][post]
            if count > 0:
                print(f"{count:>10,}", end='')
            else:
                print(f"{'—':>10}", end='')
        print()
    
    # Convergence ratios
    print("\nConvergence/Divergence:")
    for region in ['PN', 'KC', 'MBON']:
        region_neurons = [nid for nid, nt in neuron_types.items() if nt == region]
        if not region_neurons:
            continue
        
        # Average fan-in
        fan_ins = []
        for nid in region_neurons:
            fan_in = len([syn for syn in connectome.synapses if syn.post_id == nid])
            fan_ins.append(fan_in)
        
        avg_fan_in = np.mean(fan_ins) if fan_ins else 0
        
        print(f"  {region}: avg fan-in = {avg_fan_in:.1f}")
    
    print("="*70)


if __name__ == "__main__":
    # Test extraction
    from ..substrate.connectome import Connectome
    
    print("Loading full connectome...")
    full_connectome = Connectome()
    full_connectome.load()
    
    # Extract olfactory pathway
    olfactory = extract_olfactory_pathway(full_connectome)
    
    # Analyze connectivity
    analyze_olfactory_connectivity(olfactory)
