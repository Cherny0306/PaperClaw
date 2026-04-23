"""
Hypothesis Generator Module

Discovers patterns and generates research hypotheses from data analysis.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import pandas as pd
import numpy as np

from researchclaw.llm import _LLMClientLike


class PatternType(Enum):
    """Types of patterns discovered in data"""
    STATISTICAL = "statistical"
    TEMPORAL = "temporal"
    SPATIAL = "spatial"
    CORRELATIONAL = "correlational"
    DISTRIBUTIONAL = "distributional"
    TREND = "trend"


@dataclass
class Pattern:
    """Discovered data pattern"""
    id: str
    pattern_type: PatternType
    description: str
    evidence: dict[str, Any]
    significance: float
    variables: list[str]


@dataclass
class HypothesisVariable:
    """Variable definition for hypothesis"""
    name: str
    type: str
    data_type: str
    description: str = ""


@dataclass
class Hypothesis:
    """Research hypothesis"""
    id: str
    question: str
    null_hypothesis: str
    alternative_hypothesis: str
    variables: list[HypothesisVariable]
    test_method: str
    significance_level: float = 0.05
    expected_effect: str = ""
    novelty_score: float = 0.0
    feasibility_score: float = 0.0
    domain: str = "general"
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "question": self.question,
            "null_hypothesis": self.null_hypothesis,
            "alternative_hypothesis": self.alternative_hypothesis,
            "variables": [
                {"name": v.name, "type": v.type, "data_type": v.data_type, "description": v.description}
                for v in self.variables
            ],
            "test_method": self.test_method,
            "significance_level": self.significance_level,
            "expected_effect": self.expected_effect,
            "novelty_score": self.novelty_score,
            "feasibility_score": self.feasibility_score,
            "domain": self.domain,
            "created_at": self.created_at.isoformat(),
        }


class HypothesisGenerator:
    """Generate research hypotheses from data analysis"""

    def __init__(self, llm: Optional[_LLMClientLike] = None, data_context: Optional[dict] = None):
        self.llm = llm
        self.data_context = data_context or {}
        self._pattern_counter = 0
        self._hypothesis_counter = 0

    def discover_patterns(
        self,
        df: pd.DataFrame,
        analysis_results: Optional[dict] = None
    ) -> list[Pattern]:
        """
        Discover patterns in the data.

        Args:
            df: Input DataFrame
            analysis_results: Optional pre-computed analysis results

        Returns:
            List of discovered patterns
        """
        patterns = []

        if analysis_results and "correlations" in analysis_results:
            for corr in analysis_results["correlations"].get("significant_pairs", []):
                patterns.append(Pattern(
                    id=f"pattern_{self._pattern_counter}",
                    pattern_type=PatternType.CORRELATIONAL,
                    description=f"Significant correlation between {corr['var1']} and {corr['var2']} "
                               f"(r={corr['correlation']:.3f}, p={corr['p_value']:.4f})",
                    evidence=corr,
                    significance=1 - corr['p_value'],
                    variables=[corr['var1'], corr['var2']],
                ))
                self._pattern_counter += 1

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            skew = df[col].skew()
            if abs(skew) > 1:
                patterns.append(Pattern(
                    id=f"pattern_{self._pattern_counter}",
                    pattern_type=PatternType.DISTRIBUTIONAL,
                    description=f"Highly skewed distribution in {col} (skewness={skew:.3f})",
                    evidence={"skewness": float(skew)},
                    significance=min(abs(skew) / 3, 1.0),
                    variables=[col],
                ))
                self._pattern_counter += 1

        if analysis_results and "group_comparisons" in analysis_results:
            for comparison in analysis_results["group_comparisons"]:
                if comparison.get("is_significant"):
                    patterns.append(Pattern(
                        id=f"pattern_{self._pattern_counter}",
                        pattern_type=PatternType.STATISTICAL,
                        description=f"Significant difference in {comparison['value_col']} "
                                   f"across {comparison['group_col']} groups "
                                   f"(p={comparison['p_value']:.4f})",
                        evidence=comparison,
                        significance=1 - comparison['p_value'],
                        variables=[comparison['group_col'], comparison['value_col']],
                    ))
                    self._pattern_counter += 1

        if analysis_results and "time_series" in analysis_results:
            ts = analysis_results["time_series"]
            if ts.get("trend", {}).get("p_value", 1) < 0.05:
                trend = ts["trend"]
                patterns.append(Pattern(
                    id=f"pattern_{self._pattern_counter}",
                    pattern_type=PatternType.TREND,
                    description=f"Significant {trend['direction']} trend "
                               f"(slope={trend['slope']:.4f}, p={trend['p_value']:.4f})",
                    evidence=trend,
                    significance=1 - trend['p_value'],
                    variables=["time", "value"],
                ))
                self._pattern_counter += 1

        if not analysis_results:
            corr_matrix = df[numeric_cols].corr()
            for i, col1 in enumerate(numeric_cols):
                for j, col2 in enumerate(numeric_cols):
                    if i < j:
                        r = corr_matrix.loc[col1, col2]
                        if abs(r) > 0.5:
                            patterns.append(Pattern(
                                id=f"pattern_{self._pattern_counter}",
                                pattern_type=PatternType.CORRELATIONAL,
                                description=f"Correlation between {col1} and {col2} (r={r:.3f})",
                                evidence={"correlation": float(r)},
                                significance=abs(r),
                                variables=[col1, col2],
                            ))
                            self._pattern_counter += 1

        return patterns

    def generate_research_questions(
        self,
        patterns: list[Pattern],
        domain: str = "general"
    ) -> list[str]:
        """
        Generate research questions from discovered patterns.

        Args:
            patterns: List of discovered patterns
            domain: Research domain

        Returns:
            List of research questions
        """
        questions = []

        for pattern in patterns:
            if pattern.pattern_type == PatternType.CORRELATIONAL:
                var1, var2 = pattern.variables[:2]
                questions.append(f"What is the causal relationship between {var1} and {var2}?")
                questions.append(f"How does {var1} influence {var2} under different conditions?")

            elif pattern.pattern_type == PatternType.STATISTICAL:
                group_col = pattern.variables[0]
                value_col = pattern.variables[1] if len(pattern.variables) > 1 else pattern.variables[0]
                questions.append(f"What factors explain the significant difference in {value_col} across {group_col} groups?")

            elif pattern.pattern_type == PatternType.TREND:
                questions.append("What factors drive the observed temporal trend?")
                questions.append("Will this trend continue in the future?")

            elif pattern.pattern_type == PatternType.DISTRIBUTIONAL:
                var = pattern.variables[0]
                questions.append(f"What explains the skewed distribution of {var}?")
                questions.append(f"Are there subpopulations with different {var} distributions?")

        if self.llm and len(patterns) > 0:
            questions.extend(self._llm_generate_questions(patterns, domain))

        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)

        return unique_questions

    def _llm_generate_questions(self, patterns: list[Pattern], domain: str) -> list[str]:
        """Use LLM to generate additional research questions."""
        if not self.llm:
            return []

        try:
            system = f"You are a research assistant specializing in {domain} research."
            user = f"""Based on the following discovered patterns, generate 3-5 additional research questions:

