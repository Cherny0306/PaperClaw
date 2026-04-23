"""
Experiment Designer Module

Designs experiments based on hypotheses.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np


@dataclass
class ExperimentPlan:
    """Experiment design plan"""
    id: str
    name: str
    description: str
    hypothesis_id: str
    design_type: str
    variables: dict[str, Any]
    sample_size: int
    power_analysis: dict
    timeline: list[dict]
    resources: dict[str, Any]
    risk_mitigation: list[str]


@dataclass
class AblationPlan:
    """Ablation study plan"""
    baseline_id: str
    components: list[str]
    removal_order: list[str]
    evaluation_metrics: list[str]
    expected_contributions: dict[str, float]


@dataclass
class SampleSizeResult:
    """Sample size calculation result"""
    n: int
    effect_size: float
    alpha: float
    power: float
    test_type: str
    method: str
    notes: str = ""


class ExperimentDesigner:
    """Design experiments based on hypotheses"""

    def __init__(self):
        pass

    def design_comparative_experiment(
        self,
        hypothesis: Any,
        groups: list[str],
        control_group: Optional[str] = None,
        randomize: bool = True,
        blind: bool = False
    ) -> ExperimentPlan:
        """
        Design a comparative experiment.
        """
        design_type = "comparative"
        if control_group:
            design_type = "controlled_trial"

        variables = {
            "independent": [],
            "dependent": [],
            "controlled": [],
        }

        if hasattr(hypothesis, 'variables'):
            for var in hypothesis.variables:
                if var.type == "independent":
                    variables["independent"].append(var.name)
                elif var.type == "dependent":
                    variables["dependent"].append(var.name)
                elif var.type == "controlled":
                    variables["controlled"].append(var.name)

        timeline = [
            {"phase": "preparation", "duration": "1 week", "tasks": ["materials", "IRB approval"]},
            {"phase": "recruitment", "duration": "2-4 weeks", "tasks": ["participant selection", "consent"]},
            {"phase": "baseline", "duration": "1 week", "tasks": ["pre-assessment"]},
            {"phase": "intervention", "duration": "4-8 weeks", "tasks": ["treatment", "monitoring"]},
            {"phase": "follow_up", "duration": "2-4 weeks", "tasks": ["post-assessment", "data collection"]},
            {"phase": "analysis", "duration": "2 weeks", "tasks": ["data cleaning", "statistical analysis"]},
        ]

        resources = {
            "personnel": ["PI", "Research Assistants"],
            "equipment": [],
            "budget_estimate": "TBD",
            "participants_needed": sum([100] * len(groups)),
        }

        return ExperimentPlan(
            id=f"exp_{hash(hypothesis.question) % 10000}",
            name=f"Comparative Study: {groups[0]} vs {groups[1]}" if len(groups) == 2 else "Comparative Study",
            description=f"Comparative experiment to test {hypothesis.question}",
            hypothesis_id=hypothesis.id if hasattr(hypothesis, 'id') else "unknown",
            design_type=design_type,
            variables=variables,
            sample_size=100,
            power_analysis={"power": 0.8, "alpha": 0.05},
            timeline=timeline,
            resources=resources,
            risk_mitigation=["Data backup", "Protocol deviations monitoring"],
        )

    def design_ablation_study(
        self,
        baseline_components: list[str],
        evaluation_metrics: list[str],
        removal_strategy: str = "sequential"
    ) -> AblationPlan:
        """
        Design an ablation study.
        """
        if removal_strategy == "sequential":
            removal_order = baseline_components
        elif removal_strategy == "random":
            removal_order = list(baseline_components)
            np.random.shuffle(removal_order)
        else:
            removal_order = baseline_components

        return AblationPlan(
            baseline_id="baseline",
            components=baseline_components,
            removal_order=removal_order,
            evaluation_metrics=evaluation_metrics,
            expected_contributions={comp: 0.5 for comp in baseline_components},
        )

    def calculate_sample_size(
        self,
        effect_size: float,
        power: float = 0.8,
        alpha: float = 0.05,
        test_type: str = "two_sample_ttest"
    ) -> SampleSizeResult:
        """
        Calculate required sample size using power analysis.
        """
        from scipy.stats import norm

        if test_type in ["two_sample_ttest", "anova"]:
            z_alpha = norm.ppf(1 - alpha / 2)
            z_beta = norm.ppf(power)
            n_per_group = 2 * ((z_alpha + z_beta) / effect_size) ** 2
            n = int(np.ceil(n_per_group))
            method = "Cohen's formula for two-sample t-test"

        elif test_type == "paired_ttest":
            z_alpha = norm.ppf(1 - alpha / 2)
            z_beta = norm.ppf(power)
            n = int(np.ceil(((z_alpha + z_beta) / effect_size) ** 2))
            method = "Cohen's formula for paired t-test"

        elif test_type == "correlation":
            z_alpha = norm.ppf(1 - alpha / 2)
            z_beta = norm.ppf(power)
            n = int(np.ceil(((z_alpha + z_beta) / (0.5 * np.log((1 + effect_size) / (1 - effect_size)))) ** 2 + 3))
            method = "Fisher's z transformation for correlation"

        elif test_type == "chi_square":
            from scipy.stats import chi2
            df = 1
            n = int(np.ceil(chi2.ppf(1 - alpha, df) / effect_size + 1))
            method = "Chi-square test formula"

        else:
            n = 100
            method = "Default (conservative estimate)"

        return SampleSizeResult(
            n=n,
            effect_size=effect_size,
            alpha=alpha,
            power=power,
            test_type=test_type,
            method=method,
            notes=f"Based on {method}"
        )

    def generate_experiment_protocol(
        self,
        plan: ExperimentPlan,
        include_randomization: bool = True,
        include_blinding: bool = True
    ) -> str:
        """
        Generate detailed experiment protocol document.
        """
        lines = []
        lines.append("# Experiment Protocol")
        lines.append("=" * 60)
        lines.append(f"\n**Protocol ID**: {plan.id}")
        lines.append(f"**Name**: {plan.name}")
        lines.append(f"**Design Type**: {plan.design_type}")
        lines.append(f"**Hypothesis**: {plan.hypothesis_id}")

        lines.append("\n## 1. Objectives")
        lines.append(f"\n{plan.description}")

        lines.append("\n## 2. Variables")
        lines.append("\n### 2.1 Independent Variables")
        for var in plan.variables.get("independent", []):
            lines.append(f"- {var}")

        lines.append("\n### 2.2 Dependent Variables")
        for var in plan.variables.get("dependent", []):
            lines.append(f"- {var}")

        lines.append("\n### 2.3 Controlled Variables")
        for var in plan.variables.get("controlled", []):
            lines.append(f"- {var}")

        lines.append(f"\n## 3. Sample Size")
        lines.append(f"\n**Required N**: {plan.sample_size}")
        lines.append(f"\n**Power Analysis**:")
        lines.append(f"- Power: {plan.power_analysis.get('power', 'N/A')}")
        lines.append(f"- Alpha: {plan.power_analysis.get('alpha', 'N/A')}")

        lines.append("\n## 4. Timeline")
        for i, phase in enumerate(plan.timeline):
            lines.append(f"\n### Phase {i+1}: {phase['phase']}")
            lines.append(f"- Duration: {phase['duration']}")
            lines.append("- Tasks:")
            for task in phase.get('tasks', []):
                lines.append(f"  - {task}")

        lines.append("\n## 5. Resources")
        lines.append(f"\n- Personnel: {', '.join(plan.resources.get('personnel', []))}")
        lines.append(f"- Equipment: {', '.join(plan.resources.get('equipment', []))}")
        lines.append(f"- Budget: {plan.resources.get('budget_estimate', 'TBD')}")

        if include_randomization:
            lines.append("\n## 6. Randomization")
            lines.append("\nParticipants will be randomly assigned to experimental groups using:")
            lines.append("- Random number generator")
            lines.append("- Stratified randomization (if needed for demographic balance)")

        if include_blinding:
            lines.append("\n## 7. Blinding")
            lines.append("\n- Participants: blinded to group assignment where possible")
            lines.append("- Experimenters: blinded during data collection")
            lines.append("- Analysts: blinded until analysis complete")

        lines.append("\n## 8. Risk Mitigation")
        for risk in plan.risk_mitigation:
            lines.append(f"- {risk}")

        lines.append("\n## 9. Data Analysis Plan")
        lines.append("\n1. Descriptive statistics for all variables")
        lines.append("2. Assumption checking (normality, homogeneity of variance)")
        lines.append("3. Primary analysis: appropriate statistical test")
        lines.append("4. Secondary analysis: effect size estimation")
        lines.append("5. Sensitivity analysis: robustness checks")

        lines.append("\n" + "=" * 60)
        lines.append("**Protocol Version**: 1.0")
        lines.append("**Date**: Generated automatically")

        return "\n".join(lines)
