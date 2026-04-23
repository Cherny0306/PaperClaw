"""
Research Paper Writer Module

Generates IMRaD structured research papers.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np

from researchclaw.llm import _LLMClientLike


@dataclass
class ResearchContext:
    """Context for paper writing"""
    title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    hypotheses: list[dict] = field(default_factory=list)
    experiment_results: dict = field(default_factory=dict)
    data_summary: dict = field(default_factory=dict)
    domain: str = "general"
    paper_type: str = "original_research"
    references: list[str] = field(default_factory=list)


@dataclass
class SectionContent:
    """Content for a paper section"""
    title: str
    content: str
    subsections: list['SectionContent'] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    tables: list[dict] = field(default_factory=list)


@dataclass
class ResearchPaper:
    """Complete research paper"""
    title: str
    abstract: str
    keywords: list[str]
    introduction: SectionContent
    methods: SectionContent
    results: SectionContent
    discussion: SectionContent
    conclusion: SectionContent
    references: list[str]
    supplementary: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class ResearchPaperWriter:
    """Write research papers in IMRaD format"""

    def __init__(self, llm: Optional[_LLMClientLike] = None):
        self.llm = llm

    def write_introduction(
        self,
        context: ResearchContext,
        include_subsections: bool = True
    ) -> SectionContent:
        """
        Write Introduction section.
        """
        if self.llm:
            return self._llm_write_introduction(context)

        content_parts = []
        content_parts.append("# Introduction\n")
        content_parts.append("## 1. Background\n")
        content_parts.append(
            f"This research addresses the domain of {context.domain}. "
            f"Recent advances in this field have generated interest in {context.title}. "
            "Understanding the underlying mechanisms is crucial for advancing the field."
        )

        content_parts.append("\n## 2. Problem Statement\n")
        if context.hypotheses:
            problem = " ".join([h.get('question', '') for h in context.hypotheses[:2]])
            content_parts.append(f"Despite significant progress, several questions remain unanswered: {problem}")
        else:
            content_parts.append(
                "Despite significant progress in the field, there remain unanswered questions "
                "that require systematic investigation."
            )

        content_parts.append("\n## 3. Research Objectives\n")
        content_parts.append("This study aims to:\n")
        if context.hypotheses:
            for i, h in enumerate(context.hypotheses[:3], 1):
                content_parts.append(f"{i}. Investigate {h.get('question', 'the research question')}")
        else:
            content_parts.append("1. Analyze the relationship between key variables")
            content_parts.append("2. Test proposed hypotheses")
            content_parts.append("3. Provide insights for practical applications")

        content_parts.append("\n## 4. Contributions\n")
        content_parts.append("This paper makes the following contributions:\n")
        content_parts.append("- Novel analysis of the research problem\n")
        content_parts.append("- Empirical evaluation of proposed hypotheses\n")
        content_parts.append("- Insights applicable to the broader field\n")

        return SectionContent(
            title="Introduction",
            content="\n".join(content_parts),
            subsections=[]
        )

    def _llm_write_introduction(self, context: ResearchContext) -> SectionContent:
        """Use LLM to write introduction."""
        try:
            system = f"You are an academic paper writer specializing in {context.domain} research."
            user = f"""Write a comprehensive Introduction section for a research paper with the following context:

Title: {context.title}

Hypotheses:
{chr(10).join([f"- {h.get('question', '')}" for h in context.hypotheses[:3]])}

Data Summary:
{context.data_summary}

Write in formal academic style. Include:
1. Background and motivation
2. Problem statement
3. Research objectives
4. Paper contributions

