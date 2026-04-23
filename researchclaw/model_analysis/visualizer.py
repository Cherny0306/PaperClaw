"""
Model Visualizer

Visualization utilities for model analysis results.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class FigureData:
    """Figure data container"""
    figure_type: str
    data: dict
    title: str
    filename: str


class ModelVisualizer:
    """Visualizer for model analysis results"""

    def __init__(self):
        self.figures = []

    def plot_training_curves(
        self,
        results: Any,
        save_path: Optional[Path] = None
    ) -> FigureData:
        """
        Plot training curves.

        Args:
            results: TrainingResults object or dict with curve data
            save_path: Optional path to save figure

        Returns:
            FigureData
        """
        # Extract data
        if hasattr(results, 'to_dataframe'):
            df = results.to_dataframe()
        elif isinstance(results, dict):
            df = results
        else:
            raise ValueError("Invalid results format")

        figure_data = {
            "type": "training_curves",
            "epochs": df.get('epoch', list(range(len(df)))).tolist() if hasattr(df.get('epoch'), 'tolist') else list(df.get('epoch', [])),
            "loss_curves": {},
            "metric_curves": {},
        }

        # Loss curves
        for col in ['box_loss', 'cls_loss', 'dfl_loss', 'val_box_loss']:
            if col in df.columns:
                figure_data["loss_curves"][col] = df[col].tolist() if hasattr(df[col], 'tolist') else list(df[col])

        # Metric curves
        for col in ['precision', 'recall', 'mAP50', 'mAP50_95']:
            if col in df.columns:
                figure_data["metric_curves"][col] = df[col].tolist() if hasattr(df[col], 'tolist') else list(df[col])

        return FigureData(
            figure_type="training_curves",
            data=figure_data,
            title="Training Curves",
            filename="training_curves.png",
        )

    def plot_confusion_matrix(
        self,
        cm: np.ndarray,
        class_names: list[str],
        save_path: Optional[Path] = None,
        normalize: bool = True
    ) -> FigureData:
        """
        Plot confusion matrix.

        Args:
            cm: Confusion matrix
            class_names: List of class names
            save_path: Optional path to save
            normalize: Whether to normalize

        Returns:
            FigureData
        """
        if normalize:
            cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            cm_normalized = np.nan_to_num(cm_normalized)
        else:
            cm_normalized = cm

        return FigureData(
            figure_type="confusion_matrix",
            data={
                "matrix": cm_normalized.tolist(),
                "class_names": class_names,
                "normalize": normalize,
            },
            title="Confusion Matrix",
            filename="confusion_matrix.png",
        )

    def plot_pr_curve(
        self,
        pr_data: Any,
        save_path: Optional[Path] = None
    ) -> FigureData:
        """
        Plot Precision-Recall curve.

        Args:
            pr_data: PRCurveData or dict with precision/recall
            save_path: Optional path to save

        Returns:
            FigureData
        """
        if hasattr(pr_data, 'precision'):
            data = {
                "precision": pr_data.precision,
                "recall": pr_data.recall,
                "thresholds": pr_data.thresholds,
                "ap": pr_data.ap,
                "class_names": pr_data.class_names,
            }
        else:
            data = pr_data

        return FigureData(
            figure_type="pr_curve",
            data=data,
            title="Precision-Recall Curve",
            filename="pr_curve.png",
        )

    def plot_detection_results(
        self,
        image: np.ndarray,
        predictions: list[dict],
        ground_truth: list[dict],
        save_path: Optional[Path] = None
    ) -> FigureData:
        """
        Plot detection results with predictions vs ground truth.

        Args:
            image: Image array
            predictions: Prediction list
            ground_truth: Ground truth list
            save_path: Optional path to save

        Returns:
            FigureData
        """
        # Classify detections
        tp, fp, fn = self._classify_detections(predictions, ground_truth)

        return FigureData(
            figure_type="detection_results",
            data={
                "image_shape": image.shape,
                "predictions": predictions,
                "ground_truth": ground_truth,
                "tp_count": len(tp),
                "fp_count": len(fp),
                "fn_count": len(fn),
            },
            title="Detection Results",
            filename="detection_results.png",
        )

    def _classify_detections(
        self,
        predictions: list[dict],
        ground_truth: list[dict],
        iou_threshold: float = 0.5
    ) -> tuple[list, list, list]:
        """Classify detections as TP, FP, FN."""
        tp = []
        fp = []
        matched_gt = set()

        for pred in predictions:
            matched = False
            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue
                if pred.get('class') == gt.get('class'):
                    iou = self._calculate_iou(pred['bbox'], gt['bbox'])
                    if iou >= iou_threshold:
                        matched = True
                        matched_gt.add(i)
                        tp.append(pred)
                        break
            if not matched:
                fp.append(pred)

        fn = [gt for i, gt in enumerate(ground_truth) if i not in matched_gt]

        return tp, fp, fn

    def _calculate_iou(self, bbox1: list, bbox2: list) -> float:
        """Calculate IoU."""
        x1_min, y1_min, x1_max, y1_max = bbox1
        x2_min, y2_min, x2_max, y2_max = bbox2

        inter_xmin = max(x1_min, x2_min)
        inter_ymin = max(y1_min, y2_min)
        inter_xmax = min(x1_max, x2_max)
        inter_ymax = min(y1_max, y2_max)

        if inter_xmax < inter_xmin or inter_ymax < inter_ymin:
            return 0.0

        inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
        bbox1_area = (x1_max - x1_min) * (y1_max - y1_min)
        bbox2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = bbox1_area + bbox2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    def plot_scale_distribution(
        self,
        detections: list[dict],
        save_path: Optional[Path] = None
    ) -> FigureData:
        """
        Plot object scale distribution.

        Args:
            detections: List of detections with bbox info
            save_path: Optional path to save

        Returns:
            FigureData
        """
        sizes = []
        for det in detections:
            bbox = det.get('bbox', [0, 0, 0, 0])
            size = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            sizes.append(float(size))

        # Categorize
        sizes_array = np.array(sizes) if sizes else np.array([0])
        q25, q75 = np.percentile(sizes_array, [25, 75]) if len(sizes_array) > 1 else (0, 0)

        small = sum(1 for s in sizes if s <= q25)
        medium = sum(1 for s in sizes if q25 < s <= q75)
        large = sum(1 for s in sizes if s > q75)

        return FigureData(
            figure_type="scale_distribution",
            data={
                "sizes": sizes,
                "categories": {
                    "small": small,
                    "medium": medium,
                    "large": large,
                },
                "percentiles": {
                    "q25": float(q25),
                    "q50": float(np.median(sizes_array)),
                    "q75": float(q75),
                }
            },
            title="Object Scale Distribution",
            filename="scale_distribution.png",
        )

    def generate_detection_report(
        self,
        analysis: dict
    ) -> str:
        """
        Generate analysis report text.

        Args:
            analysis: Analysis results

        Returns:
            Report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("MODEL DETECTION ANALYSIS REPORT")
        lines.append("=" * 60)

        if 'metrics' in analysis:
            lines.append("\n## Detection Metrics")
            for key, value in analysis['metrics'].items():
                if isinstance(value, float):
                    lines.append(f"- {key}: {value:.4f}")
                else:
                    lines.append(f"- {key}: {value}")

        if 'per_class' in analysis:
            lines.append("\n## Per-Class Performance")
            for cls, metrics in analysis['per_class'].items():
                lines.append(f"\n### {cls}")
                for key, value in metrics.items():
                    if isinstance(value, float):
                        lines.append(f"  - {key}: {value:.4f}")

        if 'recommendations' in analysis:
            lines.append("\n## Recommendations")
            for rec in analysis['recommendations']:
                lines.append(f"- {rec}")

        return "\n".join(lines)
