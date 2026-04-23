"""
PaperClaw Model Analysis Module

Analysis tools for deep learning model training results (YOLO, MIE-YOLO, etc.)
"""

from .base import ModelDataParser, ModelData
from .yolo_analyzer import YOLOAnalyzer, TrainingResults, DetectionMetrics
from .mie_yolo_analyzer import MIEYOLOAnalyzer, MultispectralAnalysis, RemoteSensingMetrics
from .detector_analyzer import DetectorAnalyzer
from .classifier_analyzer import ClassifierAnalyzer
from .metrics_calculator import MetricsCalculator
from .augmentation_analyzer import DataAugmentationAnalyzer, AugmentationConfig
from .inference_speed_analyzer import InferenceSpeedAnalyzer, SpeedMetrics, EfficiencyMetrics
from .ablation_analyzer import AblationAnalyzer, AblationResult, ContributionAnalysis
from .visualizer import ModelVisualizer

__all__ = [
    # Base
    "ModelDataParser",
    "ModelData",
    # YOLO
    "YOLOAnalyzer",
    "TrainingResults",
    "DetectionMetrics",
    # MIE-YOLO
    "MIEYOLOAnalyzer",
    "MultispectralAnalysis",
    "RemoteSensingMetrics",
    # Other analyzers
    "DetectorAnalyzer",
    "ClassifierAnalyzer",
    "MetricsCalculator",
    # Analysis tools
    "DataAugmentationAnalyzer",
    "AugmentationConfig",
    "InferenceSpeedAnalyzer",
    "SpeedMetrics",
    "EfficiencyMetrics",
    "AblationAnalyzer",
    "AblationResult",
    "ContributionAnalysis",
    # Visualization
    "ModelVisualizer",
]