Patterns discovered:
{chr(10).join([f"- {p.description}" for p in patterns])}

Generate insightful research questions that build on these patterns. Focus on:
1. Causal relationships
2. Predictive factors
3. Intervention opportunities
4. Theoretical implications

Output as a numbered list."""

            response = self.llm.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], max_tokens=500)

            questions = []
            for line in response.content.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    q = line.lstrip('0123456789.-) ')
                    if q and len(q) > 10:
                        questions.append(q)

            return questions

        except Exception:
            return []

    def formulate_hypotheses(
        self,
        questions: list[str],
        domain: str = "general"
    ) -> list[Hypothesis]:
        """
        Formulate hypotheses from research questions.

        Args:
            questions: List of research questions
            domain: Research domain

        Returns:
            List of formulated hypotheses
        """
        hypotheses = []

        for question in questions:
            variables = self._extract_variables_from_question(question)
            h0, h1 = self._generate_hypotheses_pair(question, variables)
            test_method = self._determine_test_method(variables)

            hypothesis = Hypothesis(
                id=f"h_{self._hypothesis_counter}",
                question=question,
                null_hypothesis=h0,
                alternative_hypothesis=h1,
                variables=variables,
                test_method=test_method,
                domain=domain,
            )

            hypotheses.append(hypothesis)
            self._hypothesis_counter += 1

        return hypotheses

    def _extract_variables_from_question(self, question: str) -> list[HypothesisVariable]:
        """Extract variables from a research question."""
        variables = []

        independent_markers = ["influence", "affect", "effect on", "depends on", "relationship between"]
        dependent_markers = ["outcome", "result", "performance", "accuracy", "efficiency"]

        has_independent = any(m in question.lower() for m in independent_markers)
        has_dependent = any(m in question.lower() for m in dependent_markers)

        if " and " in question.lower():
            parts = question.lower().split(" and ")
            if len(parts) >= 2:
                var1 = parts[0].split()[-1].strip("?")
                var2 = parts[1].split()[-1].strip("?")
                if var1 and var2:
                    if has_independent:
                        variables.append(HypothesisVariable(
                            name=var1, type="independent", data_type="numeric"
                        ))
                        variables.append(HypothesisVariable(
                            name=var2, type="dependent", data_type="numeric"
                        ))
                    else:
                        variables.append(HypothesisVariable(
                            name=var1, type="variable", data_type="numeric"
                        ))
                        variables.append(HypothesisVariable(
                            name=var2, type="variable", data_type="numeric"
                        ))

        if not variables:
            variables.append(HypothesisVariable(
                name="factor", type="independent", data_type="numeric"
            ))
            variables.append(HypothesisVariable(
                name="outcome", type="dependent", data_type="numeric"
            ))

        return variables

    def _generate_hypotheses_pair(
        self,
        question: str,
        variables: list[HypothesisVariable]
    ) -> tuple[str, str]:
        """Generate null and alternative hypotheses."""
        if len(variables) >= 2:
            var_indep = variables[0].name
            var_dep = variables[1].name
            h0 = f"There is no significant relationship between {var_indep} and {var_dep}"
            h1 = f"There is a significant relationship between {var_indep} and {var_dep}"
        else:
            h0 = "There is no significant effect"
            h1 = "There is a significant effect"

        return h0, h1

    def _determine_test_method(self, variables: list[HypothesisVariable]) -> str:
        """Determine appropriate statistical test."""
        if len(variables) < 2:
            return "descriptive analysis"

        numeric_vars = [v for v in variables if v.data_type == "numeric"]

        if len(numeric_vars) >= 2:
            return "correlation analysis (Pearson/Spearman)"
        else:
            return "t-test / ANOVA / chi-square"

    def prioritize_hypotheses(
        self,
        hypotheses: list[Hypothesis],
        criteria: Optional[dict] = None
    ) -> list[Hypothesis]:
        """
        Prioritize hypotheses based on novelty and feasibility.

        Args:
            hypotheses: List of hypotheses
            criteria: Optional scoring criteria

        Returns:
            Prioritized list of hypotheses
        """
        for h in hypotheses:
            if h.novelty_score == 0:
                h.novelty_score = self._assess_novelty(h)
            if h.feasibility_score == 0:
                h.feasibility_score = self._assess_feasibility(h)

        def composite_score(h: Hypothesis) -> float:
            novelty_weight = 0.6
            feasibility_weight = 0.4
            return h.novelty_score * novelty_weight + h.feasibility_score * feasibility_weight

        return sorted(hypotheses, key=composite_score, reverse=True)

    def _assess_novelty(self, hypothesis: Hypothesis) -> float:
        """Assess the novelty of a hypothesis (0-1)."""
        score = 0.5

        if len(hypothesis.variables) > 2:
            score += 0.1

        if hypothesis.expected_effect:
            score += 0.2

        if self.llm:
            try:
                system = "You are a research novelty assessor."
                user = f"""Rate the novelty of this hypothesis from 0 to 1 (1 being highly novel):

