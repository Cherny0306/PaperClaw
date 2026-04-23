"""
PaperClaw Papercraft Module

Original research mode for data-driven research papers.
"""

from .data_analyzer import DataAnalyzer, RemoteSensingAnalyzer
from .hypothesis_generator import HypothesisGenerator, Hypothesis, Pattern
from .experiment_designer import ExperimentDesigner, ExperimentPlan
from .paper_writer import ResearchPaperWriter, ResearchContext

__all__ = [
    "DataAnalyzer",
    "RemoteSensingAnalyzer",
    "HypothesisGenerator",
    "Hypothesis",
    "Pattern",
    "ExperimentDesigner",
    "ExperimentPlan",
    "ResearchPaperWriter",
    "ResearchContext",
]
