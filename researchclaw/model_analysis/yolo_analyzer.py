"""
YOLO Model Analyzer

Analyzes YOLO series model training results.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from .base import ModelDataParser, ModelData


@dataclass
class TrainingResults:
    """Training results container"""
    epochs: list[int]
    box_loss: list[float]
    cls_loss: list[float]
    dfl_loss: list[float]
    precision: list[float]
    recall: list[float]
    mAP50: list[float]
    mAP50_95: list[float]
    learning_rate: list[float]
    best_epoch: int
    best_mAP50: float
    config: dict = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame"""
        return pd.DataFrame({
            'epoch': self.epochs,
            'box_loss': self.box_loss,
            'cls_loss': self.cls_loss,
            'dfl_loss': self.dfl_loss,
            'precision': self.precision,
            'recall': self.recall,
            'mAP50': self.mAP50,
            'mAP50_95': self.mAP50_95,
            'learning_rate': self.learning_rate,
        })

    def summary(self) -> dict:
        """Get summary statistics"""
        return {
            "total_epochs": len(self.epochs),
            "best_epoch": self.best_epoch,
            "best_mAP50": self.best_mAP50,
            "final_mAP50": self.mAP50[-1] if self.mAP50 else 0,
            "final_precision": self.precision[-1] if self.precision else 0,
            "final_recall": self.recall[-1] if self.recall else 0,
        }


@dataclass
class DetectionMetrics:
    """Object detection metrics"""
    mAP50: float
    mAP50_95: float
    precision: float
    recall: float
    f1_score: float
    per_class_ap: dict[str, float]
    confusion_matrix: Optional[np.ndarray] = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "mAP50": self.mAP50,
            "mAP50_95": self.mAP50_95,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "per_class_ap": self.per_class_ap,
            "confusion_matrix": self.confusion_matrix.tolist() if self.confusion_matrix is not None else None,
        }


@dataclass
class TrainingCurves:
    """Training curve data"""
    epochs: list[int]
    loss_curves: dict[str, list[float]]
    metric_curves: dict[str, list[float]]
    learning_rate_schedule: list[float]

    def get_convergence_epoch(self, metric: str = "mAP50", threshold: float = 0.95) -> int:
        """Find epoch when metric reached threshold of final value"""
        if metric not in self.metric_curves or not self.metric_curves[metric]:
            return -1

        values = self.metric_curves[metric]
        final_value = values[-1]
        target = final_value * threshold

        for i, v in enumerate(values):
            if v >= target:
                return i

        return len(values) - 1

    def detect_overfitting(self, metric: str = "mAP50", window: int = 5) -> dict:
        """Detect overfitting based on metric trends"""
        if metric not in self.metric_curves or len(self.metric_curves[metric]) < window * 2:
            return {"overfitting": False, "reason": "insufficient_data"}

        values = self.metric_curves[metric]
        recent = values[-window:]
        best = max(values)

        if max(recent) < best * 0.95:
            return {
                "overfitting": True,
                "reason": "metric_decreased",
                "best_epoch": values.index(best),
                "current_vs_best": max(recent) / best if best > 0 else 0,
            }

        return {"overfitting": False, "reason": "metric_stable"}


@dataclass
class PRCurveData:
    """Precision-Recall curve data"""
    precision: list[float]
    recall: list[float]
    thresholds: list[float]
    ap: float
    class_names: list[str]


