"""
Metrics Calculator

Shared metrics calculation utilities.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class DetectionMetricSet:
    """Complete detection metrics"""
    precision: float
    recall: float
    f1: float
    mAP: float
    mAP50: float
    mAP75: float
    mAP_s: float  # Small objects
    mAP_m: float  # Medium objects
    mAP_l: float  # Large objects


class MetricsCalculator:
    """Calculator for various metrics"""

    @staticmethod
    def calculate_iou(bbox1: list, bbox2: list, format: str = "xyxy") -> float:
        """
        Calculate IoU between two bboxes.

        Args:
            bbox1: First bounding box
            bbox2: Second bounding box
            format: 'xyxy' (x1,y1,x2,y2) or 'xywh' (x,y,w,h)

        Returns:
            IoU value
        """
        if format == "xywh":
            bbox1 = [bbox1[0], bbox1[1], bbox1[0] + bbox1[2], bbox1[1] + bbox1[3]]
            bbox2 = [bbox2[0], bbox2[1], bbox2[0] + bbox2[2], bbox2[1] + bbox2[3]]

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

    @staticmethod
    def calculate_precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
        """Calculate precision, recall, and F1."""
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return precision, recall, f1

    @staticmethod
    def calculate_map(
        predictions: list[dict],
        ground_truth: list[dict],
        iou_thresholds: list[float] = None,
        format: str = "xyxy"
    ) -> dict:
        """
        Calculate mean Average Precision.

        Args:
            predictions: List of predictions with 'bbox', 'score', 'class'
            ground_truth: List of ground truths with 'bbox', 'class'
            iou_thresholds: List of IoU thresholds
            format: Bbox format

        Returns:
            Dictionary with mAP at different thresholds
        """
        if iou_thresholds is None:
            iou_thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]

        results = {}

        for iou_thresh in iou_thresholds:
            # Sort predictions by score
            sorted_preds = sorted(predictions, key=lambda x: x.get('score', 0), reverse=True)

            tp = 0
            fp = 0
            matched_gt = set()

            for pred in sorted_preds:
                matched = False
                for i, gt in enumerate(ground_truth):
                    if i in matched_gt:
                        continue
                    if pred.get('class') == gt.get('class'):
                        iou = MetricsCalculator.calculate_iou(pred['bbox'], gt['bbox'], format)
                        if iou >= iou_thresh:
                            matched = True
                            matched_gt.add(i)
                            break

                if matched:
                    tp += 1
                else:
                    fp += 1

            fn = len(ground_truth) - len(matched_gt)
            precision, recall, f1 = MetricsCalculator.calculate_precision_recall(tp, fp, fn)

            results[f"AP@{iou_thresh:.2f}"] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }

        # Calculate mAP
        aps = [r[f"AP@{iou:.2f}"]["precision"] for iou in iou_thresholds]
        results["mAP"] = np.mean(aps) if aps else 0
        results["mAP50"] = results.get("AP@0.50", {}).get("precision", 0)
        results["mAP75"] = results.get("AP@0.75", {}).get("precision", 0)

        return results

    @staticmethod
    def calculate_confusion_matrix(
        predictions: list[dict],
        ground_truth: list[dict],
        class_names: list[str],
        iou_threshold: float = 0.5,
        format: str = "xyxy"
    ) -> np.ndarray:
        """Calculate confusion matrix."""
        n_classes = len(class_names)
        cm = np.zeros((n_classes, n_classes), dtype=int)

        matched_gt = set()

        for pred in predictions:
            best_iou = 0
            best_gt_idx = -1

            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue
                if pred.get('class') == gt.get('class'):
                    iou = MetricsCalculator.calculate_iou(pred['bbox'], gt['bbox'], format)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = i

            if best_iou >= iou_threshold and best_gt_idx >= 0:
                pred_class_idx = class_names.index(pred.get('class')) if pred.get('class') in class_names else -1
                gt_class_idx = class_names.index(ground_truth[best_gt_idx].get('class')) if ground_truth[best_gt_idx].get('class') in class_names else -1

                if pred_class_idx >= 0 and gt_class_idx >= 0:
                    cm[gt_class_idx, pred_class_idx] += 1
                    matched_gt.add(best_gt_idx)

        return cm

    @staticmethod
    def calculate_segmentation_metrics(
        pred_mask: np.ndarray,
        gt_mask: np.ndarray
    ) -> dict:
        """Calculate segmentation metrics (IoU, Dice, etc.)."""
        intersection = np.sum(pred_mask & gt_mask)
        union = np.sum(pred_mask | gt_mask)

        iou = intersection / union if union > 0 else 0
        dice = 2 * intersection / (np.sum(pred_mask) + np.sum(gt_mask)) if (np.sum(pred_mask) + np.sum(gt_mask)) > 0 else 0

        return {
            "iou": float(iou),
            "dice": float(dice),
            "intersection": int(intersection),
            "union": int(union),
        }

    @staticmethod
    def format_metrics_table(metrics: dict, precision: int = 4) -> str:
        """Format metrics as ASCII table."""
        lines = []
        lines.append("+" + "-" * 30 + "+" + "-" * 15 + "+")
        lines.append(f"| {'Metric':<28} | {'Value':>13} |")
        lines.append("+" + "=" * 30 + "+" + "=" * 15 + "+")

        for key, value in sorted(metrics.items()):
            if isinstance(value, float):
                formatted = f"{value