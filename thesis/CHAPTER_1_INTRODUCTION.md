# Chapter 1: Introduction

---

## 1.1 The Problem: What is a Digital Smell?

Vision can be represented as pixel arrays. Sound as waveforms. But smell remains elusive — chemistry doesn't have a "natural" digital encoding. The question we address: **How does the brain encode smell as neural activity?**

## 1.2 Biological Context

The *Drosophila* olfactory system transforms chemical signals into sparse neural codes through a well-characterized pathway:

1. **ORN (Olfactory Receptor Neurons)**: ~2,279 neurons detect chemicals
2. **PN (Projection Neurons)**: ~2,198 neurons amplify signals in antennal lobe
3. **KC (Kenyon Cells)**: ~5,279 neurons in mushroom body create sparse codes
4. **MBON (Mushroom Body Output)**: ~96 neurons drive behavior

This is one of the only complete neural circuits mapped at synaptic resolution (Dorkenwald et al. 2024).

## 1.3 Theoretical Foundation: Sparse Coding Theory

**What is Sparse Coding?**

Sparse coding theory (Olshausen & Field 1996, Rolls & Tovee 1995) proposes that neural systems maximize information capacity and discrimination by representing stimuli using minimal active neurons. This has three key advantages:

**1. Memory Capacity:**
- Dense coding (50% active): Each memory requires modifying ~2,500 synapses
  - Capacity: N_synapses / 2,500 ≈ 200 memories for 5,279 KCs
- Sparse coding (2% active): Each memory requires modifying ~50 synapses  
  - Capacity: N_synapses / 50 ≈ 10,000 memories for 5,279 KCs
- **Result: 50× memory capacity increase**

**2. Metabolic Efficiency:**
- Action potentials consume ~10⁹ ATP per spike
- 2% active: 105 neurons firing → 10¹¹ ATP/second
- 50% active: 2,640 neurons firing → 10¹³ ATP/second
- **Result: 100× energy savings**

**3. Discrimination by Decorrelation:**
- Dense codes: Similar inputs → Similar outputs (correlation preserved)
  - Example: Apple (chem: [0.8, 0.7, 0.3]) → KC: [0.75, 0.65, 0.28]
  - Result: High correlation makes discrimination difficult
- Sparse codes: Similar inputs → Dissimilar outputs (orthogonalization)
  - Example: Apple (chem: [0.8, 0.7, 0.3]) → KC: {1, 5, 42, 105}
  - Example: Apricot (chem: [0.75, 0.72, 0.25]) → KC: {12, 88, 234, 501}
  - Result: Zero overlap despite 90% chemical similarity
- **Result: 1000× better discrimination**

**Sparse Expansion Coding in Olfaction:**

The mushroom body implements sparse expansion through:
1. **Expansion Layer**: 2,198 PNs (input) → 5,279 KCs (2.4× expansion)
2. **Random Connectivity**: Each KC samples ~7 random PNs (Caron et al. 2013)
3. **High Threshold**: KCs require strong coincident input to activate
4. **Global Inhibition**: APL neuron enforces winner-take-all competition

**Theoretical Predictions (Litwin-Kumar et al. 2017):**
1. KC activity should be 1-5% (sparse)
2. Chemically similar odors should produce decorrelated KC patterns (r < 0)
3. Expansion ratio should be 2-10× input dimensionality
4. Discrimination capacity scales with KC population size

**Our Contribution:**
First computational validation that these predictions emerge from wave physics applied to the real connectome, without explicit tuning.

## 1.4 Existing Approaches

**Experimental (Calcium Imaging)**:
- Turner et al. 2008: Recorded 50-200 KCs, observed 1-3% sparsity
- Lin et al. 2014: Found ~200 KCs active per odor
- **Limitation**: Can only record subset of neurons, no full circuit view

**Computational (Rate-Based Models)**:
- Bazhenov et al. 2001: Rate-based AL-MB model
- Luo et al. 2010: Spiking neuron models
- **Limitation**: Don't capture wave dynamics, use abstract connectivity

**Our Approach**:
Wave-based probabilistic oscillators on the real connectome — combining biological realism with computational efficiency while testing sparse coding predictions.
