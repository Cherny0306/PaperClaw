"""
Classifier Analyzer

Analyzer for image classification models.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ClassificationMetrics:
    """Classification metrics container"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: np.ndarray
    per_class_metrics: dict


class ClassifierAnalyzer:
    """Analyzer for image classification models"""

    def __init__(self, model_type: str = "generic"):
        self.model_type = model_type

    def calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        class_names: Optional[list[str]] = None
    ) -> ClassificationMetrics:
        """Calculate classification metrics."""
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

        if class_names is None:
            classes = np.unique(np.concatenate([y_true, y_pred]))
            class_names = [f"Class_{c}" for c in classes]

        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        cm = confusion_matrix(y_true, y_pred)

        # Per-class metrics
        per_class = {}
        for i, name in enumerate(class_names):
            if i < cm.shape[0]:
                tp = cm[i, i]
                fp = cm[:, i].sum() - tp
                fn = cm[i, :].sum() - tp

                class_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                class_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                class_f1 = 2 * class_precision * class_recall / (class_precision + class_recall) if (class_precision + class_recall) > 0 else 0

                per_class[name] = {
                    "precision": float(class_precision),
                    "recall": float(class_recall),
                    "f1": float(class_f1),
                    "support": int(cm[i, :].sum()),
                }

        return ClassificationMetrics(
            accuracy=float(accuracy),
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            confusion_matrix=cm,
            per_class_metrics=per_class,
        )

    def analyze_top_k_accuracy(
        self,
        probabilities: np.ndarray,
        true_labels: np.ndarray,
        k: int = 5
    ) -> dict:
        """Analyze top-k accuracy."""
        if probabilities.ndim != 2:
            raise ValueError("Probabilities must be 2D array")

        # Get top-k predictions
        top_k_preds = np.argsort(probabilities, axis=1)[:, -k:]

        # Check if true label is in top-k
        correct = 0
        for i, true_label in enumerate(true_labels):
            if true_label in top_k_preds[i]:
                correct += 1

        return {
            f"top_{k}_accuracy": correct / len(true_labels),
            "total_samples": len(true_labels),
            "correct_predictions": correct,
        }

    def analyze_confidence_calibration(
        self,
        probabilities: np.ndarray,
        true_labels: np.ndarray,
        n_bins: int = 10
    ) -> dict:
        """Analyze model confidence calibration (ECE)."""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        bin_accuracies = []
        bin_confidences = []
        bin_counts = []

        for i in range(n_bins):
            bin_lower = bin_boundaries[i]
            bin_upper = bin_boundaries[i + 1]

            in_bin = (probabilities.max(axis=1) > bin_lower) & (probabilities.max(axis=1) <= bin_upper)
            count = np.sum(in_bin)

            if count > 0:
                avg_confidence = np.mean(probabilities.max(axis=1)[in_bin])
                avg_accuracy = np.mean(np.argmax(probabilities[in_bin], axis=1) == true_labels[in_bin])

                bin_accuracies.append(float(avg_accuracy))
                bin_confidences.append(float(avg_confidence))
                bin_counts.append(int(count))

                ece += (count / len(true_labels)) * abs(avg_accuracy - avg_confidence)
            else:
                bin_accuracies.append(0.0)
                bin_confidences.append((bin_lower + bin_upper) / 2)
                bin_counts.append(0)

        return {
            "ece": float(ece),
            "bin_accuracies": bin_accuracies,
            "bin_confidences": bin_confidences,
            "bin_counts": bin_counts,
        }