{hypothesis.question}

Consider:
- How specific is it?
- How specific are the expected effects?
- Does it address a gap in current knowledge?

Output only a number between 0 and 1."""

                response = self.llm.chat([
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ], max_tokens=50)

                import re
                match = re.search(r'0?\.\d+', response.content)
                if match:
                    return float(match.group())

            except Exception:
                pass

        return min(score, 1.0)

    def _assess_feasibility(self, hypothesis: Hypothesis) -> float:
        """Assess the feasibility of testing a hypothesis (0-1)."""
        score = 0.7

        if len(hypothesis.variables) > 3:
            score -= 0.1

        simple_tests = ["correlation", "t-test", "ANOVA"]
        if any(t in hypothesis.test_method.lower() for t in simple_tests):
            score += 0.1

        return min(max(score, 0), 1.0)

    def generate_report(
        self,
        patterns: list[Pattern],
        hypotheses: list[Hypothesis]
    ) -> str:
        """Generate a summary report."""
        lines = []
        lines.append("=" * 60)
        lines.append("HYPOTHESIS GENERATION REPORT")
        lines.append("=" * 60)

        lines.append(f"\n## Discovered Patterns ({len(patterns)})")
        for p in patterns:
            lines.append(f"\n### {p.id}: {p.pattern_type.value}")
            lines.append(f"**Description**: {p.description}")
            lines.append(f"**Significance**: {p.significance:.2%}")
            lines.append(f"**Variables**: {', '.join(p.variables)}")

        lines.append(f"\n## Generated Hypotheses ({len(hypotheses)})")
        for h in hypotheses:
            lines.append(f"\n### {h.id}")
            lines.append(f"**Question**: {h.question}")
            lines.append(f"**H0**: {h.null_hypothesis}")
            lines.append(f"**H1**: {h.alternative_hypothesis}")
            lines.append(f"**Test Method**: {h.test_method}")
            lines.append(f"**Novelty**: {h.novelty_score:.2f} | **Feasibility**: {h.feasibility_score:.2f}")

        return "\n".join(lines)
