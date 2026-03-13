"""
Pattern Similarity Metrics

Quantify similarity between simulated and published neural patterns.

Metrics:
- Spatial correlation: Pearson correlation between activity patterns
- Cosine similarity: Angle between pattern vectors
- Wasserstein distance: Earth mover's distance (distribution difference)
- Temporal correlation: Cross-correlation of time-series
- Composite score: Weighted combination

Usage for validation:
- Match quality: correlation > 0.7 and cosine > 0.8 = good match
- Population coding: Wasserstein < 0.5 = similar distributions
"""

import numpy as np
from typing import Dict, Tuple, Optional
from scipy.stats import pearsonr, spearmanr
from scipy.spatial.distance import cosine as cosine_distance


def spatial_correlation(pattern1: np.ndarray, pattern2: np.ndarray) -> float:
    """
    Pearson correlation between spatial activity patterns.
    
    Measures linear relationship between patterns.
    Range: [-1, 1], where 1 = perfect match
    
    Args:
        pattern1: First activity pattern (any shape, will be flattened)
        pattern2: Second activity pattern (same shape as pattern1)
    
    Returns:
        Correlation coefficient
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match: {pattern1.shape} vs {pattern2.shape}")
    
    # Handle edge cases
    if np.std(p1_flat) == 0 or np.std(p2_flat) == 0:
        return 0.0
    
    corr, _ = pearsonr(p1_flat, p2_flat)
    
    return float(corr)


def rank_correlation(pattern1: np.ndarray, pattern2: np.ndarray) -> float:
    """
    Spearman rank correlation (non-parametric).
    
    Robust to outliers and non-linear monotonic relationships.
    
    Args:
        pattern1: First activity pattern
        pattern2: Second activity pattern
    
    Returns:
        Rank correlation coefficient
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    if np.std(p1_flat) == 0 or np.std(p2_flat) == 0:
        return 0.0
    
    corr, _ = spearmanr(p1_flat, p2_flat)
    
    return float(corr)


def cosine_similarity(pattern1: np.ndarray, pattern2: np.ndarray) -> float:
    """
    Cosine similarity (angle between vectors).
    
    Measures orientation similarity, ignoring magnitude.
    Range: [0, 1], where 1 = same direction
    
    Args:
        pattern1: First activity pattern
        pattern2: Second activity pattern
    
    Returns:
        Cosine similarity (1 - cosine distance)
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    # Handle zero vectors
    norm1 = np.linalg.norm(p1_flat)
    norm2 = np.linalg.norm(p2_flat)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # Cosine distance is 1 - cosine similarity
    cos_sim = 1.0 - cosine_distance(p1_flat, p2_flat)
    
    return float(cos_sim)


def euclidean_distance(pattern1: np.ndarray, pattern2: np.ndarray, normalized=True) -> float:
    """
    Euclidean distance between patterns.
    
    Simple L2 distance. If normalized=True, patterns are L2-normalized first.
    
    Args:
        pattern1: First activity pattern
        pattern2: Second activity pattern
        normalized: Whether to L2-normalize patterns first
    
    Returns:
        Euclidean distance (lower is more similar)
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    if normalized:
        norm1 = np.linalg.norm(p1_flat)
        norm2 = np.linalg.norm(p2_flat)
        if norm1 > 0:
            p1_flat = p1_flat / norm1
        if norm2 > 0:
            p2_flat = p2_flat / norm2
    
    dist = np.linalg.norm(p1_flat - p2_flat)
    
    return float(dist)


def wasserstein_distance(pattern1: np.ndarray, pattern2: np.ndarray) -> float:
    """
    Earth mover's distance (Wasserstein-1 distance).
    
    Measures how much "work" is needed to transform one distribution into another.
    Captures distribution shape differences better than correlation.
    
    Args:
        pattern1: First activity pattern
        pattern2: Second activity pattern
    
    Returns:
        Wasserstein distance (lower is more similar)
    """
    from scipy.stats import wasserstein_distance as wd
    
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    # Make non-negative (required for Wasserstein)
    p1_flat = np.maximum(p1_flat, 0)
    p2_flat = np.maximum(p2_flat, 0)
    
    # Handle empty patterns
    if np.sum(p1_flat) == 0 or np.sum(p2_flat) == 0:
        return float('inf')
    
    dist = wd(p1_flat, p2_flat)
    
    return float(dist)


