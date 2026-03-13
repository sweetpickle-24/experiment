"""
Visual stimulus generator for fly brain experiments.
Loads images and generates synthetic motion patterns.
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, List, Dict, Optional
import json
import random


class StimulusGenerator:
    """
    Generates and manages visual stimuli for the fly brain.
    Supports loading images from disk and generating synthetic patterns.
    """
    
    def __init__(self, stimulus_dir: str = "data/stimuli", config: Optional[dict] = None):
        self.stimulus_dir = Path(stimulus_dir)
        
        # Configuration
        if config and 'vision' in config and 'stimulus' in config['vision']:
            stim_config = config['vision']['stimulus']
            self.frame_rate = stim_config['frame_rate']
            self.stimulus_duration = stim_config['stimulus_duration']  # ms
            self.inter_stimulus_interval = stim_config['inter_stimulus_interval']  # ms
            self.randomize = stim_config['randomize']
        else:
            # Defaults
            self.frame_rate = 200  # Hz
            self.stimulus_duration = 200  # ms
            self.inter_stimulus_interval = 100  # ms
            self.randomize = True
        
        # Calculate frame counts
        self.frames_per_stimulus = int(self.stimulus_duration * self.frame_rate / 1000)
        self.frames_per_isi = int(self.inter_stimulus_interval * self.frame_rate / 1000)
        
        # Load stimulus library
        self.stimuli = self._load_stimuli()
        
        # Current state
        self.current_stimulus = None
        self.current_label = "blank"
        self.current_frame = 0
        self.total_frames = 0
        self.stimulus_index = 0
        self.in_isi = False
        
        # Blank frame (gray)
        self.blank_frame = np.ones((100, 100), dtype=np.uint8) * 127
        
        print(f"Stimulus generator initialized:")
        print(f"  {len(self.stimuli)} stimuli loaded")
        print(f"  {self.frames_per_stimulus} frames per stimulus")
        print(f"  {self.frames_per_isi} frames ISI")
    
    def _load_stimuli(self) -> List[Dict]:
        """Load stimulus images and metadata from disk."""
        stimuli = []
        
        if not self.stimulus_dir.exists():
            print(f"Warning: Stimulus directory {self.stimulus_dir} not found")
            print("Generating synthetic stimuli only")
            return self._generate_default_stimuli()
        
        # Load metadata if available
        metadata_path = self.stimulus_dir / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # Scan for images in subdirectories
        for category_dir in self.stimulus_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            category = category_dir.name
            
            for img_path in category_dir.glob("*.png"):
                stimuli.append({
                    'type': 'image',
                    'category': category,
                    'path': img_path,
                    'label': f"{category}_{img_path.stem}",
                    'metadata': metadata.get(img_path.name, {})
                })
            
            for img_path in category_dir.glob("*.jpg"):
                stimuli.append({
                    'type': 'image',
                    'category': category,
                    'path': img_path,
                    'label': f"{category}_{img_path.stem}",
                    'metadata': metadata.get(img_path.name, {})
                })
        
        if len(stimuli) == 0:
            print("No image stimuli found, using synthetic stimuli")
            return self._generate_default_stimuli()
        
        return stimuli
    
    def _generate_default_stimuli(self) -> List[Dict]:
        """Generate default synthetic stimuli when no images available."""
        stimuli = []
        
        # Add synthetic patterns
        for direction in ['front', 'back', 'upward', 'downward']:
            for speed in [1, 2, 5]:
                stimuli.append({
                    'type': 'grating',
                    'category': 'patterns',
                    'label': f'grating_{direction}_{speed}',
                    'direction': direction,
                    'speed': speed
                })
        
        # Add looming stimuli
        for rate in [0.05, 0.1, 0.2]:
            stimuli.append({
                'type': 'looming',
                'category': 'patterns',
                'label': f'loom_{int(rate*100)}',
                'expansion_rate': rate
            })
        
        return stimuli
    
    def get_next_stimulus(self) -> Tuple[np.ndarray, str]:
        """
        Get next stimulus frame.
        
        Returns:
            (image, label) tuple where image is grayscale (H, W) and label is string
        """
        self.total_frames += 1
        
        # During ISI, return blank
        if self.in_isi:
            self.current_frame += 1
            if self.current_frame >= self.frames_per_isi:
                self.in_isi = False
                self.current_frame = 0
                self._select_next_stimulus()
            return self.blank_frame.copy(), "blank"
        
        # Generate stimulus frame
        self.current_frame += 1
        
        if self.current_frame >= self.frames_per_stimulus:
            # Stimulus presentation complete, enter ISI
            self.in_isi = True
            self.current_frame = 0
            return self.blank_frame.copy(), "blank"
        
        # Generate current stimulus
        frame = self._generate_stimulus_frame()
        return frame, self.current_label
    
    def _select_next_stimulus(self):
        """Select the next stimulus to present."""
        if self.randomize:
            self.stimulus_index = random.randint(0, len(self.stimuli) - 1)
        else:
            self.stimulus_index = (self.stimulus_index + 1) % len(self.stimuli)
        
        self.current_stimulus = self.stimuli[self.stimulus_index]
        self.current_label = self.current_stimulus['label']
        self.current_frame = 0
    
    def _generate_stimulus_frame(self) -> np.ndarray:
        """Generate the current frame of the current stimulus."""
        if self.current_stimulus is None:
            self._select_next_stimulus()
        
        stim = self.current_stimulus
        
        if stim['type'] == 'image':
            # Load and return image
            return self._load_image(stim['path'])
        
        elif stim['type'] == 'grating':
            # Generate drifting grating
            return self.create_drifting_grating(
                stim['direction'],
                stim['speed'],
                self.current_frame
            )
        
        elif stim['type'] == 'looming':
            # Generate looming circle
            return self.create_looming_stimulus(
                stim['expansion_rate'],
                self.current_frame,
                self.frames_per_stimulus
            )
        
        else:
            return self.blank_frame.copy()
    
    def _load_image(self, path: Path) -> np.ndarray:
        """Load image from disk and convert to grayscale."""
        img = cv2.imread(str(path))
        if img is None:
            print(f"Warning: Failed to load image {path}")
            return self.blank_frame.copy()
        
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Resize to standard size
        resized = cv2.resize(gray, (100, 100))
        return resized
    
    def create_drifting_grating(
        self,
        direction: str,
        speed: float,
        frame: int
    ) -> np.ndarray:
        """
        Generate drifting sinusoidal grating.
        
        Args:
            direction: 'front', 'back', 'upward', 'downward'
            speed: drift speed in pixels/frame
            frame: current frame number
        
        Returns:
            Grayscale image (100, 100)
        """
        size = 100
        img = np.zeros((size, size), dtype=np.uint8)
        
        # Spatial frequency (cycles per image)
        frequency = 5
        
        # Phase offset based on frame and speed
        phase = frame * speed * 2 * np.pi / size
        
        # Create sinusoidal grating
        if direction in ['front', 'back']:
            # Horizontal grating (vertical bars)
            for x in range(size):
                value = 127 + 127 * np.sin(2 * np.pi * frequency * x / size + phase)
                img[:, x] = np.clip(value, 0, 255)
            
            # Reverse phase for backward motion
            if direction == 'back':
                img = np.fliplr(img)
        
        else:  # upward, downward
            # Vertical grating (horizontal bars)
            for y in range(size):
                value = 127 + 127 * np.sin(2 * np.pi * frequency * y / size + phase)
                img[y, :] = np.clip(value, 0, 255)
            
            # Reverse phase for downward motion
            if direction == 'downward':
                img = np.flipud(img)
        
        return img
    
    def create_looming_stimulus(
        self,
        expansion_rate: float,
        frame: int,
        total_frames: int
    ) -> np.ndarray:
        """
        Generate expanding circle (simulates approaching object).
        
        Args:
            expansion_rate: how fast circle expands (0-1)
            frame: current frame
            total_frames: total frames in stimulus
        
        Returns:
            Grayscale image (100, 100)
        """
        size = 100
        img = np.ones((size, size), dtype=np.uint8) * 127  # Gray background
        
        # Calculate radius based on frame
        progress = frame / max(1, total_frames - 1)
        max_radius = size // 2
        radius = int(max_radius * progress * expansion_rate * 5)
        radius = min(radius, max_radius)
        
        # Draw expanding circle (dark on gray)
        center = (size // 2, size // 2)
        cv2.circle(img, center, radius, 0, -1)  # Filled black circle
        
        return img
    
    def create_flickering_pattern(self, frame: int) -> np.ndarray:
        """Generate flickering pattern (alternating light/dark)."""
        size = 100
        if (frame // 2) % 2 == 0:
            return np.ones((size, size), dtype=np.uint8) * 200
        else:
            return np.ones((size, size), dtype=np.uint8) * 50
    
    def get_current_label(self) -> str:
        """Get label of current stimulus."""
        return self.current_label
    
    def get_statistics(self) -> Dict:
        """Get stimulus generation statistics."""
        return {
            'total_frames': self.total_frames,
            'current_label': self.current_label,
            'current_frame': self.current_frame,
            'in_isi': self.in_isi,
            'num_stimuli': len(self.stimuli)
        }
    
    def reset(self):
        """Reset stimulus generator state."""
        self.current_stimulus = None
        self.current_label = "blank"
        self.current_frame = 0
        self.total_frames = 0
        self.stimulus_index = 0
        self.in_isi = False
    
    def get_statistics(self) -> Dict:
        """Return current stimulus generator statistics."""
        return {
            'total_stimuli_available': len(self.stimuli),
            'frames_delivered': self.total_frames,
            'current_stimulus_index': self.stimulus_index,
            'frame_rate': self.frame_rate,
            'stimulus_duration_ms': self.stimulus_duration,
            'isi_duration_ms': self.inter_stimulus_interval
        }
