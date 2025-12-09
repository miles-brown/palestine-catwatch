from .analyzer import process_image_ai
from .analysis_cache import AnalysisCache

# UniformAnalyzer requires anthropic package - only import if available
try:
    from .uniform_analyzer import UniformAnalyzer
    __all__ = ['process_image_ai', 'UniformAnalyzer', 'AnalysisCache']
except ImportError:
    # anthropic package not installed
    UniformAnalyzer = None
    __all__ = ['process_image_ai', 'AnalysisCache']