class YOLOAnalyzer:
    """Analyzer for YOLO series models (YOLOv5, v8, v11, etc.)"""

    def __init__(self, model_type: str = "yolov8"):
        self.model_type = model_type
        self.parser = ModelDataParser()

    def parse_training_results(self, results_dir: Path) -> TrainingResults:
        """Parse YOLO training results."""
        results_csv = Path(results_dir) / "results.csv"

        if not results_csv.exists():
            raise FileNotFoundError(f"results.csv not found in {results_dir}")

        df, metadata = self.parser._parse_yolo_results(results_csv)

        epoch_col = 'epoch' if 'epoch' in df.columns else df.columns[0]
        epochs = df[epoch_col].tolist() if epoch_col in df.columns else list(range(len(df)))

        def get_col(name: str) -> list:
            if name in df.columns:
                return df[name].tolist()
            return [0.0] * len(df)

        return TrainingResults(
            epochs=epochs,
            box_loss=get_col('box_loss'),
            cls_loss=get_col('cls_loss'),
            dfl_loss=get_col('dfl_loss'),
            precision=get_col('precision'),
            recall=get_col('recall'),
            mAP50=get_col('mAP50'),
            mAP50_95=get_col('mAP50_95'),
            learning_rate=get_col('learning_rate'),
            best_epoch=int(df['mAP50'].idxmax()) if 'mAP50' in df.columns and len(df) > 0 else 0,
            best_mAP50=float(df['mAP50'].max()) if 'mAP50' in df.columns and len(df) > 0 else 0,
            config=metadata,
        )

    def calculate_detection_metrics(
        self,
        predictions: list[dict],
        ground_truth: list[dict],
        iou_threshold: float = 0.5
    ) -> DetectionMetrics:
        """Calculate object detection metrics."""
        def calculate_iou(bbox1: list, bbox2: list) -> float:
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

        tp, fp, fn = 0, 0, 0
        class_tp, class_fp, class_fn = {}, {}, {}
        class_ap = {}

        for pred in predictions:
            matched = False
            for gt in ground_truth:
                if pred.get('class') == gt.get('class'):
                    iou = calculate_iou(pred['bbox'], gt['bbox'])
                    if iou >= iou_threshold:
                        tp += 1
                        class_tp[pred['class']] = class_tp.get(pred['class'], 0) + 1
                        matched = True
                        break
            if not matched:
                fp += 1
                class_fp[pred['class']] = class_fp.get(pred['class'], 0) + 1

        for gt in ground_truth:
            matched = False
            for pred in predictions:
                if pred.get('class') == gt.get('class'):
                    iou = calculate_iou(pred['bbox'], gt['bbox'])
                    if iou >= iou_threshold:
                        matched = True
                        break
            if not matched:
                fn += 1
                class_fn[gt['class']] = class_fn.get(gt['class'], 0) + 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        all_classes = set(class_tp.keys()) | set(class_fp.keys()) | set(class_fn.keys())
        for cls in all_classes:
            cls_tp = class_tp.get(cls, 0)
            cls_fp = class_fp.get(cls, 0)
            cls_fn = class_fn.get(cls, 0)
            cls_precision = cls_tp / (cls_tp + cls_fp) if (cls_tp + cls_fp) > 0 else 0
            cls_recall = cls_tp / (cls_tp + cls_fn) if (cls_tp + cls_fn) > 0 else 0
            class_ap[str(cls)] = 2 * cls_precision * cls_recall / (cls_precision + cls_recall) if (cls_precision + cls_recall) > 0 else 0

        return DetectionMetrics(
            mAP50=0.0,
            mAP50_95=0.0,
            precision=precision,
            recall=recall,
            f1_score=f1,
            per_class_ap=class_ap,
        )

    def analyze_training_curves(self, results_csv: Path) -> TrainingCurves:
        """Analyze training curves."""
        df, _ = self.parser._parse_yolo_results(results_csv)

        loss_curves = {}
        metric_curves = {}

        for col in ['box_loss', 'cls_loss', 'dfl_loss']:
            if col in df.columns:
                loss_curves[col] = df[col].tolist()

        for col in ['precision', 'recall', 'mAP50', 'mAP50_95']:
            if col in df.columns:
                metric_curves[col] = df[col].tolist()

        lr_col = 'learning_rate' if 'learning_rate' in df.columns else None
        if lr_col is None:
            for c in df.columns:
                if 'lr' in c.lower():
                    lr_col = c
                    break

        lr_schedule = df[lr_col].tolist() if lr_col and lr_col in df.columns else []

        epochs = df['epoch'].tolist() if 'epoch' in df.columns else list(range(len(df)))

        return TrainingCurves(
            epochs=epochs,
            loss_curves=loss_curves,
            metric_curves=metric_curves,
            learning_rate_schedule=lr_schedule,
        )

    def generate_pr_curve(
        self,
        predictions: list[dict],
        ground_truth: list[dict],
        num_thresholds: int = 100
    ) -> PRCurveData:
        """Generate Precision-Recall curve data."""
        sorted_preds = sorted(predictions, key=lambda x: x.get('score', 1.0), reverse=True)

        precision_points = []
        recall_points = []
        thresholds = []

        tp, fp = 0, 0
        total_gt = len(ground_truth)

        for i, pred in enumerate(sorted_preds):
            matched = any(
                pred.get('class') == gt.get('class')
                for gt in ground_truth
            )

            if matched:
                tp += 1
            else:
                fp += 1

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / total_gt if total_gt > 0 else 0

            precision_points.append(precision)
            recall_points.append(recall)
            thresholds.append(pred.get('score', 1.0 - i / len(sorted_preds)))

        ap = np.trapz(precision_points, recall_points) if recall_points else 0

        return PRCurveData(
            precision=precision_points,
            recall=recall_points,
            thresholds=thresholds,
            ap=ap,
            class_names=list(set(p.get('class', 'unknown') for p in predictions)),
        )

    def analyze_inference_speed(
        self,
        model_path: Path,
        test_images: list[Path],
        device: str = "cuda"
    ) -> dict:
        """Analyze inference speed."""
        try:
            from ultralytics import YOLO
        except ImportError:
            return {
                "error": "ultralytics not installed",
                "fps": 0,
                "avg_inference_ms": 0,
            }

        model = YOLO(str(model_path))

        import time
        times = []

        for img_path in test_images:
            start = time.time()
            model.predict(str(img_path), verbose=False, device=device)
            elapsed = time.time() - start
            times.append(elapsed * 1000)

        times = np.array(times)

        return {
            "fps": 1000 / times.mean() if times.mean() > 0 else 0,
            "avg_inference_ms": float(times.mean()),
            "p50_ms": float(np.percentile(times, 50)),
            "p95_ms": float(np.percentile(times, 95)),
            "p99_ms": float(np.percentile(times, 99)),
            "min_ms": float(times.min()),
            "max_ms": float(times.max()),
        }

    def compare_models(self, results_dir1: Path, results_dir2: Path) -> dict:
        """Compare two model training results."""
        results1 = self.parse_training_results(results_dir1)
        results2 = self.parse_training_results(results_dir2)

        return {
            "model1": results1.summary(),
            "model2": results2.summary(),
            "mAP50_diff": results1.best_mAP50 - results2.best_mAP50,
            "best_epoch_diff": results1.best_epoch - results2.best_epoch,
            "winner": "model1" if results1.best_mAP50 > results2.best_mAP50 else "model2",
        }
