"""
Remote Sensing Paper Templates

Templates for remote sensing research papers.
"""

from typing import Any, Optional


class RemoteSensingTemplates:
    """Templates for remote sensing papers"""

    INTRODUCTION_TEMPLATE = """
## 1. Introduction

Remote sensing technology has revolutionized our ability to monitor and analyze Earth's surface
at various scales. This study focuses on {study_focus} using {sensor_type} data.

### 1.1 Background
{background_text}

### 1.2 Problem Statement
Despite advances in remote sensing, challenges remain in {problem_area}:

- Limited accuracy in {specific_issue_1}
- Difficulty in {specific_issue_2}
- Need for improved {specific_issue_3}

### 1.3 Research Objectives
This study aims to:

1. Develop an improved method for {objective_1}
2. Evaluate the performance of {objective_2}
3. Analyze the impact of {objective_3}

### 1.4 Contributions
The main contributions of this paper are:

- Novel approach to {contribution_1}
- Comprehensive evaluation on {dataset_name}
- Insights into {contribution_3}
"""

    METHODS_TEMPLATE = """
## 2. Study Area and Data

### 2.1 Study Area
The study area is located in {location}, covering approximately {area_size} km2.
The region exhibits diverse land cover types including {land_cover_types}.

### 2.2 Remote Sensing Data
{data_description}

### 2.3 Ground Reference Data
Reference data was collected from {reference_source}, comprising {n_samples} samples
across {n_classes} classes.

## 3. Methods

### 3.1 Preprocessing
Preprocessing steps included:
- Atmospheric correction using {correction_method}
- Geometric registration with RMSE of {rmse} pixels
- Cloud masking using {cloud_detection_method}

### 3.2 Classification Framework
{classification_framework_description}

### 3.3 Accuracy Assessment
Accuracy assessment was conducted using:
- Confusion matrix analysis
- Stratified random sampling ({n_samples} validation points)
- McNemar's test for statistical comparison

## 4. Results

### 4.1 Classification Performance
{classification_results}

### 4.2 Spatial Analysis
{spatial_analysis_results}

### 4.3 Temporal Analysis (if applicable)
{temporal_analysis_results}
"""

    RESULTS_TEMPLATE = """
## 4. Results

### 4.1 Classification Performance

The proposed method achieved an overall accuracy of {oa:.2%} and a Kappa coefficient
of {kappa:.4f}. Table 1 summarizes the per-class performance.

### 4.2 Comparison with Existing Methods

Table 2 compares our method with state-of-the-art approaches:

| Method | OA | Kappa | mAP | Inference Time |
|--------|-----|-------|-----|----------------|
{comparison_table}

### 4.3 Error Analysis

The main sources of confusion were identified:
{error_analysis}

### 4.4 Spatial Patterns

{spatial_patterns_description}
"""

    DISCUSSION_TEMPLATE = """
## 5. Discussion

### 5.1 Interpretation of Results

The results demonstrate that {interpretation_1}. This is consistent with
previous studies by {citation_1} and {citation_2}.

### 5.2 Comparison with Literature

Our method outperformed {baseline_method} by {improvement_value} in terms of {metric}.
This improvement can be attributed to:

- Enhanced feature extraction through {reason_1}
- Improved classification algorithm {reason_2}
- Better handling of {reason_3}

### 5.3 Limitations

This study has several limitations:

1. Limited spatial extent of validation data
2. Temporal resolution constraints
3. Sensitivity to atmospheric conditions

### 5.4 Implications for Practice

The findings have important implications for {application_area}:

- Improved accuracy can support better {application_1}
- Faster processing enables {application_2}
- Cost reduction in {application_3}

### 5.5 Future Work

Future research should address:

- Extension to larger geographic areas
- Integration of multi-source data
- Development of real-time processing capabilities
"""

    LAND_COVER_CLASSES = [
        "Urban/Built-up",
        "Agricultural Land",
        "Forest",
        "Grassland",
        "Wetland",
        "Water Bodies",
        "Barren Land",
        "Clouds/No Data",
    ]

    SENSOR_TYPES = {
        "optical": ["Landsat-8/9 OLI", "Sentinel-2 MSI", "PlanetScope", "WorldView"],
        "sar": ["Sentinel-1", "ALOS-2 PALSAR", "TerraSAR-X"],
        "hyperspectral": ["Hyperion", "PRISMA", "DESIS"],
        "thermal": ["Landsat-8 TIRS", "ASTER"],
        "lidar": ["ICESat-2", "GEDI"],
    }

    METRICS_REQUIREMENTS = {
        "classification": ["Overall Accuracy", "Kappa", "F1-Score (macro)", "IoU (per class)"],
        "change_detection": ["Overall Accuracy", "F1-Score (change)", "Producer's Accuracy", "User's Accuracy"],
        "object_detection": ["mAP@0.5", "mAP@0.5:0.95", "Precision", "Recall"],
        "segmentation": ["mIoU", "F1-Score", "Boundary F1"],
    }

    @classmethod
    def get_introduction(cls, **kwargs) -> str:
        """Generate introduction section."""
        template = cls.INTRODUCTION_TEMPLATE
        return template.format(**kwargs)

    @classmethod
    def get_methods(cls, **kwargs) -> str:
        """Generate methods section."""
        template = cls.METHODS_TEMPLATE
        return template.format(**kwargs)

    @classmethod
    def get_results(cls, **kwargs) -> str:
        """Generate results section."""
        template = cls.RESULTS_TEMPLATE
        return template.format(**kwargs)

    @classmethod
    def get_discussion(cls, **kwargs) -> str:
        """Generate discussion section."""
        template = cls.DISCUSSION_TEMPLATE
        return template.format(**kwargs)

    @classmethod
    def get_paper_outline(cls, paper_type: str = "classification") -> list[str]:
        """Get recommended paper outline based on type."""
        outlines = {
            "classification": [
                "1. Introduction",
                "   1.1 Background",
                "   1.2 Study Area",
                "   1.3 Research Objectives",
                "2. Data and Methods",
                "   2.1 Study Area and Data",
                "   2.2 Preprocessing",
                "   2.3 Classification Method",
                "   2.4 Accuracy Assessment",
                "3. Results",
                "   3.1 Classification Accuracy",
                "   3.2 Spatial Analysis",
                "   3.3 Error Analysis",
                "4. Discussion",
                "   4.1 Interpretation",
                "   4.2 Comparison with Literature",
                "   4.3 Limitations",
                "   4.4 Future Work",
                "5. Conclusion",
            ],
            "change_detection": [
                "1. Introduction",
                "2. Study Area and Multi-temporal Data",
                "3. Change Detection Methodology",
                "4. Results and Analysis",
                "5. Discussion",
                "6. Conclusion",
            ],
            "object_detection": [
                "1. Introduction",
                "2. Related Work",
                "3. Methodology",
                "   3.1 Network Architecture",
                "   3.2 Training Procedure",
                "   3.3 Inference Pipeline",
                "4. Experiments",
                "   4.1 Dataset",
                "   4.2 Implementation Details",
                "   4.3 Results",
                "5. Discussion",
                "6. Conclusion",
            ],
        }
        return outlines.get(paper_type, outlines["classification"])

    @classmethod
    def generate_metrics_table(cls, metrics: dict, class_names: list[str]) -> str:
        """Generate metrics table in markdown format."""
        lines = []
        lines.append("| Class | Precision | Recall | F1-Score | IoU | Support |")
        lines.append("|-------|-----------|--------|----------|-----|---------|")

        for class_name in class_names:
            if class_name in metrics:
                m = metrics[class_name]
                lines.append(
                    f"| {class_name} | "
                    f"{m.get('precision', 0):.4f} | "
                    f"{m.get('recall', 0):.4f} | "
                    f"{m.get('f1', 0):.4f} | "
                    f"{m.get('iou', 0):.4f} | "
                    f"{m.get('support', 0)} |"
                )

        return "\n".join(lines)
