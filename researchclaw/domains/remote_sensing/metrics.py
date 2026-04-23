"""
Remote Sensing Metrics Calculator

Specialized metrics for remote sensing classification and change detection.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class ClassificationReport:
    """Classification report with remote sensing specific metrics"""
    overall_accuracy: float
    kappa: float
    macro_f1: float
    weighted_f1: float
    per_class: dict


class RemoteSensingMetricsCalculator:
    """Calculator for remote sensing specific metrics"""

    @staticmethod
    def calculate_kappa(confusion_matrix: np.ndarray) -> float:
        """Calculate Cohen's Kappa coefficient."""
        n = confusion_matrix.sum()
        sum_po = confusion_matrix.diagonal().sum()
        sum_pe = np.sum(confusion_matrix.sum(axis=1) * confusion_matrix.sum(axis=0)) / n

        if sum_pe == 1:
            return 1.0

        kappa = (sum_po / n - sum_pe) / (1 - sum_pe) if (1 - sum_pe) != 0 else 0
        return kappa

    @staticmethod
    def calculate_f1_per_class(confusion_matrix: np.ndarray, class_names: list[str]) -> dict:
        """Calculate F1 score per class."""
        results = {}

        for i, name in enumerate(class_names):
            if i >= confusion_matrix.shape[0]:
                continue

            tp = confusion_matrix[i, i]
            fp = confusion_matrix[:, i].sum() - tp
            fn = confusion_matrix[i, :].sum() - tp

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            results[name] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": int(confusion_matrix[i, :].sum()),
            }

        return results

    @staticmethod
    def calculate_iou_per_class(confusion_matrix: np.ndarray, class_names: list[str]) -> dict:
        """Calculate IoU (Jaccard Index) per class."""
        results = {}

        for i, name in enumerate(class_names):
            if i >= confusion_matrix.shape[0]:
                continue

            tp = confusion_matrix[i, i]
            fp = confusion_matrix[:, i].sum() - tp
            fn = confusion_matrix[i, :].sum() - tp

            iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0

            results[name] = {
                "iou": iou,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
            }

        return results

    @staticmethod
    def calculate_oa(confusion_matrix: np.ndarray) -> float:
        """Calculate Overall Accuracy."""
        return confusion_matrix.diagonal().sum() / confusion_matrix.sum()

    @staticmethod
    def generate_classification_report(confusion_matrix: np.ndarray, class_names: list[str]) -> ClassificationReport:
        """Generate comprehensive classification report."""
        from sklearn.metrics import f1_score

        y_true = []
        y_pred = []
        for i in range(confusion_matrix.shape[0]):
            for j in range(confusion_matrix.shape[1]):
                count = int(confusion_matrix[i, j])
                y_true.extend([i] * count)
                y_pred.extend([j] * count)

        oa = RemoteSensingMetricsCalculator.calculate_oa(confusion_matrix)
        kappa = RemoteSensingMetricsCalculator.calculate_kappa(confusion_matrix)
        per_class_f1 = RemoteSensingMetricsCalculator.calculate_f1_per_class(confusion_matrix, class_names)

        y_true_arr = np.array(y_true)
        y_pred_arr = np.array(y_pred)

        if len(np.unique(y_true_arr)) > 1:
            macro_f1 = f1_score(y_true_arr, y_pred_arr, average='macro', zero_division=0)
            weighted_f1 = f1_score(y_true_arr, y_pred_arr, average='weighted', zero_division=0)
        else:
            macro_f1 = 0.0
            weighted_f1 = 0.0

        return ClassificationReport(
            overall_accuracy=oa,
            kappa=kappa,
            macro_f1=macro_f1,
            weighted_f1=weighted_f1,
            per_class=per_class_f1,
        )

    @staticmethod
    def calculate_change_metrics(change_map: np.ndarray, reference_change: np.ndarray) -> dict:
        """Calculate change detection metrics."""
        tp = np.sum((change_map == 1) & (reference_change == 1))
        tn = np.sum((change_map == 0) & (reference_change == 0))
        fp = np.sum((change_map == 1) & (reference_change == 0))
        fn = np.sum((change_map == 0) & (reference_change == 1))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

        return {
            "overall_accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "producer_accuracy": recall,
            "user_accuracy": precision,
            "true_positives": int(tp),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
        }

    @staticmethod
    def calculate_morans_i(data: np.ndarray, spatial_weights: Optional[np.ndarray] = None) -> dict:
        """Calculate Moran's I for spatial autocorrelation."""
        from scipy import stats as scipy_stats

        flat_data = data.flatten()

        if spatial_weights is None:
            rows, cols = data.shape
            weights = np.zeros((rows * cols, rows * cols))

            for i in range(rows):
                for j in range(cols):
                    idx = i * cols + j
                    if i > 0:
                        weights[idx, (i - 1) * cols + j] = 1
                    if i < rows - 1:
                        weights[idx, (i + 1) * cols + j] = 1
                    if j > 0:
                        weights[idx, i * cols + (j - 1)] = 1
                    if j < cols - 1:
                        weights[idx, i * cols + (j + 1)] = 1

            row_sums = weights.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1
            spatial_weights = weights / row_sums

        n = len(flat_data)
        mean_val = np.mean(flat_data)
        centered = flat_data - mean_val
        z = centered / np.std(flat_data) if np.std(flat_data) > 0 else centered

        if n > 10000:
            spatial_weights_sample = spatial_weights[np.ix_(np.random.choice(n, 1000, replace=False), np.random.choice(n, 1000, replace=False))]
            z_sample = z[np.random.choice(n, 1000, replace=False)]
            numerator = np.sum(spatial_weights_sample * np.outer(z_sample, z_sample))
            denominator = np.sum(z_sample ** 2) / n
        else:
            numerator = np.sum(spatial_weights * np.outer(z, z))
            denominator = np.sum(z ** 2) / n

        morans_i = numerator / denominator if denominator != 0 else 0
        z_score = morans_i / 0.089
        p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_score)))

        return {
            "morans_i": float(morans_i),
            "z_score": float(z_score),
            "p_value": float(p_value),
            "interpretation": "clustered" if morans_i > 0.1 else "dispersed" if morans_i < -0.1 else "random",
        }
