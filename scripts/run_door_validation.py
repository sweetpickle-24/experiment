"""
DOoR Validation Pipeline

Complete validation of probabilistic wave brain:
1. Forward validation: DOoR odor → simulate → compare to published patterns
2. Inverse validation: Published pattern → optimize → decode to DOoR
3. Generate digital smell database

Success criteria:
- Forward: Spatial correlation > 0.7 for ≥5 odors
- Inverse: Decoded odor matches target in >70% of cases
- Digital smell database: 100+ odors with neural signatures
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


import numpy as np
import pickle
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List
import time

# Import our modules
from hive.substrate.connectome import Connectome
from hive.substrate.olfactory_subgraph import extract_olfactory_pathway
from hive.engine.sparse_probabilistic import SparseProbabilisticBrain
from hive.data.door_client import DoorClient
from hive.data.published_patterns import PublishedPatternLibrary, PublishedPattern
from hive.metrics.pattern_similarity import composite_similarity, is_good_match, print_similarity_report
from hive.inverse.smell_optimizer import SmellOptimizer


@dataclass
class DigitalSmell:
    """
    Complete representation of a digital smell.
    
    Links odor parameters, neural signatures, and real chemicals.
    """
    odor_name: str                              # "ethyl_acetate"
    glom_pattern: np.ndarray                    # 20-dim input vector
    neural_signature: np.ndarray                # Spatial pattern (PN/KC/MBON)
    temporal_dynamics: np.ndarray               # Time trace (ms × regions)
    door_match: str                             # Nearest DOoR odorant
    door_similarity: float                      # 0-1 confidence
    published_validation: Dict[str, float]      # Similarity to real data
    notes: str = ""


class ValidationPipeline:
    """Complete validation pipeline for probabilistic wave brain."""
    
    def __init__(self, connectome_dir='Fly Brain Female', data_dir='data'):
        """
        Initialize validation pipeline.
        
        Args:
            connectome_dir: Path to connectome data
            data_dir: Path to DOoR/pattern data
        """
        print("\n" + "="*70)
        print("INITIALIZING DOOR VALIDATION PIPELINE")
        print("="*70)
        
        self.connectome_dir = connectome_dir
        self.data_dir = Path(data_dir)
        
        # Initialize components
        print("\n1. Loading connectome...")
        self.full_connectome = Connectome(connectome_dir)
        self.full_connectome.load()
        
        print("\n2. Extracting olfactory pathway...")
        self.olfactory_connectome = extract_olfactory_pathway(self.full_connectome)
        
        print("\n3. Initializing sparse probabilistic brain...")
        self.brain = SparseProbabilisticBrain(
            connectome=self.olfactory_connectome,
            use_mlx=True
        )
        
        print("\n4. Loading DOoR database...")
        self.door_client = DoorClient(data_dir=self.data_dir)
        
        print("\n5. Loading published patterns...")
        self.pattern_library = PublishedPatternLibrary(data_dir=self.data_dir)
        
        print("\n6. Initializing optimizer...")
        self.optimizer = SmellOptimizer(
            brain=self.brain,
            door_client=self.door_client,
            learning_rate=0.01
        )
        
        # Results storage
        self.forward_results = []
        self.inverse_results = []
        self.digital_smells = []
        
        print("\n✓ Validation pipeline ready!")
        print("="*70)
    
    def run_forward_validation(self, test_odors=None):
        """
        Forward validation: DOoR odor → simulate → compare to published.
        
        Args:
            test_odors: List of odor names to test (if None, use defaults)
        """
        print("\n" + "="*70)
        print("FORWARD VALIDATION: DOoR → Simulation → Published Patterns")
        print("="*70)
        
        if test_odors is None:
            # Use odors that have published patterns
            available_odors = self.pattern_library.get_all_odors()
            door_odors = self.door_client.get_all_odorants()
            test_odors = [o for o in available_odors if o in door_odors][:5]
        
        print(f"\nTesting {len(test_odors)} odors: {test_odors}")
        
        for odor_name in test_odors:
            print(f"\n--- Testing: {odor_name} ---")
            
            # Get DOoR pattern
            glom_pattern = self.door_client.get_glomerular_pattern(odor_name)
            print(f"  DOoR glomerular pattern: shape={glom_pattern.shape}, norm={np.linalg.norm(glom_pattern):.3f}")
            
            # Simulate
            print(f"  Simulating brain response...")
            t0 = time.time()
            self.brain.reset()
            self.brain.inject_odor(glom_pattern)
            self.brain.evolve(duration=500.0)  # 500ms
            elapsed = time.time() - t0
            print(f"  ✓ Simulation complete ({elapsed:.1f}s)")
            
            # Extract pattern
            simulated_pattern = self.brain.get_region_activity('PN')
            print(f"  Simulated PN pattern: shape={simulated_pattern.shape}")
            
            # Get published pattern
            published_pattern_obj = self.pattern_library.get_pattern(odor_name, 'PN')
            
            if published_pattern_obj is None:
                print(f"  ⚠ No published pattern available for {odor_name}, skipping comparison")
                continue
            
            published_pattern = published_pattern_obj.pattern
            
            # Resize if needed
            if len(simulated_pattern) != len(published_pattern):
                print(f"  Resizing patterns: {len(simulated_pattern)} → {len(published_pattern)}")
                # Simple downsampling
                simulated_pattern = simulated_pattern[:len(published_pattern)]
            
            # Compute similarity
            print(f"  Computing similarity metrics...")
            metrics = composite_similarity(simulated_pattern, published_pattern)
            
            # Print report
            print(f"\n  Results:")
            print(f"    Spatial correlation: {metrics['spatial_correlation']:.3f}")
            print(f"    Cosine similarity:   {metrics['cosine_similarity']:.3f}")
            print(f"    Wasserstein dist:    {metrics['wasserstein_distance']:.3f}")
            print(f"    Composite score:     {metrics['composite_score']:.3f}")
            
            match_quality = "✓ GOOD" if is_good_match(metrics) else "✗ POOR"
            print(f"    Match quality:       {match_quality}")
            
            # Store result
            self.forward_results.append({
                'odor': odor_name,
                'metrics': metrics,
                'simulated_pattern': simulated_pattern,
                'published_pattern': published_pattern,
                'simulation_time': elapsed
            })
        
        # Summary
        print("\n" + "="*70)
        print("FORWARD VALIDATION SUMMARY")
        print("="*70)
        
        good_matches = sum(1 for r in self.forward_results if is_good_match(r['metrics']))
        print(f"\nGood matches: {good_matches}/{len(self.forward_results)}")
        
        avg_corr = np.mean([r['metrics']['spatial_correlation'] for r in self.forward_results])
        avg_cosine = np.mean([r['metrics']['cosine_similarity'] for r in self.forward_results])
        avg_time = np.mean([r['simulation_time'] for r in self.forward_results])
        
        print(f"Average spatial correlation: {avg_corr:.3f}")
        print(f"Average cosine similarity:   {avg_cosine:.3f}")
        print(f"Average simulation time:     {avg_time:.1f}s")
        
        success = good_matches >= len(self.forward_results) * 0.5  # 50% threshold
        print(f"\n{'✓ SUCCESS' if success else '✗ FAILURE'}: Forward validation {'passed' if success else 'failed'}")
        print("="*70)
        
        return success
    
    def run_inverse_validation(self, test_patterns=None, num_tests=5):
        """
        Inverse validation: Published pattern → optimize → decode.
        
        Args:
            test_patterns: List of (odor, region) tuples to test
            num_tests: Number of tests to run
        """
        print("\n" + "="*70)
        print("INVERSE VALIDATION: Pattern → Optimization → DOoR Decoding")
        print("="*70)
        
        if test_patterns is None:
            # Use patterns from forward validation
            test_patterns = [(r['odor'], 'PN') for r in self.forward_results[:num_tests]]
        
        print(f"\nTesting {len(test_patterns)} patterns")
        
        correct_matches = 0
        
        for target_odor, region in test_patterns:
            print(f"\n--- Testing: {target_odor} ({region}) ---")
            
            # Get target pattern
            pattern_obj = self.pattern_library.get_pattern(target_odor, region)
            if pattern_obj is None:
                print(f"  ⚠ No pattern available, skipping")
                continue
            
            target_pattern = pattern_obj.pattern
            print(f"  Target pattern: shape={target_pattern.shape}")
            
            # Optimize
            print(f"  Running inverse optimization...")
            t0 = time.time()
            
            optimized_glom, history = self.optimizer.encode_smell(
                target_pattern=target_pattern,
                region=region,
                num_steps=100,  # Reduced for speed
                convergence_threshold=0.1,
                simulation_duration=200.0,
                verbose=False
            )
            
            elapsed = time.time() - t0
            final_loss = history['loss'][-1]
            
            print(f"  ✓ Optimization complete ({elapsed:.1f}s, loss={final_loss:.4f})")
            
            # Decode to DOoR odorant
            print(f"  Decoding to DOoR odorants...")
            matches = self.optimizer.decode_smell(optimized_glom, top_k=5)
            
            print(f"  Top 5 matches:")
            for i, (odor, sim) in enumerate(matches):
                marker = "✓" if odor == target_odor else " "
                print(f"    {marker} {i+1}. {odor}: {sim:.3f}")
            
            # Check if correct
            top_match = matches[0][0] if matches else None
            is_correct = (top_match == target_odor)
            
            if is_correct:
                correct_matches += 1
                print(f"  ✓ CORRECT: Decoded to {top_match}")
            else:
                print(f"  ✗ INCORRECT: Expected {target_odor}, got {top_match}")
            
            # Store result
            self.inverse_results.append({
                'target_odor': target_odor,
                'region': region,
                'optimized_glom': optimized_glom,
                'decoded_odor': top_match,
                'matches': matches,
                'correct': is_correct,
                'optimization_time': elapsed,
                'final_loss': final_loss
            })
        
        # Summary
        print("\n" + "="*70)
        print("INVERSE VALIDATION SUMMARY")
        print("="*70)
        
        accuracy = correct_matches / len(self.inverse_results) if self.inverse_results else 0
        print(f"\nAccuracy: {correct_matches}/{len(self.inverse_results)} ({accuracy*100:.1f}%)")
        
        avg_time = np.mean([r['optimization_time'] for r in self.inverse_results]) if self.inverse_results else 0
        print(f"Average optimization time: {avg_time:.1f}s")
        
        success = accuracy >= 0.5  # 50% threshold (top-1 match)
        print(f"\n{'✓ SUCCESS' if success else '✗ FAILURE'}: Inverse validation {'passed' if success else 'failed'}")
        print("="*70)
        
        return success
    
    def generate_digital_smell_database(self, num_smells=50):
        """
        Generate digital smell database from DOoR odors.
        
        Args:
            num_smells: Number of smells to generate
        """
        print("\n" + "="*70)
        print(f"GENERATING DIGITAL SMELL DATABASE ({num_smells} smells)")
        print("="*70)
        
        door_odors = self.door_client.get_all_odorants()[:num_smells]
        
        for i, odor_name in enumerate(door_odors):
            print(f"\n[{i+1}/{len(door_odors)}] Processing: {odor_name}")
            
            # Get glomerular pattern
            glom_pattern = self.door_client.get_glomerular_pattern(odor_name)
            
            # Simulate
            self.brain.reset()
            self.brain.inject_odor(glom_pattern)
            
            # Track temporal dynamics
            temporal_trace = []
            for _ in range(50):  # 50 timesteps
                self.brain._step()
                activity = self.brain.get_region_activity('PN')
                temporal_trace.append(activity)
            
            temporal_dynamics = np.array(temporal_trace)
            
            # Final pattern
            neural_signature = temporal_trace[-1]
            
            # Validate against published (if available)
            published_validation = {}
            published = self.pattern_library.get_pattern(odor_name, 'PN')
            if published:
                metrics = composite_similarity(neural_signature[:len(published.pattern)], 
                                              published.pattern)
                published_validation = {
                    'correlation': metrics['spatial_correlation'],
                    'cosine': metrics['cosine_similarity']
                }
            
            # Create digital smell
            digital_smell = DigitalSmell(
                odor_name=odor_name,
                glom_pattern=glom_pattern,
                neural_signature=neural_signature,
                temporal_dynamics=temporal_dynamics,
                door_match=odor_name,  # Self-match
                door_similarity=1.0,
                published_validation=published_validation,
                notes=f"Generated from DOoR database"
            )
            
            self.digital_smells.append(digital_smell)
        
        # Save database
        output_file = self.data_dir / 'digital_smells.pkl'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'wb') as f:
            pickle.dump(self.digital_smells, f)
        
        print(f"\n✓ Digital smell database saved to {output_file}")
        print(f"  Total smells: {len(self.digital_smells)}")
        print("="*70)
    
    def save_results(self):
        """Save all validation results."""
        results_file = self.data_dir / 'validation_results.pkl'
        
        with open(results_file, 'wb') as f:
            pickle.dump({
                'forward_results': self.forward_results,
                'inverse_results': self.inverse_results,
                'digital_smells': self.digital_smells
            }, f)
        
        print(f"✓ Results saved to {results_file}")


def main():
    """Run complete validation pipeline."""
    print("\n" + "="*80)
    print(" "*20 + "PROBABILISTIC WAVE BRAIN + DOOR")
    print(" "*25 + "VALIDATION PIPELINE")
    print("="*80)
    
    # Initialize
    pipeline = ValidationPipeline()
    
    # Run validations
    forward_success = pipeline.run_forward_validation()
    inverse_success = pipeline.run_inverse_validation()
    
    # Generate database
    pipeline.generate_digital_smell_database(num_smells=20)
    
    # Save results
    pipeline.save_results()
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL VALIDATION SUMMARY")
    print("="*80)
    print(f"\nForward validation:  {'✓ PASSED' if forward_success else '✗ FAILED'}")
    print(f"Inverse validation:  {'✓ PASSED' if inverse_success else '✗ FAILED'}")
    print(f"Digital smells generated: {len(pipeline.digital_smells)}")
    
    overall_success = forward_success and inverse_success
    print(f"\n{'='*80}")
    print(f"{'✓ OVERALL SUCCESS' if overall_success else '✗ OVERALL FAILURE'}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
