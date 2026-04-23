"""
Remote Sensing Visualizer

Visualization tools for remote sensing data.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class VisualizationData:
    """Visualization data container"""
    type: str
    data: dict
    title: str
    colormap: str = "viridis"


class RemoteSensingVisualizer:
    """Visualizer for remote sensing data"""

    def __init__(self):
        self.figures = []

    def prepare_band_composite(self, raster: np.ndarray, bands: tuple[int, int, int] = (0, 1, 2), normalize: bool = True) -> np.ndarray:
        """Prepare RGB band composite."""
        r = raster[bands[0]]
        g = raster[bands[1]]
        b = raster[bands[2]]

        if normalize:
            for band, arr in [(0, r), (1, g), (2, b)]:
                p2 = np.percentile(arr, 2)
                p98 = np.percentile(arr, 98)
                arr_normalized = np.clip((arr - p2) / (p98 - p2), 0, 1)
                if band == 0:
                    r = arr_normalized
                elif band == 1:
                    g = arr_normalized
                else:
                    b = arr_normalized

        composite = np.stack([r, g, b], axis=-1)
        return composite

    def prepare_ndvi_visualization(self, ndvi: np.ndarray, clip_range: tuple[float, float] = (-1, 1)) -> np.ndarray:
        """Prepare NDVI for visualization."""
        ndvi_clipped = np.clip(ndvi, clip_range[0], clip_range[1])
        ndvi_norm = (ndvi_clipped - clip_range[0]) / (clip_range[1] - clip_range[0])

        r = np.where(ndvi_norm < 0.5, 0.5 - ndvi_norm, 0)
        g = ndvi_norm
        b = np.where(ndvi_norm > 0.5, ndvi_norm - 0.5, 0)

        rgb = np.stack([r, g, b], axis=-1)
        return np.clip(rgb, 0, 1)

    def prepare_classification_overlay(self, image: np.ndarray, classification: np.ndarray, class_colors: dict, alpha: float = 0.5) -> np.ndarray:
        """Create classification overlay on image."""
        overlay = image.copy()

        for class_id, color in class_colors.items():
            mask = classification == class_id
            for c, col in enumerate(color[:3]):
                overlay[:, :, c][mask] = alpha * col + (1 - alpha) * overlay[:, :, c][mask]

        return overlay

    def prepare_change_detection_visualization(self, change_map: np.ndarray, image_before: np.ndarray, image_after: np.ndarray) -> dict:
        """Prepare change detection visualization."""
        if image_before.ndim == 3:
            rgb_before = self.prepare_band_composite(image_before)
            rgb_after = self.prepare_band_composite(image_after)
        else:
            rgb_before = image_before
            rgb_after = image_after

        change_rgb = np.zeros((*change_map.shape, 3))
        stable_mask = change_map == 0
        change_rgb[stable_mask] = [0.3, 0.3, 0.3]
        change_rgb[~stable_mask] = [1.0, 0.0, 0.0]

        return {
            "before": rgb_before,
            "after": rgb_after,
            "change_overlay": change_rgb,
            "change_mask": change_map,
        }

    def generate_statistics_heatmap(self, data: np.ndarray, window_size: int = 3) -> dict:
        """Generate sliding window statistics heatmap."""
        from scipy.ndimage import uniform_filter, minimum_filter, maximum_filter

        mean_map = uniform_filter(data.astype(float), size=window_size)
        std_map = np.sqrt(uniform_filter((data.astype(float) - mean_map) ** 2, size=window_size))
        min_map = minimum_filter(data.astype(float), size=window_size)
        max_map = maximum_filter(data.astype(float), size=window_size)

        return {
            "mean": mean_map,
            "std": std_map,
            "min": min_map,
            "max": max_map,
        }

    def prepare_confusion_matrix_visualization(self, confusion_matrix: np.ndarray, class_names: list[str], normalize: bool = True) -> dict:
        """Prepare confusion matrix for visualization."""
        if normalize:
            row_sums = confusion_matrix.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1
            cm_normalized = confusion_matrix / row_sums
        else:
            cm_normalized = confusion_matrix.astype(float)

        return {
            "matrix": cm_normalized.tolist(),
            "class_names": class_names,
            "raw_counts": confusion_matrix.tolist() if not normalize else None,
        }

    def prepare_scale_analysis_chart(self, scale_metrics: dict) -> dict:
        """Prepare scale analysis chart data."""
        return {
            "categories": ["Small", "Medium", "Large"],
            "recall_values": [
                scale_metrics.get("small_object_recall", 0),
                scale_metrics.get("medium_object_recall", 0),
                scale_metrics.get("large_object_recall", 0),
            ],
            "map_values": [
                scale_metrics.get("small_object_map", 0),
                scale_metrics.get("medium_object_map", 0),
                scale_metrics.get("large_object_map", 0),
            ],
        }

    def prepare_timeline_chart(self, time_series: dict) -> dict:
        """Prepare time series chart data."""
        return {
            "timestamps": time_series.get("timestamps", []),
            "values": time_series.get("values", []),
            "moving_average": time_series.get("moving_average", []),
            "trend_direction": time_series.get("trend", {}).get("direction", "unknown"),
            "trend_slope": time_series.get("trend", {}).get("slope", 0),
        }
