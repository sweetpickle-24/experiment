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


def extract_olfactory_pathway(connectome: Connectome,
                              strict: bool = False) -> Connectome:
    """
    Extract olfactory-only neurons and synapses from full connectome.
    
    Args:
        connectome: Full fly brain connectome
        strict: forwarded to classify_olfactory_neuron. Off by default; turning
            it on excludes auditory wedge PNs and unnamed central-brain neurons
            from the PN population, which changes the subgraph size and makes
            results incomparable with runs made without it. See that function.
    
    Returns:
        New Connectome with only olfactory pathway
    """
    print("\n" + "="*70)
    print("EXTRACTING OLFACTORY PATHWAY" + ("  [strict]" if strict else ""))
    print("="*70)
    
    # Identify olfactory neurons
    print("Identifying olfactory neurons...")
    olfactory_neurons = {}
    type_counts = {key: 0 for key in OLFACTORY_TYPES.keys()}
    
    for nid, neuron in connectome.neurons.items():
        neuron_type = classify_olfactory_neuron(neuron, strict=strict)
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


#: Cell-type prefixes that the loose 'PN' substring match sweeps in but that are
#: not olfactory projection neurons. Measured against
#: consolidated_cell_types.csv.gz on 2026-09-04: of the 854 neurons whose type
#: string contains 'PN', 289 are uniglomerular olfactory PNs, 264 are
#: multiglomerular M_ PNs, and these two groups account for 254 - about 30 % -
#: that are not olfactory at all.
NON_OLFACTORY_PN_PREFIXES = (
    'WEDPN',   # wedge projection neurons: auditory/mechanosensory, 93 neurons
    'CB',      # unnamed central brain neurons, 161 neurons
)


def _is_non_olfactory_pn(cell_types_str: str) -> bool:
    """True when a 'PN' match came from a non-olfactory cell type."""
    for token in cell_types_str.replace(',', ' ').split():
        if token.startswith(NON_OLFACTORY_PN_PREFIXES):
            return True
    return False


def classify_olfactory_neuron(neuron: Neuron, strict: bool = False) -> str:
    """
    Classify neuron as olfactory type (or None if not olfactory).

    Args:
        neuron: Neuron object
        strict: reject cell types that match an olfactory keyword only by
            substring accident. Off by default, because turning it on changes the
            PN population and therefore the size of the extracted subgraph, which
            would silently make every previously recorded result incomparable.

            What it rejects, and why it matters: the loose match tests
            ``'PN' in cell_types_str``, so ``WEDPN6B`` (an auditory wedge
            projection neuron) and ``CB1078`` (an unnamed central brain neuron)
            are both classified as olfactory PNs. Measured on the shipped
            annotations, 93 WEDPN and 161 CB neurons are swept in this way, about
            30 % of the 854 neurons whose type string contains 'PN'.

            Strict mode does not touch the neuropil-region fallback below, which
            is where most of the PN population actually comes from.

    Returns:
        Olfactory type string ('ORN', 'PN', etc.) or None
    """
    # Check cell types
    cell_types_str = ' '.join(neuron.cell_types).upper()

    for olf_type, keywords in OLFACTORY_TYPES.items():
        for keyword in keywords:
            if keyword.upper() in cell_types_str:
                if strict and olf_type == 'PN' and \
                        _is_non_olfactory_pn(cell_types_str):
                    # Do not return PN, and do not let a later keyword rescue it
                    # on the same accident; fall through to the region check.
                    break
                return olf_type
    
    # Check group (neuropil region)
    group_str = neuron.group.upper()
    
    # Antennal lobe (AL) contains ORNs, PNs, LNs
    if _in_region(group_str, 'AL', strict) or 'ANTENNAL' in group_str:
        # Further classify by neurotransmitter or morphology
        if 'GLUT' in neuron.nt_type.upper():
            return 'PN'  # PNs are glutamatergic
        elif 'GABA' in neuron.nt_type.upper():
            return 'LN'  # LNs are GABAergic
        else:
            return 'PN'  # Default to PN
    
    # Mushroom body (MB) contains KCs, MBONs
    if _in_region(group_str, 'MB', strict) or 'MUSHROOM' in group_str:
        if 'OUTPUT' in cell_types_str or 'MBON' in cell_types_str:
            return 'MBON'
        else:
            return 'KC'  # Kenyon cells
    
    # Calyx - MB input region (KCs)
    if 'CA' in group_str and 'CALYX' in group_str:
        return 'KC'
    
    return None


def _in_region(group_str: str, region: str, strict: bool) -> bool:
    """
    Is *group_str* a neuropil annotation for *region*?

    Loose (default, pre-2026-09-04 behaviour): plain substring test. This is a
    real defect and it is large. Group strings are dot-separated neuropil lists
    like ``AL``, ``AL.MB_CA``, ``LAL``, ``PLP.LAL``, and ``'AL' in group_str``
    therefore matches every LAL neuron - the lateral accessory lobe, a central
    complex output region with no olfactory role. Measured on the shipped
    annotations: the substring test matches **4,796** neurons where only
    **2,762** are annotated ``AL``. That is how ``PFL3`` (central complex) and
    ``LC33`` (lobula columnar, visual) end up classified as olfactory projection
    neurons.

    Strict: *region* must appear as a whole dot-separated token. That keeps the
    genuinely AL-related compartments - ``AL``, ``AL.LH``, ``AL.MB_CA``,
    ``AL.PLP``, ``AL.SMP`` - and rejects ``LAL`` and its combinations.
    """
    if not strict:
        return region in group_str
    return region in {token.strip() for token in group_str.split('.')}


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
