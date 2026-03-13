"""Initialize patterns package."""
from .thought_patterns import ThoughtPatternDetector, ThoughtPattern
from .pattern_completion import PatternCompletion, CompletionCandidate
from .advanced_patterns import (
    PatternComposition,
    ThoughtChainTracker,
    PatternInhibition,
    MetaCognition,
    PatternLanguage,
    AdvancedPatternSystem
)

__all__ = [
    'ThoughtPatternDetector',
    'ThoughtPattern',
    'PatternCompletion',
    'CompletionCandidate',
    'PatternComposition',
    'ThoughtChainTracker',
    'PatternInhibition',
    'MetaCognition',
    'PatternLanguage',
    'AdvancedPatternSystem'
]
