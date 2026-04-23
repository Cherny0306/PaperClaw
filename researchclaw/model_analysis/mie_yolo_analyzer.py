"""
MIE-YOLO Specialized Analyzer

Medical/Industrial/Earth Observation YOLO model analysis.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field

import numpy as np

from .yolo_analyzer import YOLOAnalyzer


@dataclass
class MultispectralAnalysis:
    """Multispectral data analysis results"""
    band_statistics: list[dict]
    band_correlations: np.ndarray
    band_names: list[str]
    recommendations: list[str]


@dataclass
class RemoteSensingMetrics:
    """Remote sensing specific detection metrics"""
    edge_accuracy: float
    small_object_recall: float
    medium_object_recall: float
    large_object_recall: float
    background_rejection_rate: float
    scale_sensitivity: dict[str, float]


@dataclass
class ScaleAnalysis:
    """Detection scale analysis results"""
    small_object_map: float
    medium_object_map: float
    large_object_map: float
    scale_curve: list[dict]
    optimal_scale_range: tuple[float, float]


@dataclass
class FalseDetectionAnalysis:
    """False detection analysis results"""
    false_positive_rate: float
    background_false_positive_rate: float
    class_confusion_matrix: dict
    recommendations: list[str]


class MIEYOLOAnalyzer(YOLOAnalyzer):
    """MIE-YOLO (Medical/Industrial/Earth Observation) specialized analyzer"""

    def __init__(self):
        super().__init__(model_type="mie_yolo")

    def analyze_multispectral_data(self, multispectral_images: list[Path]) -> MultispectralAnalysis:
        """Analyze multispectral image data."""
        try:
            import rasterio
        except ImportError:
            return MultispectralAnalysis(
                band_statistics=[],
                band_correlations=np.array([]),
                band_names=[],
                recommendations=["Install rasterio for multispectral analysis"]
            )

        all_band_stats = []
        all_bands = []

        for img_path in multispectral_images:
            with rasterio.open(img_path) as src:
                for i in range(src.count):
                    band = src.read(i + 1)
                    all_bands.append(band)
                    all_band_stats.append({
                        "band": i + 1,
                        "min": float(band.min()),
                        "max": float(band.max()),
                        "mean": float(band.mean()),
                        "std": float(band.std()),
                    })

        band_correlations = np.corrcoef([b.flatten() for b in all_bands]) if all_bands else np.array([])

        recommendations = []
        if len(all_band_stats) >= 3:
            recommendations.append("Consider band combination for vegetation indices (NDVI)")

        return MultispectralAnalysis(
            band_statistics=all_band_stats,
            band_correlations=band_correlations,
            band_names=[f"Band {i+1}" for i in range(len(all_band_stats))],
            recommendations=recommendations,
        )

    def calculate_remote_sensing_metrics(
        self,
        predictions: list[dict],
        ground_truth: list[dict],
        image_size: tuple[int, int]
    ) -> RemoteSensingMetrics:
        """Calculate remote sensing specific detection metrics."""
        img_width, img_height = image_size
        img_area = img_width * img_height

        small_threshold = 0.01
        medium_threshold = 0.05
        large_threshold = 0.05

        def get_object_size(bbox: list) -> float:
            x1, y1, x2, y2 = bbox
            return (x2 - x1) * (y2 - y1) / img_area

        def get_size_category(bbox: list) -> str:
            size = get_object_size(bbox)
            if size < small_threshold:
                return "small"
            elif size < large_threshold:
                return "medium"
            else:
                return "large"

        gt_by_size = {"small": [], "medium": [], "large": []}
        for gt in ground_truth:
            category = get_size_category(gt['bbox'])
            gt_by_size[category].append(gt)

        def calculate_recall(preds: list, gt_list: list, iou_threshold: float = 0.5) -> float:
            if not gt_list:
                return 0.0

            matched = 0
            for gt in gt_list:
                for pred in preds:
                    if pred.get('class') == gt.get('class'):
                        if self._bbox_iou(pred['bbox'], gt['bbox']) >= iou_threshold:
                            matched += 1
                            break

            return matched / len(gt_list) if gt_list else 0.0

        small_recall = calculate_recall(predictions, gt_by_size["small"])
        medium_recall = calculate_recall(predictions, gt_by_size["medium"])
        large_recall = calculate_recall(predictions, gt_by_size["large"])

        edge_threshold = 0.05
        edge_gt = [gt for gt in ground_truth if self._is_edge_object(gt['bbox'], edge_threshold, img_width, img_height)]

        if edge_gt:
            edge_tp = sum(
                1 for gt in edge_gt
                for pred in predictions
                if pred.get('class') == gt.get('class') and self._bbox_iou(pred['bbox'], gt['bbox']) >= 0.5
            )
            edge_accuracy = edge_tp / len(edge_gt)
        else:
            edge_accuracy = 1.0

        total_preds = len(predictions)
        background_preds = sum(1 for p in predictions if not any(
            self._bbox_iou(p['bbox'], gt['bbox']) >= 0.5 for gt in ground_truth
        ))
        background_rejection_rate = background_preds / total_preds if total_preds > 0 else 0

        scale_sensitivity = {
            "small_object_sensitivity": small_recall / (medium_recall + 0.01),
            "medium_object_sensitivity": medium_recall / (large_recall + 0.01),
            "large_object_sensitivity": large_recall / (small_recall + 0.01),
        }

        return RemoteSensingMetrics(
            edge_accuracy=edge_accuracy,
            small_object_recall=small_recall,
            medium_object_recall=medium_recall,
            large_object_recall=large_recall,
            background_rejection_rate=background_rejection_rate,
            scale_sensitivity=scale_sensitivity,
        )

    def _bbox_iou(self, bbox1: list, bbox2: list) -> float:
        """Calculate IoU between two bboxes"""
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

    def _is_edge_object(self, bbox: list, threshold: float, img_width: int, img_height: int) -> bool:
        """Check if object is near image edge"""
        x1, y1, x2, y2 = bbox
        margin_x = img_width * threshold
        margin_y = img_height * threshold

        return (x1 < margin_x or x2 > img_width - margin_x or
                y1 < margin_y or y2 > img_height - margin_y)

    def analyze_detection_scale(self, predictions: list[dict]) -> ScaleAnalysis:
        """Analyze detection performance across different scales."""
        sizes = []
        for pred in predictions:
            x1, y1, x2, y2 = pred['bbox']
            size = (x2 - x1) * (y2 - y1)
            sizes.append(size)

        if not sizes:
            return ScaleAnalysis(
                small_object_map=0.0,
                medium_object_map=0.0,
                large_object_map=0.0,
                scale_curve=[],
                optimal_scale_range=(0, 1),
            )

        sizes = np.array(sizes)
        percentiles = [10, 25, 50, 75, 90]

        scale_points = []
        for p in percentiles:
            threshold = np.percentile(sizes, p)
            scale_preds = [pr for pr in predictions if (pr['bbox'][2] - pr['bbox'][0]) * (pr['bbox'][3] - pr['bbox'][1]) <= threshold]
            scale_map = np.mean([pr.get('score', 0) for pr in scale_preds]) if scale_preds else 0
            scale_points.append({
                "percentile": p,
                "threshold": float(threshold),
                "map_estimate": float(scale_map),
            })

        q1, q3 = np.percentile(sizes, [25, 75])

        small_map = np.mean([p.get('score', 0) for p in predictions if (p['bbox'][2] - p['bbox'][0]) * (p['bbox'][3] - p['bbox'][1]) <= q1])
        medium_map = np.mean([p.get('score', 0) for p in predictions if q1 < (p['bbox'][2] - p['bbox'][0]) * (p['bbox'][3] - p['bbox'][1]) <= q3])
        large_map = np.mean([p.get('score', 0) for p in predictions if (p['bbox'][2] - p['bbox'][0]) * (p['bbox'][3] - p['bbox'][1]) > q3])

        return ScaleAnalysis(
            small_object_map=float(small_map),
            medium_object_map=float(medium_map),
            large_object_map=float(large_map),
            scale_curve=scale_points,
            optimal_scale_range=(float(q1), float(q3)),
        )

    def generate_detection_heatmap(
        self,
        image: np.ndarray,
        predictions: list[dict],
        output_size: tuple[int, int] = (100, 100)
    ) -> np.ndarray:
        """Generate detection density heatmap."""
        h, w = image.shape[:2] if image.ndim == 3 else image.shape
        heatmap = np.zeros((output_size[1], output_size[0]))

        scale_y = h / output_size[1]
        scale_x = w / output_size[0]

        for pred in predictions:
            x1, y1, x2, y2 = pred['bbox']
            score = pred.get('score', 1.0)

            hx1, hy1 = int(x1 / scale_x), int(y1 / scale_y)
            hx2, hy2 = int(x2 / scale_x), int(y2 / scale_y)

            for y in range(max(0, hy1), min(output_size[1], hy2 + 1)):
                for x in range(max(0, hx1), min(output_size[0], hx2 + 1)):
                    heatmap[y, x] += score

        if heatmap.max() > 0:
            heatmap = heatmap / heatmap.max()

        return heatmap

    def analyze_false_detections(
        self,
        predictions: list[dict],
        ground_truth: list[dict]
    ) -> FalseDetectionAnalysis:
        """Analyze false detections."""
        total_preds = len(predictions)
        if total_preds == 0:
            return FalseDetectionAnalysis(
                false_positive_rate=0.0,
                background_false_positive_rate=0.0,
                class_confusion_matrix={},
                recommendations=["No predictions to analyze"]
            )

        fp = 0
        background_fp = 0
        class_confusion = {}

        for pred in predictions:
            matched = False
            for gt in ground_truth:
                if pred.get('class') == gt.get('class'):
                    iou = self._bbox_iou(pred['bbox'], gt['bbox'])
                    if iou >= 0.5:
                        matched = True
                        break

            if not matched:
                fp += 1
                if pred.get('score', 1.0) < 0.5:
                    background_fp += 1

            pred_class = pred.get('class', 'unknown')
            gt_class = None
            for gt in ground_truth:
                if self._bbox_iou(pred['bbox'], gt['bbox']) >= 0.5:
                    gt_class = gt.get('class', 'unknown')
                    break

            if gt_class and gt_class != pred_class:
                key = f"{gt_class}->{pred_class}"
                class_confusion[key] = class_confusion.get(key, 0) + 1

        fp_rate = fp / total_preds
        bg_fp_rate = background_fp / total_preds if total_preds > 0 else 0

        recommendations = []
        if bg_fp_rate > 0.3:
            recommendations.append("Consider increasing confidence threshold to reduce background false positives")
        if class_confusion:
            top_confusion = sorted(class_confusion.items(), key=lambda x: x[1], reverse=True)[:3]
            recommendations.append(f"Common confusions: {', '.join([f'{k}({v})' for k, v in top_confusion])}")

        return FalseDetectionAnalysis(
            false_positive_rate=fp_rate,
            background_false_positive_rate=bg_fp_rate,
            class_confusion_matrix=class_confusion,
            recommendations=recommendations,
        )
