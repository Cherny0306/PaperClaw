"""
Base Model Data Parser

Provides unified interface for parsing various model training result formats.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np


class DataFormat(Enum):
    """Supported model data formats"""
    YOLO_RESULTS_CSV = "yolo_results_csv"
    YOLO_CONFUSION_MATRIX = "yolo_confusion_matrix"
    YOLO_ARGS = "yolo_args"
    COCO_PREDICTIONS = "coco_predictions"
    COCO_ANNOTATIONS = "coco_annotations"
    CSV_METRICS = "csv_metrics"
    JSON_METRICS = "json_metrics"
    TENSORBOARD_LOGS = "tensorboard_logs"
    UNKNOWN = "unknown"


@dataclass
class ModelData:
    """Unified container for model data"""
    format_type: DataFormat
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    source_file: Optional[Path] = None

    def to_dataframe(self) -> Optional[pd.DataFrame]:
        """Convert to DataFrame if applicable"""
        if isinstance(self.data, pd.DataFrame):
            return self.data
        if isinstance(self.data, dict):
            return pd.DataFrame([self.data])
        if isinstance(self.data, list) and len(self.data) > 0:
            if isinstance(self.data[0], dict):
                return pd.DataFrame(self.data)
        return None


class ModelDataParser:
    """Parser for various model training data formats"""

    SUPPORTED_FORMATS = {
        "results.csv": DataFormat.YOLO_RESULTS_CSV,
        "confusion_matrix.csv": DataFormat.YOLO_CONFUSION_MATRIX,
        "args.yaml": DataFormat.YOLO_ARGS,
        "predictions.json": DataFormat.COCO_PREDICTIONS,
        "instances.json": DataFormat.COCO_ANNOTATIONS,
        "metrics.csv": DataFormat.CSV_METRICS,
        "metrics.json": DataFormat.JSON_METRICS,
    }

    def __init__(self):
        self._parsers = {
            DataFormat.YOLO_RESULTS_CSV: self._parse_yolo_results,
            DataFormat.YOLO_CONFUSION_MATRIX: self._parse_confusion_matrix,
            DataFormat.YOLO_ARGS: self._parse_yolo_args,
            DataFormat.COCO_PREDICTIONS: self._parse_coco_predictions,
            DataFormat.CSV_METRICS: self._parse_csv_metrics,
            DataFormat.JSON_METRICS: self._parse_json_metrics,
        }

    def auto_detect_format(self, data_dir: Union[str, Path]) -> Optional[DataFormat]:
        """Auto-detect data format from directory contents"""
        data_path = Path(data_dir)

        if not data_path.exists():
            return None

        for file_name, fmt in self.SUPPORTED_FORMATS.items():
            if (data_path / file_name).exists():
                return fmt

        for subdir in data_path.iterdir():
            if subdir.is_dir():
                detected = self.auto_detect_format(subdir)
                if detected:
                    return detected

        return None

    def parse(self, data_path: Union[str, Path], format_type: Optional[DataFormat] = None) -> ModelData:
        """Parse data from path."""
        path = Path(data_path)

        if path.is_file():
            return self._parse_file(path, format_type)
        elif path.is_dir():
            return self._parse_directory(path, format_type)
        else:
            raise ValueError(f"Path does not exist: {path}")

    def _parse_file(self, path: Path, format_type: Optional[DataFormat]) -> ModelData:
        """Parse a single file"""
        if format_type is None:
            format_type = self.SUPPORTED_FORMATS.get(path.name, DataFormat.UNKNOWN)

        if format_type in self._parsers:
            data, metadata = self._parsers[format_type](path)
            return ModelData(
                format_type=format_type,
                data=data,
                metadata=metadata,
                source_file=path
            )

        if path.suffix == '.csv':
            return ModelData(
                format_type=DataFormat.CSV_METRICS,
                data=pd.read_csv(path),
                metadata={"file": str(path)},
                source_file=path
            )
        elif path.suffix == '.json':
            return ModelData(
                format_type=DataFormat.JSON_METRICS,
                data=self._load_json(path),
                metadata={"file": str(path)},
                source_file=path
            )

        return ModelData(
            format_type=DataFormat.UNKNOWN,
            data=None,
            metadata={"file": str(path), "error": "Unknown format"},
            source_file=path
        )

    def _parse_directory(self, path: Path, format_type: Optional[DataFormat]) -> ModelData:
        """Parse a directory of model results"""
        results = {}

        results_csv = path / "results.csv"
        if results_csv.exists():
            results["training_curves"] = self._parse_yolo_results(results_csv)

        confusion_csv = path / "confusion_matrix.csv"
        if confusion_csv.exists():
            results["confusion_matrix"] = self._parse_confusion_matrix(confusion_csv)

        args_yaml = path / "args.yaml"
        if args_yaml.exists():
            results["config"] = self._parse_yolo_args(args_yaml)

        weights_dir = path / "weights"
        if weights_dir.exists():
            best_weights = weights_dir / "best.pt"
            last_weights = weights_dir / "last.pt"
            results["weights"] = {
                "best": str(best_weights) if best_weights.exists() else None,
                "last": str(last_weights) if last_weights.exists() else None,
            }

        return ModelData(
            format_type=DataFormat.YOLO_RESULTS_CSV,
            data=results,
            metadata={
                "directory": str(path),
                "files_found": list(path.iterdir()),
            },
            source_file=path
        )

    def _parse_yolo_results(self, path: Path) -> tuple[pd.DataFrame, dict]:
        """Parse YOLO results.csv"""
        df = pd.read_csv(path)

        column_mapping = {
            'epoch': 'epoch',
            'train/box_loss': 'box_loss',
            'train/cls_loss': 'cls_loss',
            'train/dfl_loss': 'dfl_loss',
            'metrics/precision(B)': 'precision',
            'metrics/recall(B)': 'recall',
            'metrics/mAP50(B)': 'mAP50',
            'metrics/mAP50-95(B)': 'mAP50_95',
            'val/box_loss': 'val_box_loss',
            'val/cls_loss': 'val_cls_loss',
            'val/dfl_loss': 'val_dfl_loss',
            'lr/pg0': 'learning_rate',
        }

        df_renamed = df.copy()
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df_renamed = df_renamed.rename(columns={old_name: new_name})

        metadata = {
            "total_epochs": len(df),
            "best_epoch": int(df['mAP50(B)'].idxmax()) if 'mAP50(B)' in df.columns else 0,
            "final_mAP50": float(df['mAP50(B)'].iloc[-1]) if 'mAP50(B)' in df.columns else 0,
        }

        return df_renamed, metadata

    def _parse_confusion_matrix(self, path: Path) -> tuple[np.ndarray, dict]:
        """Parse confusion matrix CSV"""
        df = pd.read_csv(path, header=None)
        matrix = df.values

        metadata = {
            "shape": matrix.shape,
            "sum": float(matrix.sum()),
        }

        return matrix, metadata

    def _parse_yolo_args(self, path: Path) -> tuple[dict, dict]:
        """Parse YOLO args.yaml"""
        try:
            import yaml
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            return config, {"file": str(path)}
        except ImportError:
            return {}, {"file": str(path), "error": "yaml not available"}

    def _parse_coco_predictions(self, path: Path) -> tuple[list[dict], dict]:
        """Parse COCO predictions JSON"""
        import json

        with open(path, 'r') as f:
            predictions = json.load(f)

        metadata = {
            "count": len(predictions) if isinstance(predictions, list) else 0,
        }

        return predictions, metadata

    def _parse_csv_metrics(self, path: Path) -> tuple[pd.DataFrame, dict]:
        """Parse generic CSV metrics"""
        df = pd.read_csv(path)

        metadata = {
            "rows": len(df),
            "columns": list(df.columns),
        }

        return df, metadata

    def _parse_json_metrics(self, path: Path) -> tuple[dict, dict]:
        """Parse generic JSON metrics"""
        data = self._load_json(path)

        metadata = {
            "keys": list(data.keys()) if isinstance(data, dict) else None,
        }

        return data, metadata

    def _load_json(self, path: Path) -> dict:
        """Load JSON file"""
        import json

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def parse_training_config(self, results_dir: Path) -> dict:
        """Parse training configuration from results directory"""
        args_file = results_dir / "args.yaml"

        if not args_file.exists():
            return {}

        try:
            import yaml
            with open(args_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception:
            return {}
