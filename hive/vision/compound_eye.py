"""
Compound eye simulator for fly vision.
Simulates ~800 ommatidia with photoreceptors detecting motion in 4 directions.
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Ommatidium:
    """Single facet of compound eye."""
    index: int
    position: Tuple[float, float]  # Azimuth, elevation angles in degrees
    x_pixel: int  # X position in image space
    y_pixel: int  # Y position in image space
    direction_preference: Optional[str] = None  # 'front', 'back', 'upward', 'downward'


class CompoundEyeSimulator:
    """
    Simulates a fly's compound eye with ~800 ommatidia.
    Each ommatidium detects motion via optical flow.
    """
    
    def __init__(self, config: dict, sensory_motor_map):
        self.config = config['vision']['compound_eye']
        self.sm_map = sensory_motor_map
        
        # Compound eye parameters
        self.num_ommatidia = self.config['num_ommatidia']
        self.fov_h = self.config['field_of_view_h']  # degrees
        self.fov_v = self.config['field_of_view_v']  # degrees
        self.acceptance_angle = self.config['ommatidium_acceptance_angle']
        
        # Image processing parameters
        self.processing_config = config['vision']['processing']
        self.motion_threshold = self.processing_config['motion_threshold']
        self.flow_method = self.processing_config['optical_flow_method']
        self.smoothing_size = self.processing_config['spatial_smoothing']
        
        # Build ommatidi array
        self.ommatidia = self._create_ommatidia_array()
        
        # Map ommatidia to T4/T5 neurons
        self._build_retinotopic_map()
        
        # Previous frame for optical flow
        self.prev_frame = None
        self.frame_count = 0
        
        # Motion history for each direction
        self.motion_history = {
            'front': [],
            'back': [],
            'upward': [],
            'downward': []
        }
        
        print(f"Compound eye initialized: {len(self.ommatidia)} ommatidia")
        print(f"Visual motion neurons mapped:")
        for direction, neurons in self.sm_map.visual_motion.items():
            print(f"  {direction}: {len(neurons)} T4/T5 neurons")
    
    def _create_ommatidia_array(self) -> List[Ommatidium]:
        """
        Create hexagonal array of ommatidia covering the field of view.
        Higher density in frontal region (biologically accurate).
        """
        ommatidia = []
        
        # Calculate grid spacing
        # More ommatidia means denser packing
        h_steps = int(np.sqrt(self.num_ommatidia * (self.fov_h / self.fov_v)))
        v_steps = int(self.num_ommatidia / h_steps)
        
        # Angular spacing
        az_step = self.fov_h / h_steps
        el_step = self.fov_v / v_steps
        
        # Center on frontal view
        az_start = -self.fov_h / 2
        el_start = -self.fov_v / 2
        
        idx = 0
        for i in range(h_steps):
            for j in range(v_steps):
                # Hexagonal offset for alternating rows
                az_offset = (az_step / 2) if (j % 2 == 1) else 0
                
                azimuth = az_start + i * az_step + az_offset
                elevation = el_start + j * el_step
                
                # Higher density in frontal region (-45° to +45° azimuth)
                if abs(azimuth) < 45:
                    # Add extra ommatidia for foveal region
                    ommatidia.append(Ommatidium(
                        index=idx,
                        position=(azimuth, elevation),
                        x_pixel=0,  # Will be set during image processing
                        y_pixel=0
                    ))
                    idx += 1
                
                # Standard ommatidia for periphery
                ommatidia.append(Ommatidium(
                    index=idx,
                    position=(azimuth, elevation),
                    x_pixel=0,
                    y_pixel=0
                ))
                idx += 1
                
                if idx >= self.num_ommatidia:
                    break
            if idx >= self.num_ommatidia:
                break
        
        return ommatidia[:self.num_ommatidia]
    
    def _build_retinotopic_map(self):
        """
        Map ommatidia to T4/T5 neurons based on spatial position.
        T4/T5 neurons are organized retinotopically (visual space maps to brain space).
        """
        # Assign directional preference to ommatidia based on position
        for omm in self.ommatidia:
            az, el = omm.position
            
            # Determine primary motion direction based on visual field location
            # Front-preferring: frontal region
            # Back-preferring: peripheral/posterior
            # Upward/downward: based on elevation
            
            if abs(az) < 60:  # Frontal 120° arc
                if abs(el) < 30:
                    omm.direction_preference = 'front'
                elif el >= 30:
                    omm.direction_preference = 'upward'
                else:
                    omm.direction_preference = 'downward'
            else:  # Peripheral
                omm.direction_preference = 'back'
        
        # Count ommatidia per direction
        self.ommatidia_per_direction = {
            'front': len([o for o in self.ommatidia if o.direction_preference == 'front']),
            'back': len([o for o in self.ommatidia if o.direction_preference == 'back']),
            'upward': len([o for o in self.ommatidia if o.direction_preference == 'upward']),
            'downward': len([o for o in self.ommatidia if o.direction_preference == 'downward']),
        }
    
    def process_image(self, image: np.ndarray) -> Dict[str, np.ndarray]:
        """
        Process image through compound eye.
        
        Args:
            image: RGB image (H, W, 3) or grayscale (H, W)
        
        Returns:
            Dictionary with motion intensity per direction per ommatidium:
            {'front': [n_omm], 'back': [n_omm], 'upward': [n_omm], 'downward': [n_omm]}
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Resize to processing resolution (fly-scale vision)
        target_size = (100, 100)
        gray_resized = cv2.resize(gray, target_size)
        
        # Apply Gaussian blur (compound eye optics)
        blurred = cv2.GaussianBlur(
            gray_resized,
            (self.smoothing_size, self.smoothing_size),
            0
        )
        
        # Initialize motion arrays
        motion_by_direction = {
            'front': np.zeros(self.ommatidia_per_direction['front']),
            'back': np.zeros(self.ommatidia_per_direction['back']),
            'upward': np.zeros(self.ommatidia_per_direction['upward']),
            'downward': np.zeros(self.ommatidia_per_direction['downward']),
        }
        
        # Need previous frame for optical flow
        if self.prev_frame is None:
            self.prev_frame = blurred
            return motion_by_direction
        
        # Compute optical flow
        if self.flow_method == "farneback":
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_frame, blurred,
                None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )
        else:  # lucas-kanade
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_frame, blurred,
                None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )
        
        # Extract flow components
        flow_x = flow[..., 0]
        flow_y = flow[..., 1]
        
        # Sample flow at each ommatidium location
        h, w = blurred.shape
        
        direction_indices = {
            'front': 0,
            'back': 0,
            'upward': 0,
            'downward': 0
        }
        
        for omm in self.ommatidia:
            # Map ommatidium angle to pixel position
            az, el = omm.position
            
            # Convert spherical to pixel coordinates
            # Azimuth: -fov_h/2 to +fov_h/2 → 0 to w
            # Elevation: -fov_v/2 to +fov_v/2 → 0 to h
            x = int((az + self.fov_h / 2) / self.fov_h * w)
            y = int((el + self.fov_v / 2) / self.fov_v * h)
            
            # Clamp to image bounds
            x = np.clip(x, 0, w - 1)
            y = np.clip(y, 0, h - 1)
            
            # Sample optical flow at this location
            fx = flow_x[y, x]
            fy = flow_y[y, x]
            
            # Compute motion magnitude
            motion_mag = np.sqrt(fx**2 + fy**2)
            
            # Project motion onto preferred direction
            # Front/back: horizontal motion (fx)
            # Upward/downward: vertical motion (fy)
            
            direction = omm.direction_preference
            if direction == 'front':
                # Positive horizontal flow = forward motion
                projected_motion = max(0, fx) if fx > self.motion_threshold else 0
            elif direction == 'back':
                # Negative horizontal flow = backward motion
                projected_motion = max(0, -fx) if -fx > self.motion_threshold else 0
            elif direction == 'upward':
                # Negative vertical flow = upward motion (image coordinates)
                projected_motion = max(0, -fy) if -fy > self.motion_threshold else 0
            elif direction == 'downward':
                # Positive vertical flow = downward motion
                projected_motion = max(0, fy) if fy > self.motion_threshold else 0
            else:
                projected_motion = 0
            
            # Store in direction array
            idx = direction_indices[direction]
            motion_by_direction[direction][idx] = projected_motion
            direction_indices[direction] += 1
        
        # Update previous frame
        self.prev_frame = blurred
        self.frame_count += 1
        
        # Update motion history (for smoothing/adaptation)
        for direction in motion_by_direction:
            self.motion_history[direction].append(np.mean(motion_by_direction[direction]))
            if len(self.motion_history[direction]) > 20:
                self.motion_history[direction].pop(0)
        
        return motion_by_direction
    
    def get_visual_neuron_stimulation(
        self,
        motion_by_direction: Dict[str, np.ndarray]
    ) -> Dict[str, List[Tuple[int, float]]]:
        """
        Map ommatidium motion to T4/T5 neuron activation.
        
        Args:
            motion_by_direction: Motion arrays per direction
        
        Returns:
            Dictionary mapping direction to list of (neuron_id, force) tuples
        """
        neuron_forces = {
            'front': [],
            'back': [],
            'upward': [],
            'downward': []
        }
        
        for direction in ['front', 'back', 'upward', 'downward']:
            motion_array = motion_by_direction[direction]
            neuron_ids = self.sm_map.visual_motion[direction]
            
            if len(neuron_ids) == 0 or len(motion_array) == 0:
                continue
            
            # Distribute motion across available T4/T5 neurons
            # Each neuron gets input from a subset of ommatidia (retinotopic mapping)
            
            n_neurons = len(neuron_ids)
            n_ommatidia = len(motion_array)
            
            # Simple mapping: divide ommatidia into groups for each neuron
            ommatidia_per_neuron = max(1, n_ommatidia // n_neurons)
            
            for i, neuron_id in enumerate(neuron_ids):
                # Get ommatidia responsible for this neuron
                start_idx = i * ommatidia_per_neuron
                end_idx = min(start_idx + ommatidia_per_neuron, n_ommatidia)
                
                if start_idx >= n_ommatidia:
                    break
                
                # Average motion from assigned ommatidia
                omm_motion = motion_array[start_idx:end_idx]
                avg_motion = np.mean(omm_motion)
                
                if avg_motion > self.motion_threshold:
                    # Scale to forcing magnitude
                    force = avg_motion * 10.0  # Scaling factor
                    neuron_forces[direction].append((neuron_id, force))
        
        return neuron_forces
    
    def get_statistics(self) -> Dict:
        """Get compound eye processing statistics."""
        stats = {
            'frame_count': self.frame_count,
            'ommatidia_count': len(self.ommatidia),
            'mean_motion_by_direction': {}
        }
        
        for direction, history in self.motion_history.items():
            if history:
                stats['mean_motion_by_direction'][direction] = float(np.mean(history))
            else:
                stats['mean_motion_by_direction'][direction] = 0.0
        
        return stats
    
    def reset(self):
        """Reset visual system state."""
        self.prev_frame = None
        self.frame_count = 0
        self.motion_history = {k: [] for k in self.motion_history}
