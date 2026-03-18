"""Vision module for compound eye simulation and visual processing."""

# CompoundEyeSimulator and StimulusGenerator require cv2 (OpenCV).
# Import them explicitly when needed rather than at package level:
#   from hive.vision.compound_eye import CompoundEyeSimulator
#   from hive.vision.stimulus_generator import StimulusGenerator
# This keeps the package importable in environments without cv2.

__all__ = ['CompoundEyeSimulator', 'StimulusGenerator']