def kullback_leibler_divergence(pattern1: np.ndarray, pattern2: np.ndarray, epsilon=1e-10) -> float:
    """
    KL divergence (information-theoretic distance).
    
    Measures how one probability distribution differs from another.
    Non-symmetric!
    
    Args:
        pattern1: First activity pattern (P)
        pattern2: Second activity pattern (Q)
        epsilon: Small value to avoid log(0)
    
    Returns:
        KL divergence D_KL(P||Q) (lower is more similar)
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    # Make non-negative and normalize to probability distributions
    p1_flat = np.maximum(p1_flat, 0)
    p2_flat = np.maximum(p2_flat, 0)
    
    p1_sum = np.sum(p1_flat)
    p2_sum = np.sum(p2_flat)
    
    if p1_sum == 0 or p2_sum == 0:
        return float('inf')
    
    p1_flat = p1_flat / p1_sum
    p2_flat = p2_flat / p2_sum
    
    # Add epsilon to avoid log(0)
    p1_flat += epsilon
    p2_flat += epsilon
    
    # Renormalize
    p1_flat /= np.sum(p1_flat)
    p2_flat /= np.sum(p2_flat)
    
    # KL divergence
    kl = np.sum(p1_flat * np.log(p1_flat / p2_flat))
    
    return float(kl)


def temporal_correlation(trace1: np.ndarray, trace2: np.ndarray, max_lag: Optional[int] = None) -> Tuple[float, int]:
    """
    Cross-correlation of temporal dynamics.
    
    Finds best time-alignment between two time-series.
    
    Args:
        trace1: First time-series (time × neurons)
        trace2: Second time-series (same shape)
        max_lag: Maximum time lag to consider (default: length/4)
    
    Returns:
        (max_correlation, best_lag)
    """
    from scipy.signal import correlate
    
    if trace1.shape != trace2.shape:
        raise ValueError(f"Trace shapes don't match: {trace1.shape} vs {trace2.shape}")
    
    # Flatten if multi-dimensional
    if trace1.ndim > 1:
        trace1 = trace1.flatten()
        trace2 = trace2.flatten()
    
    # Normalize traces
    trace1 = (trace1 - np.mean(trace1)) / (np.std(trace1) + 1e-10)
    trace2 = (trace2 - np.mean(trace2)) / (np.std(trace2) + 1e-10)
    
    # Cross-correlation
    xcorr = correlate(trace1, trace2, mode='same')
    xcorr /= len(trace1)
    
    # Find peak within max_lag
    if max_lag is None:
        max_lag = len(trace1) // 4
    
    center = len(xcorr) // 2
    lag_range = slice(center - max_lag, center + max_lag)
    
    max_idx = np.argmax(xcorr[lag_range]) + (center - max_lag)
    best_lag = max_idx - center
    max_corr = xcorr[max_idx]
    
    return float(max_corr), int(best_lag)


def population_sparseness(pattern: np.ndarray) -> float:
    """
    Population sparseness (Treves-Rolls metric).
    
    Measures how sparse the neural code is.
    Range: [0, 1], where 1 = only one neuron active
    
    Args:
        pattern: Activity pattern
    
    Returns:
        Sparseness value
    """
    p = pattern.flatten()
    p = np.maximum(p, 0)  # Non-negative
    
    if np.sum(p) == 0:
        return 0.0
    
    n = len(p)
    sum_r = np.sum(p)
    sum_r2 = np.sum(p**2)
    
    if sum_r2 == 0:
        return 0.0
    
    sparseness = (1 - (sum_r**2) / (n * sum_r2)) / (1 - 1/n)
    
    return float(np.clip(sparseness, 0, 1))


def pattern_overlap(pattern1: np.ndarray, pattern2: np.ndarray, threshold=0.1) -> float:
    """
    Fraction of neurons active in both patterns (Jaccard index).
    
    Measures how many neurons are co-active.
    
    Args:
        pattern1: First activity pattern
        pattern2: Second activity pattern
        threshold: Activity threshold for "active" neuron
    
    Returns:
        Overlap coefficient [0, 1]
    """
    p1_flat = pattern1.flatten()
    p2_flat = pattern2.flatten()
    
    if len(p1_flat) != len(p2_flat):
        raise ValueError(f"Pattern shapes don't match")
    
    # Binarize
    active1 = p1_flat > threshold
    active2 = p2_flat > threshold
    
    # Jaccard index
    intersection = np.sum(active1 & active2)
    union = np.sum(active1 | active2)
    
    if union == 0:
        return 0.0
    
    overlap = intersection / union
    
    return float(overlap)


def composite_similarity(pattern1: np.ndarray, pattern2: np.ndarray, 
                        weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """
    Compute all similarity metrics in one call.
    
    Args:
        pattern1: Simulated pattern
        pattern2: Published pattern
        weights: Weights for composite score (default: equal weight)
    
    Returns:
        Dictionary of all metrics + composite score
    """
    if weights is None:
        weights = {
            'spatial_correlation': 0.3,
            'cosine_similarity': 0.3,
            'wasserstein': 0.2,
            'overlap': 0.2
        }
    
    # Compute all metrics
    results = {
        'spatial_correlation': spatial_correlation(pattern1, pattern2),
        'rank_correlation': rank_correlation(pattern1, pattern2),
        'cosine_similarity': cosine_similarity(pattern1, pattern2),
        'euclidean_distance': euclidean_distance(pattern1, pattern2),
        'wasserstein_distance': wasserstein_distance(pattern1, pattern2),
        'pattern_overlap': pattern_overlap(pattern1, pattern2),
        'sparseness_p1': population_sparseness(pattern1),
        'sparseness_p2': population_sparseness(pattern2),
    }
    
    # Composite score (higher is better)
    # Normalize metrics to [0, 1] scale where 1 = perfect match
    composite = 0.0
    
    if 'spatial_correlation' in weights:
        # Correlation: [-1, 1] → [0, 1]
        norm_corr = (results['spatial_correlation'] + 1) / 2
        composite += weights['spatial_correlation'] * norm_corr
    
    if 'cosine_similarity' in weights:
        # Cosine: already [0, 1]
        composite += weights['cosine_similarity'] * results['cosine_similarity']
    
    if 'wasserstein' in weights:
        # Wasserstein: distance, so invert and normalize (assume max ~2.0)
        norm_wass = 1.0 - np.clip(results['wasserstein_distance'] / 2.0, 0, 1)
        composite += weights['wasserstein'] * norm_wass
    
    if 'overlap' in weights:
        # Overlap: already [0, 1]
        composite += weights['overlap'] * results['pattern_overlap']
    
    results['composite_score'] = composite
    
    return results


def is_good_match(metrics: Dict[str, float], 
                 min_correlation=0.7, 
                 min_cosine=0.8,
                 max_wasserstein=0.5) -> bool:
    """
    Determine if similarity metrics indicate a good match.
    
    Args:
        metrics: Output from composite_similarity()
        min_correlation: Minimum spatial correlation
        min_cosine: Minimum cosine similarity
        max_wasserstein: Maximum Wasserstein distance
    
    Returns:
        True if match is good
    """
    return (metrics['spatial_correlation'] >= min_correlation and
            metrics['cosine_similarity'] >= min_cosine and
            metrics['wasserstein_distance'] <= max_wasserstein)


def print_similarity_report(pattern1: np.ndarray, pattern2: np.ndarray, 
                           label1='Simulated', label2='Published'):
    """
    Print detailed similarity report.
    
    Args:
        pattern1: First pattern
        pattern2: Second pattern
        label1: Label for first pattern
        label2: Label for second pattern
    """
    metrics = composite_similarity(pattern1, pattern2)
    
    print("\n" + "="*70)
    print(f"PATTERN SIMILARITY: {label1} vs {label2}")
    print("="*70)
    
    print(f"\nCorrelation metrics:")
    print(f"  Spatial correlation:  {metrics['spatial_correlation']:6.3f}")
    print(f"  Rank correlation:     {metrics['rank_correlation']:6.3f}")
    print(f"  Cosine similarity:    {metrics['cosine_similarity']:6.3f}")
    
    print(f"\nDistance metrics:")
    print(f"  Euclidean distance:   {metrics['euclidean_distance']:6.3f}")
    print(f"  Wasserstein distance: {metrics['wasserstein_distance']:6.3f}")
    
    print(f"\nCoding properties:")
    print(f"  Pattern overlap:      {metrics['pattern_overlap']:6.3f}")
    print(f"  Sparseness ({label1}): {metrics['sparseness_p1']:6.3f}")
    print(f"  Sparseness ({label2}): {metrics['sparseness_p2']:6.3f}")
    
    print(f"\nComposite score:        {metrics['composite_score']:6.3f}")
    
    match_quality = "GOOD" if is_good_match(metrics) else "POOR"
    print(f"\nMatch quality:          {match_quality}")
    
    print("="*70)


if __name__ == "__main__":
    # Test similarity metrics
    print("\n" + "="*70)
    print("TESTING SIMILARITY METRICS")
    print("="*70)
    
    # Create test patterns
    print("\nTest 1: Identical patterns")
    p1 = np.random.lognormal(0, 0.5, 100)
    p1 /= np.linalg.norm(p1)
    print_similarity_report(p1, p1, 'Pattern A', 'Pattern A (copy)')
    
    print("\nTest 2: Similar patterns (with noise)")
    p2 = p1 + np.random.normal(0, 0.1, 100)
    p2 /= np.linalg.norm(p2)
    print_similarity_report(p1, p2, 'Pattern A', 'Pattern A + noise')
    
    print("\nTest 3: Different patterns")
    p3 = np.random.lognormal(0, 0.5, 100)
    p3 /= np.linalg.norm(p3)
    print_similarity_report(p1, p3, 'Pattern A', 'Pattern B')
    
    print("\n" + "="*70)