Keep it concise but comprehensive. Output only the introduction text."""

            response = self.llm.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ], max_tokens=1500)

            return SectionContent(
                title="Introduction",
                content=f"# Introduction\n\n{response.content}",
                subsections=[]
            )

        except Exception:
            return self._fallback_introduction(context)

    def write_methods(self, context: ResearchContext, include_subsections: bool = True) -> SectionContent:
        """Write Methods section."""
        content_parts = []
        content_parts.append("# Methods\n")

        content_parts.append("## 1. Study Design\n")
        content_parts.append(
            "This study employs a quantitative research design to test the proposed hypotheses. "
            "Data was collected through controlled experiments and observational studies."
        )

        content_parts.append("\n## 2. Data Collection\n")
        if context.data_summary:
            n_samples = context.data_summary.get('n_samples', 'N/A')
            n_features = context.data_summary.get('n_features', 'N/A')
            content_parts.append(f"### 2.1 Dataset\n")
            content_parts.append(f"The dataset consists of {n_samples} samples with {n_features} features. ")
            content_parts.append("Data quality was ensured through validation procedures.")
        else:
            content_parts.append("Data was collected following standard protocols.")

        content_parts.append("\n### 2.2 Variables\n")
        if context.hypotheses:
            for h in context.hypotheses[:2]:
                if 'variables' in h:
                    content_parts.append(f"- {h['question']}: {len(h['variables'])} variables analyzed")
        else:
            content_parts.append("- Independent variables: treatment conditions")
            content_parts.append("- Dependent variables: measured outcomes")
            content_parts.append("- Controlled variables: baseline characteristics")

        content_parts.append("\n## 3. Analysis Methods\n")
        content_parts.append("### 3.1 Statistical Analysis\n")
        if context.hypotheses:
            methods = set()
            for h in context.hypotheses:
                if 'test_method' in h:
                    methods.add(h['test_method'])
            content_parts.append(f"Statistical analyses employed: {', '.join(methods) if methods else 'standard statistical methods'}.")
        else:
            content_parts.append("Analyses included descriptive statistics, correlation analysis, and hypothesis testing.")

        content_parts.append("\n### 3.2 Model Evaluation\n")
        content_parts.append("Models were evaluated using standard metrics including accuracy, precision, recall, and F1-score.")

        content_parts.append("\n## 4. Ethical Considerations\n")
        content_parts.append("This study was conducted following established ethical guidelines. All data was anonymized prior to analysis.")

        return SectionContent(title="Methods", content="\n".join(content_parts), subsections=[])

    def write_results(self, context: ResearchContext, include_statistics: bool = True) -> SectionContent:
        """Write Results section."""
        content_parts = []
        content_parts.append("# Results\n")

        if context.experiment_results:
            results = context.experiment_results

            if 'metrics' in results:
                content_parts.append("## 1. Model Performance\n")
                metrics = results['metrics']
                if isinstance(metrics, dict):
                    for metric_name, value in list(metrics.items())[:5]:
                        content_parts.append(f"- **{metric_name}**: {value:.4f}" if isinstance(value, float) else f"- **{metric_name}**: {value}")
                content_parts.append("")

            if 'comparisons' in results:
                content_parts.append("\n## 2. Comparative Analysis\n")
                comparisons = results['comparisons']
                if isinstance(comparisons, list):
                    for comp in comparisons[:3]:
                        if isinstance(comp, dict):
                            content_parts.append(f"- {comp.get('description', 'Comparison performed')}")
                elif isinstance(comparisons, dict):
                    for key, value in list(comparisons.items())[:3]:
                        content_parts.append(f"- {key}: {value}")
                content_parts.append("")

            if 'hypothesis_tests' in results:
                content_parts.append("\n## 3. Hypothesis Testing\n")
                tests = results['hypothesis_tests']
                if isinstance(tests, list):
                    for test in tests[:3]:
                        if isinstance(test, dict):
                            status = "Supported" if test.get('supported', False) else "Not supported"
                            p_value = test.get('p_value', 'N/A')
                            content_parts.append(f"- H{test.get('id', '?')}: {status} (p={p_value})")
                content_parts.append("")
        else:
            content_parts.append("## 1. Descriptive Statistics\n")
            if context.data_summary:
                content_parts.append(f"Analysis was performed on {context.data_summary.get('n_samples', 'N/A')} observations.")
            else:
                content_parts.append("Results are presented based on the collected data.")

            content_parts.append("\n## 2. Key Findings\n")
            if context.hypotheses:
                for h in context.hypotheses[:2]:
                    content_parts.append(f"- {h.get('question', 'Research question investigated')}")
                    content_parts.append(f"  - H0: {h.get('null_hypothesis', 'No significant effect')}")
                    content_parts.append(f"  - Result: Analysis performed")
            else:
                content_parts.append("- Significant relationships were observed between key variables")
                content_parts.append("- Effect sizes ranged from moderate to large")

            content_parts.append("\n## 3. Statistical Significance\n")
            content_parts.append("Statistical tests were conducted at the 0.05 significance level.")

        return SectionContent(title="Results", content="\n".join(content_parts), subsections=[])

    def write_discussion(self, context: ResearchContext, include_limitations: bool = True) -> SectionContent:
        """Write Discussion section."""
        content_parts = []
        content_parts.append("# Discussion\n")

        content_parts.append("## 1. Summary of Findings\n")
        content_parts.append(
            f"This study investigated {context.title} and examined the relationships between key variables. "
            "The results provide insights into the research questions posed in the introduction."
        )

        content_parts.append("\n## 2. Interpretation\n")
        if context.hypotheses:
            content_parts.append("The analysis reveals several important patterns:\n")
            for h in context.hypotheses[:3]:
                content_parts.append(f"- {h.get('question', 'Research question')}: ")
                content_parts.append(f"  The {h.get('test_method', 'analysis')} was conducted to test this hypothesis.")
        else:
            content_parts.append("The findings suggest that:\n")
            content_parts.append("- There is evidence of significant relationships between variables")
            content_parts.append("- The observed effects are consistent with theoretical predictions")

        content_parts.append("\n## 3. Comparison with Prior Work\n")
        content_parts.append(
            "These results are consistent with findings from previous studies in the field. "
            "However, some differences were observed that warrant further investigation."
        )

        if include_limitations:
            content_parts.append("\n## 4. Limitations\n")
            content_parts.append("This study has several limitations:\n")
            content_parts.append("- Sample size constraints may limit generalizability\n")
            content_parts.append("- Observational data limits causal inference\n")
            content_parts.append("- Potential confounding variables were not fully controlled")

        content_parts.append("\n## 5. Implications\n")
        content_parts.append("The findings have important implications for:\n")
        content_parts.append("- Theoretical understanding of the domain\n")
        content_parts.append("- Practical applications in the field\n")
        content_parts.append("- Future research directions")

        content_parts.append("\n## 6. Future Work\n")
        content_parts.append("Future research should consider:\n")
        content_parts.append("- Larger-scale validation studies\n")
        content_parts.append("- Longitudinal designs to establish causality\n")
        content_parts.append("- Exploration of additional moderating variables")

        return SectionContent(title="Discussion", content="\n".join(content_parts), subsections=[])

    def write_conclusion(self, context: ResearchContext) -> SectionContent:
        """Write Conclusion section."""
        content_parts = []
        content_parts.append("# Conclusion\n")

        content_parts.append("## 1. Summary\n")
        content_parts.append(
            f"This paper presented a comprehensive investigation of {context.title}. "
            "Through rigorous analysis of the data, we tested several hypotheses and derived insights "
            "into the research questions posed."
        )

        content_parts.append("\n## 2. Key Contributions\n")
        content_parts.append("This research contributes to the field by:\n")
        content_parts.append("- Providing empirical evidence for proposed hypotheses\n")
        content_parts.append("- Offering new insights into the mechanisms underlying the phenomena\n")
        content_parts.append("- Suggesting directions for future research and practical applications\n")

        content_parts.append("\n## 3. Final Remarks\n")
        content_parts.append(
            "The findings underscore the importance of systematic investigation in advancing "
            "scientific understanding. We hope this work stimulates further research in this area."
        )

        return SectionContent(title="Conclusion", content="\n".join(content_parts), subsections=[])

    def assemble_paper(
        self,
        context: ResearchContext,
        include_abstract: bool = True,
        include_references: bool = True
    ) -> ResearchPaper:
        """Assemble complete paper from sections."""
        introduction = self.write_introduction(context)
        methods = self.write_methods(context)
        results = self.write_results(context)
        discussion = self.write_discussion(context)
        conclusion = self.write_conclusion(context)

        if include_abstract:
            abstract = self._generate_abstract(context)
        else:
            abstract = context.abstract or "Abstract not provided."

        references = context.references if include_references else []

        return ResearchPaper(
            title=context.title or "Research Paper",
            abstract=abstract,
            keywords=context.keywords,
            introduction=introduction,
            methods=methods,
            results=results,
            discussion=discussion,
            conclusion=conclusion,
            references=references,
            metadata={
                "created_at": datetime.now().isoformat(),
                "domain": context.domain,
                "paper_type": context.paper_type,
            }
        )

    def _generate_abstract(self, context: ResearchContext) -> str:
        """Generate abstract from context."""
        abstract_parts = []
        abstract_parts.append("**Background**: ")
        abstract_parts.append(f"This study addresses {context.domain} research in {context.title}.")

        abstract_parts.append("\n**Objective**: ")
        if context.hypotheses:
            obj = " ".join([h.get('question', '')[:100] for h in context.hypotheses[:2]])
            abstract_parts.append(f"We aimed to investigate {obj}.")
        else:
            abstract_parts.append("We aimed to analyze key relationships in the research domain.")

        abstract_parts.append("\n**Methods**: ")
        if context.data_summary:
            abstract_parts.append(
                f"Data was collected from {context.data_summary.get('n_samples', 'N/A')} samples "
                f"with {context.data_summary.get('n_features', 'N/A')} features. "
                "Statistical analyses and hypothesis testing were performed."
            )
        else:
            abstract_parts.append("Standard quantitative research methods were employed.")

        abstract_parts.append("\n**Results**: ")
        if context.experiment_results and 'metrics' in context.experiment_results:
            metrics = context.experiment_results['metrics']
            if isinstance(metrics, dict):
                key_metric = list(metrics.items())[0]
                abstract_parts.append(f"Key findings include {key_metric[0]} = {key_metric[1]:.4f}.")
            else:
                abstract_parts.append("Results are presented in detail in the paper.")
        else:
            abstract_parts.append("Significant patterns were observed and hypotheses were tested.")

        abstract_parts.append("\n**Conclusions**: ")
        abstract_parts.append("The study provides evidence supporting the proposed hypotheses and offers insights for future research.")

        return "".join(abstract_parts)

    def export_to_markdown(self, paper: ResearchPaper) -> str:
        """Export paper to markdown format."""
        lines = []
        lines.append(f"# {paper.title}\n")
        lines.append(f"**Abstract**: {paper.abstract}\n")
        lines.append(f"**Keywords**: {', '.join(paper.keywords)}\n")
        lines.append("\n---\n")
        lines.append(paper.introduction.content)
        lines.append("\n---\n")
        lines.append(paper.methods.content)
        lines.append("\n---\n")
        lines.append(paper.results.content)
        lines.append("\n---\n")
        lines.append(paper.discussion.content)
        lines.append("\n---\n")
        lines.append(paper.conclusion.content)

        if paper.references:
            lines.append("\n---\n")
            lines.append("# References\n")
            for i, ref in enumerate(paper.references, 1):
                lines.append(f"[{i}] {ref}")

        return "\n".join(lines)

    def _fallback_introduction(self, context: ResearchContext) -> SectionContent:
        """Fallback introduction when LLM is not available."""
        return SectionContent(
            title="Introduction",
            content=f"""# Introduction

## Background
This research investigates {context.title} within the domain of {context.domain}. Understanding this topic is crucial for advancing knowledge in the field.

## Problem Statement
Despite advances in the field, several questions remain unanswered regarding the relationships between key variables.

## Research Objectives
This study aims to:
1. Analyze the research problem systematically
2. Test proposed hypotheses
3. Provide insights for practical applications

## Contributions
This paper makes the following contributions:
- Systematic analysis of the research problem
- Empirical evaluation of key relationships
- Insights applicable to the broader field
""",
            subsections=[]
        )
