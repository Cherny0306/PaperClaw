"""
Analysis Service

Handles data analysis, model analysis, and hypothesis generation.
"""

from pathlib import Path
from typing import Any, Optional, Union
import pandas as pd
import numpy as np

from researchclaw.papercraft import DataAnalyzer, HypothesisGenerator
from researchclaw.model_analysis import (
    YOLOAnalyzer, MIEYOLOAnalyzer, ResultAnalyzer,
    DataAugmentationAnalyzer, InferenceSpeedAnalyzer, AblationAnalyzer
)


class AnalysisService:
    """Service for handling analysis operations"""

    def __init__(self):
        self.data_analyzer = DataAnalyzer()
        self.hypothesis_generator = HypothesisGenerator()
        self.yolo_analyzer = YOLOAnalyzer()
        self.mie_yolo_analyzer = MIEYOLOAnalyzer()
        self.augmentation_analyzer = DataAugmentationAnalyzer()
        self.speed_analyzer = InferenceSpeedAnalyzer()
        self.ablation_analyzer = AblationAnalyzer()

    def analyze_results(self, results_file: str, model_type: str = "yolo") -> dict:
        """
        Analyze existing model training results.

        Args:
            results_file: Path or content to results file
            model_type: Type of model (yolo, mie_yolo, etc.)

        Returns:
            Analysis results
        """
        try:
            # Determine analyzer based on model type
            if model_type == "mie_yolo":
                analyzer = self.mie_yolo_analyzer
            else:
                analyzer = self.yolo_analyzer

            # Check if it's a directory or file
            if isinstance(results_file, (str, Path)) and Path(results_file).is_dir():
                results_dir = Path(results_file)
                training_results = analyzer.parse_training_results(results_dir)

                return {
                    "success": True,
                    "model_type": model_type,
                    "training_summary": training_results.summary(),
                    "best_epoch": training_results.best_epoch,
                    "best_mAP50": training_results.best_mAP50,
                    "curves": {
                        "epochs": training_results.epochs,
                        "mAP50": training_results.mAP50,
                        "mAP50_95": training_results.mAP50_95,
                        "precision": training_results.precision,
                        "recall": training_results.recall,
                    }
                }
            else:
                return {"success": False, "error": "Invalid results path"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def compare_models(self, results_dirs: list[dict]) -> dict:
        """
        Compare multiple model results.

        Args:
            results_dirs: List of dicts with 'name' and 'path' keys

        Returns:
            Comparison results
        """
        try:
            comparisons = []

            for result in results_dirs:
                name = result.get("name", "Unknown")
                path = result.get("path", "")

                try:
                    training_results = self.yolo_analyzer.parse_training_results(Path(path))
                    comparisons.append({
                        "name": name,
                        "summary": training_results.summary(),
                    })
                except Exception as e:
                    comparisons.append({
                        "name": name,
                        "error": str(e),
                    })

            # Sort by mAP50
            valid_comparisons = [c for c in comparisons if "summary" in c]
            if valid_comparisons:
                sorted_comparisons = sorted(
                    valid_comparisons,
                    key=lambda x: x["summary"].get("best_mAP50", 0),
                    reverse=True
                )
                winner = sorted_comparisons[0]["name"]
            else:
                sorted_comparisons = comparisons
                winner = None

            return {
                "success": True,
                "comparisons": sorted_comparisons,
                "winner": winner,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_augmentation(self, results_dir: Path) -> dict:
        """Analyze data augmentation effects."""
        try:
            args_yaml = results_dir / "args.yaml"
            results_csv = results_dir / "results.csv"

            if not args_yaml.exists() or not results_csv.exists():
                return {"success": False, "error": "Required files not found"}

            # Parse augmentation config
            aug_config = self.augmentation_analyzer.parse_augmentation_config(args_yaml)

            # Parse training results
            df = pd.read_csv(results_csv)

            # Analyze effects
            effects = self.augmentation_analyzer.analyze_augmentation_effects(df, aug_config)

            return {
                "success": True,
                "config": {
                    "flip_horizontal": aug_config.flip_horizontal,
                    "flip_vertical": aug_config.flip_vertical,
                    "rotation_degrees": aug_config.rotation_degrees,
                    "mosaic": aug_config.mosaic,
                    "mixup": aug_config.mixup,
                    "color_jitter": aug_config.color_jitter,
                },
                "effects": [
                    {
                        "augmentation": e.augmentation,
                        "delta_map": e.delta_map,
                        "significance": e.significance,
                        "recommendation": e.recommendation,
                    }
                    for e in effects.values()
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_ablation(self, baseline_dir: Path, ablated_dirs: list[dict]) -> dict:
        """Analyze ablation experiment results."""
        try:
            # Parse baseline
            baseline_csv = baseline_dir / "results.csv"
            if baseline_csv.exists():
                df_baseline = pd.read_csv(baseline_csv)
                baseline_metrics = {
                    "mAP50": float(df_baseline['mAP50'].max()) if 'mAP50' in df_baseline.columns else 0
                }
            else:
                return {"success": False, "error": "Baseline results.csv not found"}

            # Parse ablation results
            ablation_metrics = {}
            for ablated in ablated_dirs:
                name = ablated.get("name", "Unknown")
                path = ablated.get("path", "")

                results_csv = Path(path) / "results.csv"
                if results_csv.exists():
                    df = pd.read_csv(results_csv)
                    ablation_metrics[name] = {
                        "mAP50": float(df['mAP50'].max()) if 'mAP50' in df.columns else 0
                    }

            # Calculate contributions
            contributions = self.ablation_analyzer.calculate_component_contribution(
                baseline_metrics, ablation_metrics, "mAP50"
            )

            return {
                "success": True,
                "baseline_mAP50": baseline_metrics["mAP50"],
                "contributions": [
                    {
                        "component": c.component_name,
                        "absolute_contribution": c.absolute_contribution,
                        "relative_contribution": c.relative_contribution,
                        "significance": c.statistical_significance,
                    }
                    for c in contributions
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_data(self, data: Union[pd.DataFrame, list[dict]]) -> dict:
        """Analyze tabular data."""
        try:
            # Convert to DataFrame if needed
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            # Calculate descriptive statistics
            stats = self.data_analyzer.descriptive_stats(df)

            # Calculate correlations
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                corr_result = self.data_analyzer.correlation_analysis(df, numeric_cols)
                correlations = corr_result.significant_pairs
            else:
                correlations = []

            # Detect outliers
            df_with_outliers = self.data_analyzer.detect_anomalies(df)
            outlier_count = int(df_with_outliers["is_anomaly"].sum())

            return {
                "success": True,
                "shape": df.shape,
                "descriptive_stats": {
                    col: {
                        "mean": s.mean,
                        "median": s.median,
                        "std": s.std,
                        "min": s.min,
                        "max": s.max,
                    }
                    for col, s in stats.items()
                },
                "correlations": correlations[:10],  # Top 10
                "outlier_count": outlier_count,
                "column_types": df.dtypes.astype(str).to_dict(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_hypotheses(self, data: Union[pd.DataFrame, list[dict]], domain: str = "general") -> dict:
        """Generate research hypotheses from data."""
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data

            # Analyze data first
            analysis_results = {
                "correlations": {"significant_pairs": []},
            }

            # Discover patterns
            patterns = self.hypothesis_generator.discover_patterns(df, analysis_results)

            # Generate research questions
            questions = self.hypothesis_generator.generate_research_questions(patterns, domain)

            # Formulate hypotheses
            hypotheses = self.hypothesis_generator.formulate_hypotheses(questions, domain)

            # Prioritize
            hypotheses = self.hypothesis_generator.prioritize_hypotheses(hypotheses)

            return {
                "success": True,
                "patterns": [
                    {
                        "id": p.id,
                        "type": p.pattern_type.value,
                        "description": p.description,
                        "significance": p.significance,
                    }
                    for p in patterns
                ],
                "questions": questions[:10],
                "hypotheses": [
                    {
                        "id": h.id,
                        "question": h.question,
                        "null_hypothesis": h.null_hypothesis,
                        "alternative_hypothesis": h.alternative_hypothesis,
                        "test_method": h.test_method,
                        "novelty_score": h.novelty_score,
                        "feasibility_score": h.feasibility_score,
                    }
                    for h in hypotheses[:10]
                ]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# Global service instance
analysis_service = AnalysisService()
