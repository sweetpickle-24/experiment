"""Vision module for compound eye simulation and visual processing."""

try:
    from .compound_eye import CompoundEyeSimulator
    from .stimulus_generator import StimulusGenerator
except ImportError:
    # cv2 / OpenCV not available — provide stub classes so the rest of the
    # codebase can still import from this package without crashing.
    class CompoundEyeSimulator:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass
        def get_visual_neuron_stimulation(self, *args, **kwargs):
            return {}

    class StimulusGenerator:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

__all__ = ['CompoundEyeSimulator', 'StimulusGenerator']
