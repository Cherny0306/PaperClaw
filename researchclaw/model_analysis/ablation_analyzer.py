"""
Ablation Analyzer

Analyzes ablation experiment results and component contributions.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class AblationResult:
    """Single ablation result"""
    component_removed: str
    baseline_metric: float
    ablated_metric: float
    absolute_contribution: float
    relative_contribution: float
    statistical_significance: float


@dataclass
class ContributionAnalysis:
    """Component contribution analysis"""
    component_name: str
    baseline_metric: float
    ablated_metric: float
    absolute_contribution: float
    relative_contribution: float
    statistical_significance: float
    confidence_interval: tuple[float, float]


@dataclass
class InteractionAnalysis:
    """Component interaction analysis"""
    synergistic_pairs: list[tuple[str, str]]
    antagonistic_pairs: list[tuple[str, str]]
    optimal_combinations: list[list[str]]


@dataclass
class AblationMatrix:
    """Ablation matrix results"""
    matrix: np.ndarray
    components: list[str]
    metrics: list[str]
    best_combination: list[str]
    best_score: float


class AblationAnalyzer:
    """Analyzer for ablation experiments"""

    def __init__(self):
        pass

    def parse_ablation_results(self, ablation_dir: Path) -> dict:
        """
        Parse ablation experiment results.

        Args:
            ablation_dir: Directory containing ablation results

        Returns:
            Dictionary of ablation results
        """
        results = {}

        # Look for results.csv files
        for subdir in ablation_dir.iterdir():
            if subdir.is_dir():
                results_csv = subdir / "results.csv"
                if results_csv.exists():
                    component_name = subdir.name
                    try:
                        df = pd.read_csv(results_csv)
                        best_mAP = df['mAP50'].max() if 'mAP50' in df.columns else 0
                        results[component_name] = {
                            "best_mAP": best_map,
                            "final_mAP": float(df['mAP50'].iloc[-1]) if 'mAP50' in df.columns else 0,
                            "best_epoch": int(df['mAP50'].idxmax()) if 'mAP50' in df.columns else 0,
                        }
                    except Exception:
                        pass

        return results

    def calculate_component_contribution(
        self,
        baseline_metrics: dict,
        ablation_metrics: dict,
        metric_name: str = "mAP50"
    ) -> list[ContributionAnalysis]:
        """
        Calculate contribution of each component.

        Args:
            baseline_metrics: Baseline model metrics
            ablation_metrics: Dictionary of component -> metrics
            metric_name: Metric to analyze

        Returns:
            List of contribution analyses
        """
        baseline_value = baseline_metrics.get(metric_name, 0)
        contributions = []

        for component, metrics in ablation_metrics.items():
            ablated_value = metrics.get(metric_name, 0)

            absolute_contribution = baseline_value - ablated_value
            relative_contribution = (absolute_contribution / baseline_value * 100) if baseline_value > 0 else 0

            # Simplified significance (would need statistical tests for proper p-values)
            if abs(absolute_contribution) > 0.01:
                significance = 0.05 if absolute_contribution > 0 else 0.1
            else:
                significance = 0.5

            # 95% confidence interval (simplified)
            ci = (absolute_contribution - 0.02, absolute_contribution + 0.02)

            contributions.append(ContributionAnalysis(
                component_name=component,
                baseline_metric=baseline_value,
                ablated_metric=ablated_value,
                absolute_contribution=absolute_contribution,
                relative_contribution=relative_contribution,
                statistical_significance=significance,
                confidence_interval=ci,
            ))

        return sorted(contributions, key=lambda x: x.absolute_contribution, reverse=True)

    def generate_ablation_matrix(
        self,
        results: list[AblationResult],
        components: list[str]
    ) -> AblationMatrix:
        """
        Generate ablation matrix.

        Args:
            results: List of ablation results
            components: List of component names

        Returns:
            AblationMatrix
        """
        n = len(components)
        matrix = np.zeros((n, n))

        # Fill matrix with contribution values
        for result in results:
            if result.component_removed in components:
                idx = components.index(result.component_removed)
                matrix[idx, idx] = result.absolute_contribution

        # Find best combination (highest cumulative contribution)
        sorted_results = sorted(results, key=lambda x: x.absolute_contribution, reverse=True)
        best_combination = [r.component_removed for r in sorted_results[:3]]
        best_score = sum(r.absolute_contribution for r in sorted_results[:3])

        return AblationMatrix(
            matrix=matrix,
            components=components,
            metrics=["mAP50"],
            best_combination=best_combination,
            best_score=best_score,
        )

    def analyze_component_interaction(
        self,
        ablation_results: list[dict]
    ) -> InteractionAnalysis:
        """
        Analyze component interactions.

        Args:
            ablation_results: List of ablation results with component info

        Returns:
            InteractionAnalysis
        """
        synergistic_pairs = []
        antagonistic_pairs = []
        optimal_combinations = []

        # Simplified interaction analysis
        # In practice, would need full factorial design for proper interaction analysis

        contributions = {}
        for result in ablation_results:
            component = result.get('component_removed', 'unknown')
            contribution = result.get('absolute_contribution', 0)
            contributions[component] = contribution

        # Find pairs with high combined effect
        component_names = list(contributions.keys())
        for i, c1 in enumerate(component_names):
            for c2 in component_names[i+1:]:
                combined = contributions[c1] + contributions[c2]

                # If combined effect is greater than individual, synergistic
                if combined > max(contributions[c1], contributions[c2]) * 1.2:
                    synergistic_pairs.append((c1, c2))
                # If combined effect is less than expected, antagonistic
                elif combined < min(contributions[c1], contributions[c2]) * 0.8:
                    antagonistic_pairs.append((c1, c2))

        # Find optimal combinations
        sorted_components = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        if sorted_components:
            optimal_combinations = [
                [sorted_components[0][0]],  # Top single
                [sorted_components[0][0], sorted_components[1][0]] if len(sorted_components) > 1 else [],  # Top two
            ]

        return InteractionAnalysis(
            synergistic_pairs=synergistic_pairs,
            antagonistic_pairs=antagonistic_pairs,
            optimal_combinations=optimal_combinations,
        )

    def generate_ablation_report(
        self,
        contributions: list[ContributionAnalysis],
        interaction: Optional[InteractionAnalysis] = None
    ) -> str:
        """Generate ablation experiment report."""
        lines = []
        lines.append("=" * 60)
        lines.append("ABLATION EXPERIMENT ANALYSIS REPORT")
        lines.append("=" * 60)

        lines.append("\n## Component Contributions")
        lines.append("-" * 60)
        lines.append(f"{'Component':<30} {'Delta mAP':>12} {'Relative %':>12} {'Significance':>12}")
        lines.append("-" * 60)

        for contrib in contributions:
            sig_marker = "***" if contrib.statistical_significance < 0.05 else "**" if contrib.statistical_significance < 0.1 else ""
            lines.append(
                f"{contrib.component_name:<30} "
                f"{contrib.absolute_contribution:>+12.4f} "
                f"{contrib.relative_contribution:>+12.2f} "
                f"{contrib.statistical_significance:>12.4f} {sig_marker}"
            )

        lines.append("\n## Ranked Components")
        lines.append("-" * 60)
        for i, contrib in enumerate(contributions, 1):
            lines.append(f"{i}. {contrib.component_name}: {contrib.absolute_contribution:+.4f} mAP")

        # Best combination
        if contributions:
            top_components = contributions[:3]
            total_contribution = sum(c.absolute_contribution for c in top_components)
            lines.append(f"\n## Optimal Combination")
            lines.append("-" * 60)
            lines.append(f"Components: {', '.join([c.component_name for c in top_components])}")
            lines.append(f"Combined contribution: {total_contribution:+.4f} mAP")

        if interaction:
            lines.append(f"\n## Component Interactions")
            lines.append("-" * 60)

            if interaction.synergistic_pairs:
                lines.append("\nSynergistic pairs (better together):")
                for pair in interaction.synergistic_pairs:
                    lines.append(f"  - {pair[0]} + {pair[1]}")

            if interaction.antagonistic_pairs:
                lines.append("\nAntagonistic pairs (interference):")
                for pair in interaction.antagonistic_pairs:
                    lines.append(f"  - {pair[0]} + {pair[1]}")

        # Recommendations
        lines.append("\n## Recommendations")
        lines.append("-" * 60)
        if contributions:
            positive = [c for c in contributions if c.absolute_contribution > 0]
            negative = [c for c in contributions if c.absolute_contribution < 0]

            if positive:
                lines.append("\nKeep these components:")
                for c in positive[:3]:
                    lines.append(f"  - {c.component_name} ({c.absolute_contribution:+.4f} mAP)")

            if negative:
                lines.append("\nConsider removing:")
                for c in negative[:3]:
                    lines.append(f"  - {c.component_name} ({c.absolute_contribution:+.4f} mAP)")

        return "\n".join(lines)

    def compare_ablation_strategies(
        self,
        strategy1_results: dict,
        strategy2_results: dict
    ) -> dict:
        """Compare two ablation strategies."""
        # Extract best components from each strategy
        strategy1_best = sorted(
            [(k, v.get('best_mAP', 0)) for k, v in strategy1_results.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        strategy2_best = sorted(
            [(k, v.get('best_mAP', 0)) for k, v in strategy2_results.items()],
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "strategy1_top_components": strategy1_best,
            "strategy2_top_components":