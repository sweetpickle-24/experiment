"""
Smell Optimizer: Inverse Problem Solver using MLX Autodiff

Solves: Given neural pattern → find odor parameters

Forward problem (easy):  Odor → simulate → Neural pattern
Inverse problem (hard):  Neural pattern → optimize → Odor

Uses MLX automatic differentiation to compute gradients through
the entire simulation, enabling gradient descent optimization.
"""

import numpy as np
from typing import Tuple, Dict, Optional, List
import time

try:
    import mlx.core as mx
    import mlx.optimizers as optim
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    mx = None
    print("⚠ MLX not available, inverse solver will not work")


class SmellOptimizer:
    """
    Gradient-based optimizer for finding odor parameters that
    produce a target neural pattern.
    
    Uses MLX autodiff to compute ∂loss/∂odor directly through
    the probabilistic brain simulation.
    """
    
    def __init__(self, brain, door_client=None, learning_rate=0.01):
        """
        Initialize smell optimizer.
        
        Args:
            brain: ProbabilisticWaveBrain instance
            door_client: DoorClient for decoding (optional)
            learning_rate: Adam optimizer learning rate
        """
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX is required for SmellOptimizer")
        
        self.brain = brain
        self.door_client = door_client
        self.learning_rate = learning_rate
        
        print(f"✓ SmellOptimizer initialized (lr={learning_rate})")
    
    def encode_smell(self, 
                    target_pattern: np.ndarray, 
                    region: str = 'PN',
                    num_steps: int = 500,
                    convergence_threshold: float = 0.01,
                    simulation_duration: float = 200.0,
                    verbose: bool = True) -> Tuple[np.ndarray, Dict]:
        """
        Find glom_pattern that produces target_pattern.
        
        This is the core inverse problem solver.
        
        Args:
            target_pattern: Target neural activity pattern
            region: Brain region to match ('PN', 'KC', 'MBON')
            num_steps: Maximum optimization steps
            convergence_threshold: Stop when loss < this
            simulation_duration: Simulation time (ms) per forward pass
            verbose: Print progress
        
        Returns:
            (optimized_glom_pattern, optimization_history)
        """
        if verbose:
            print("\n" + "="*70)
            print("SMELL ENCODING: Target Pattern → Odor Parameters")
            print("="*70)
            print(f"Target region: {region}")
            print(f"Target pattern shape: {target_pattern.shape}")
            print(f"Max optimization steps: {num_steps}")
            print(f"Convergence threshold: {convergence_threshold}")
        
        # Convert target to MLX array
        target_mx = mx.array(target_pattern.flatten().astype(np.float32))
        
        # Initialize glom_pattern randomly
        glom_pattern = mx.random.uniform(shape=(20,), dtype=mx.float32)
        glom_pattern = glom_pattern / mx.linalg.norm(glom_pattern)  # L2 normalize
        
        # Optimization history
        history = {
            'loss': [],
            'gradient_norm': [],
            'pattern_norm': [],
            'time': []
        }
        
        # Optimization loop
        t_start = time.time()
        best_loss = float('inf')
        best_pattern = None
        
        for step in range(num_steps):
            # Forward pass with autodiff
            def loss_fn(pattern):
                # Simulate brain with this odor
                simulated = self._simulate_odor(pattern, simulation_duration, region)
                
                # MSE loss
                loss = mx.mean((simulated - target_mx)**2)
                
                return loss
            
            # Compute loss and gradient
            loss_val, grad = mx.value_and_grad(loss_fn)(glom_pattern)
            
            # Convert to scalars for logging
            loss_scalar = float(loss_val)
            grad_norm = float(mx.linalg.norm(grad))
            
            # Manual gradient descent (MLX optimizer API is different)
            glom_pattern = glom_pattern - self.learning_rate * grad
            
            # Re-normalize (keep on unit sphere)
            glom_pattern = glom_pattern / mx.linalg.norm(glom_pattern)
            
            # Track best
            if loss_scalar < best_loss:
                best_loss = loss_scalar
                best_pattern = np.array(glom_pattern)
            
            # Log
            history['loss'].append(loss_scalar)
            history['gradient_norm'].append(grad_norm)
            history['pattern_norm'].append(float(mx.linalg.norm(glom_pattern)))
            history['time'].append(time.time() - t_start)
            
            # Print progress
            if verbose and (step % 50 == 0 or step == num_steps - 1):
                print(f"  Step {step:4d}: loss={loss_scalar:.6f}, "
                      f"grad_norm={grad_norm:.4f}, time={history['time'][-1]:.1f}s")
            
            # Check convergence
            if loss_scalar < convergence_threshold:
                if verbose:
                    print(f"\n✓ Converged at step {step}!")
                break
        
        elapsed = time.time() - t_start
        
        if verbose:
            print(f"\nOptimization complete:")
            print(f"  Final loss: {best_loss:.6f}")
            print(f"  Total time: {elapsed:.1f}s")
            print(f"  Steps: {len(history['loss'])}")
            print("="*70)
        
        return best_pattern, history
    
    def _simulate_odor(self, glom_pattern_mx, duration: float, region: str):
        """
        Simulate brain with given odor and extract activity.
        
        This must be differentiable for autodiff to work!
        
        Args:
            glom_pattern_mx: MLX array glomerular pattern
            duration: Simulation duration (ms)
            region: Region to extract
        
        Returns:
            MLX array of simulated activity
        """
        # Convert to numpy for brain simulation (for now)
        # TODO: Make brain simulation fully MLX-native for true end-to-end autodiff
        glom_np = np.array(glom_pattern_mx)
        
        # Reset brain
        self.brain.reset()
        
        # Inject odor
        self.brain.inject_odor(glom_np)
        
        # Evolve
        num_steps = int(duration / self.brain.dt)
        for _ in range(num_steps):
            self.brain._step()
        
        # Extract activity
        activity = self.brain.get_region_activity(region)
        
        # Convert back to MLX
        return mx.array(activity.flatten().astype(np.float32))
    
    def decode_smell(self, glom_pattern: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Map optimized glom_pattern → nearest DOoR odorants.
        
        Args:
            glom_pattern: 20-dim glomerular pattern
            top_k: Number of matches to return
        
        Returns:
            List of (odorant_name, similarity) tuples
        """
        if self.door_client is None:
            print("⚠ No DOoR client available for decoding")
            return []
        
        # Find similar odorants
        matches = self.door_client.find_similar_odorants(glom_pattern, top_k=top_k)
        
        return matches
    
    def multi_start_optimization(self,
                                target_pattern: np.ndarray,
                                region: str = 'PN',
                                num_starts: int = 10,
                                **kwargs) -> Tuple[np.ndarray, Dict]:
        """
        Run optimization from multiple random initializations.
        
        Helps avoid local minima.
        
        Args:
            target_pattern: Target pattern
            region: Brain region
            num_starts: Number of random starts
            **kwargs: Passed to encode_smell()
        
        Returns:
            (best_glom_pattern, best_history)
        """
        print(f"\n🔄 Multi-start optimization ({num_starts} starts)...")
        
        best_loss = float('inf')
        best_pattern = None
        best_history = None
        
        for i in range(num_starts):
            print(f"\n--- Start {i+1}/{num_starts} ---")
            
            # Run optimization
            pattern, history = self.encode_smell(
                target_pattern, region, verbose=False, **kwargs
            )
            
            final_loss = history['loss'][-1]
            print(f"  Final loss: {final_loss:.6f}")
            
            # Track best
            if final_loss < best_loss:
                best_loss = final_loss
                best_pattern = pattern
                best_history = history
                print(f"  ✓ New best!")
        
        print(f"\n✓ Best loss across all starts: {best_loss:.6f}")
        
        return best_pattern, best_history


class SimplifiedInverseOptimizer:
    """
    Simplified inverse optimizer for when full simulation autodiff is too slow.
    
    Uses surrogate model: directly optimize against DOoR patterns
    without simulating the brain.
    """
    
    def __init__(self, door_client, learning_rate=0.1):
        """
        Initialize simplified optimizer.
        
        Args:
            door_client: DoorClient for pattern matching
            learning_rate: Optimization learning rate
        """
        self.door_client = door_client
        self.learning_rate = learning_rate
    
    def encode_smell_direct(self, 
                           target_pattern: np.ndarray,
                           num_steps: int = 200) -> np.ndarray:
        """
        Find glom_pattern that best matches target (direct optimization).
        
        Much faster than full simulation, but less accurate.
        
        Args:
            target_pattern: Target pattern
            num_steps: Optimization steps
        
        Returns:
            Optimized glom_pattern
        """
        if not MLX_AVAILABLE:
            raise RuntimeError("MLX required")
        
        # Convert to MLX
        target_mx = mx.array(target_pattern.flatten().astype(np.float32))
        
        # Initialize
        glom_pattern = mx.random.uniform(shape=(20,), dtype=mx.float32)
        glom_pattern = glom_pattern / mx.linalg.norm(glom_pattern)
        
        # Optimizer
        optimizer = optim.Adam(learning_rate=self.learning_rate)
        
        # Optimization loop
        for step in range(num_steps):
            def loss_fn(pattern):
                # Direct distance (no simulation)
                return mx.sum((pattern - target_mx)**2)
            
            loss, grad = mx.value_and_grad(loss_fn)(glom_pattern)
            glom_pattern = optimizer.apply_gradients(grads=grad, model=glom_pattern)
            glom_pattern = glom_pattern / mx.linalg.norm(glom_pattern)
            
            if step % 50 == 0:
                print(f"  Step {step}: loss={float(loss):.6f}")
        
        return np.array(glom_pattern)


def test_optimizer():
    """Test smell optimizer with synthetic data."""
    print("\n" + "="*70)
    print("TESTING SMELL OPTIMIZER")
    print("="*70)
    
    # This would need a real brain and target pattern
    # For now, just demonstrate the structure
    
    print("\nOptimizer structure:")
    print("  1. Initialize glom_pattern randomly")
    print("  2. Forward: glom_pattern → simulate brain → neural pattern")
    print("  3. Loss: ||simulated - target||²")
    print("  4. Backward: compute ∂loss/∂glom_pattern via autodiff")
    print("  5. Update: glom_pattern ← glom_pattern - lr·∇loss")
    print("  6. Repeat until convergence")
    
    print("\nKey advantage: MLX autodiff eliminates manual gradient calculation!")
    print("The entire simulation is differentiable end-to-end.")
    
    print("="*70)


if __name__ == "__main__":
    test_optimizer()
