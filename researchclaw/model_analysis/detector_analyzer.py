"""
Detector Analyzer

Generic object detection model analyzer for FCOS, RetinaNet, etc.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class DetectionResult:
    """Detection result container"""
    image_id: str
    detections: list[dict]
    scores: list[float]
    classes: list[int]


class DetectorAnalyzer:
    """Analyzer for general object detection models"""

    def __init__(self, model_type: str = "generic"):
        self.model_type = model_type

    def parse_coco_predictions(self, predictions_file: Path) -> list[DetectionResult]:
        """Parse COCO format predictions."""
        import json

        with open(predictions_file, 'r') as f:
            predictions = json.load(f)

        results = {}
        for pred in predictions:
            image_id = str(pred.get('image_id', ''))
            if image_id not in results:
                results[image_id] = DetectionResult(
                    image_id=image_id,
                    detections=[],
                    scores=[],
                    classes=[],
                )

            results[image_id].detections.append({
                'bbox': pred.get('bbox', []),
                'score': pred.get('score', 0),
                'category_id': pred.get('category_id', 0),
            })
            results[image_id].scores.append(pred.get('score', 0))
            results[image_id].classes.append(pred.get('category_id', 0))

        return list(results.values())

    def calculate_ap(self, predictions: list[dict], ground_truth: list[dict], iou_threshold: float = 0.5) -> float:
        """Calculate average precision."""
        if not ground_truth:
            return 0.0

        # Sort predictions by score
        sorted_preds = sorted(predictions, key=lambda x: x.get('score', 0), reverse=True)

        tp = []
        fp = []
        matched_gt = set()

        for pred in sorted_preds:
            matched = False
            for i, gt in enumerate(ground_truth):
                if i in matched_gt:
                    continue
                if pred.get('category_id') == gt.get('category_id'):
                    iou = self._calculate_iou(pred.get('bbox', []), gt.get('bbox', []))
                    if iou >= iou_threshold:
                        matched = True
                        matched_gt.add(i)
                        break

            tp.append(1 if matched else 0)
            fp.append(0 if matched else 1)

        # Calculate precision and recall
        tp_cumsum = np.cumsum(tp)
        fp_cumsum = np.cumsum(fp)

        recalls = tp_cumsum / len(ground_truth)
        precisions = tp_cumsum / (tp_cumsum + fp_cumsum)

        # Calculate AP using 11-point interpolation
        ap = 0.0
        for t in np.arange(0, 1.1, 0.1):
            p_mask = recalls >= t
            if p_mask.any():
                ap += np.max(precisions[p_mask])

        return ap / 11.0

    def _calculate_iou(self, bbox1: list, bbox2: list) -> float:
        """Calculate IoU between two bboxes [x, y, w, h] format."""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2

        x1_max = x1 + w1
        y1_max = y1 + h1
        x2_max = x2 + w2
        y2_max = y2 + h2

        inter_xmin = max(x1, x2)
        inter_ymin = max(y1, y2)
        inter_xmax = min(x1_max, x2_max)
        inter_ymax = min(y1_max, y2_max)

        if inter_xmax < inter_xmin or inter_ymax < inter_ymin:
            return 0.0

        inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
        bbox1_area = w1 * h1
        bbox2_area = w2 * h2
        union_area = bbox1_area + bbox2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0.0

    def calculate_ar(self, predictions: list[dict], ground_truth: list[dict], iou_thresholds: list[float] = None) -> dict:
        """Calculate average recall at different IoU thresholds."""
        if iou_thresholds is None:
            iou_thresholds = [0.5, 0.75, 0.95]

        results = {}
        for iou_thresh in iou_thresholds:
            recalls = []
            for gt_image in ground_truth:
                gt_bboxes = gt_image.get('bboxes', [])
                matched = 0

                for gt_bbox in gt_bboxes:
                    for pred in predictions:
                        pred_bbox = pred.get('bbox', [])
                        if self._calculate_iou(pred_bbox, gt_bbox) >= iou_thresh:
                            matched += 1
                            break
                    if matched >= len(gt_bboxes):
                        break

                recalls.append(matched / len(gt_bboxes) if gt_bboxes else 0)

            results[f"AR@{iou_thresh}"] = np.mean(recalls) if recalls else 0

        return results
