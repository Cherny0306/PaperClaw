"""
Data Validation Module

Validates data integrity, format, and schema compliance.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np


class ValidationLevel(Enum):
    """Validation strictness level"""
    LENIENT = "lenient"      # Only critical errors
    MODERATE = "moderate"    # Errors and warnings
    STRICT = "strict"        # All issues including style


@dataclass
class ValidationError:
    """Single validation error"""
    field: str
    message: str
    severity: str  # 'error', 'warning', 'info'
    row_index: Optional[int] = None


@dataclass
class ValidationResult:
    """Validation result container"""
    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def all_issues(self) -> list[ValidationError]:
        """All issues sorted by severity"""
        return self.errors + self.warnings + self.info

    def summary(self) -> str:
        """Generate human-readable summary"""
        parts = []
        if self.error_count > 0:
            parts.append(f"{self.error_count} error(s)")
        if self.warning_count > 0:
            parts.append(f"{self.warning_count} warning(s)")
        if self.is_valid:
            parts.append("Validation passed")
        else:
            parts.append("Validation failed")
        return ", ".join(parts)


class DataValidator:
    """Data validation for research datasets"""

    # Common schema templates
    SCHEMAS = {
        "training_data": {
            "required": ["sample_id", "image_path"],
            "optional": ["label", "split", "metadata"],
            "numeric": ["accuracy", "loss", "confidence"],
        },
        "validation_metrics": {
            "required": ["model_id", "metric_name", "value"],
            "optional": ["confidence_interval", "sample_size"],
            "numeric": ["value", "lower_ci", "upper_ci"],
        },
        "model_results": {
            "required": ["model_name", "mAP", "precision", "recall"],
            "optional": ["f1_score", "inference_time_ms", "params_m"],
            "numeric": ["mAP", "precision", "recall", "f1_score"],
        },
        "detection_results": {
            "required": ["image_id", "class_id", "confidence", "bbox"],
            "optional": ["gt_bbox", "iou", "tp", "fp", "fn"],
            "numeric": ["confidence", "iou"],
        },
    }

    def __init__(self, level: ValidationLevel = ValidationLevel.MODERATE):
        self.level = level

    def validate(self, data: Union[pd.DataFrame, Path], schema: Optional[str] = None) -> ValidationResult:
        """
        Validate data against optional schema.

        Args:
            data: DataFrame or path to data file
            schema: Optional schema name from SCHEMAS

        Returns:
            ValidationResult with all issues
        """
        if isinstance(data, Path):
            data = self._load_data(data)

        if not isinstance(data, pd.DataFrame):
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    field="data",
                    message="Data must be a pandas DataFrame",
                    severity="error"
                )]
            )

        result = ValidationResult(is_valid=True)

        # Schema validation if provided
        if schema and schema in self.SCHEMAS:
            self._validate_schema(data, self.SCHEMAS[schema], result)

        # General validation
        self._check_required_columns(data, result)
        self._check_data_types(data, result)
        self._detect_duplicates(data, result)
        self._detect_outliers(data, result)
        self._check_missing_values(data, result)

        return result

    def _load_data(self, path: Path) -> pd.DataFrame:
        """Load data from file"""
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path)
        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(path)
        elif ext == ".parquet":
            return pd.read_parquet(path)
        else:
            raise ValueError(f"Unsupported format for validation: {ext}")

    def _validate_schema(self, df: pd.DataFrame, schema: dict, result: ValidationResult) -> None:
        """Validate against schema"""
        required = schema.get("required", [])
        numeric = schema.get("numeric", [])

        # Check required columns
        missing = [col for col in required if col not in df.columns]
        if missing:
            result.errors.append(ValidationError(
                field="schema",
                message=f"Missing required columns: {', '.join(missing)}",
                severity="error"
            ))
            result.is_valid = False

        # Check numeric columns
        for col in numeric:
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                result.warnings.append(ValidationError(
                    field=col,
                    message=f"Expected numeric type, got {df[col].dtype}",
                    severity="warning"
                ))

    def _check_required_columns(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Check if required columns exist"""
        # For tabular data, check for at least one column
        if len(df.columns) == 0:
            result.errors.append(ValidationError(
                field="columns",
                message="DataFrame has no columns",
                severity="error"
            ))
            result.is_valid = False

    def _check_data_types(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Check data type consistency"""
        for col in df.columns:
            # Check for mixed types in object columns
            if df[col].dtype == 'object':
                unique_types = df[col].dropna().apply(type).unique()
                if len(unique_types) > 1:
                    result.warnings.append(ValidationError(
                        field=col,
                        message=f"Mixed types detected: {[t.__name__ for t in unique_types]}",
                        severity="warning"
                    ))

    def _detect_duplicates(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Detect duplicate rows"""
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            pct = duplicates / len(df) * 100
            result.warnings.append(ValidationError(
                field="rows",
                message=f"Found {duplicates} duplicate rows ({pct:.1f}%)",
                severity="warning"
            ))

    def _detect_outliers(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Detect outliers using IQR method"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if df[col].isnull().all():
                continue

            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR

            outliers = ((df[col] < lower) | (df[col] > upper)).sum()
            if outliers > 0:
                pct = outliers / len(df) * 100
                result.warnings.append(ValidationError(
                    field=col,
                    message=f"Found {outliers} outliers ({pct:.1f}%) using IQR method",
                    severity="info"
                ))

    def _check_missing_values(self, df: pd.DataFrame, result: ValidationResult) -> None:
        """Check for missing values"""
        for col in df.columns:
            missing = df[col].isnull().sum()
            if missing > 0:
                pct = missing / len(df) * 100
                if pct > 50:
                    result.warnings.append(ValidationError(
                        field=col,
                        message=f"Column '{col}' has {missing} missing values ({pct:.1f}%)",
                        severity="warning"
                    ))
                else:
                    result.info.append(ValidationError(
                        field=col,
                        message=f"Column '{col}' has {missing} missing values ({pct:.1f}%)",
                        severity="info"
                    ))

    def validate_geotiff(self, path: Path) -> ValidationResult:
        """Validate GeoTIFF file"""
        result = ValidationResult(is_valid=True)

        try:
            import rasterio

            with rasterio.open(path) as src:
                # Check dimensions
                if src.width < 1 or src.height < 1:
                    result.errors.append(ValidationError(
                        field="dimensions",
                        message=f"Invalid dimensions: {src.width}x{src.height}",
                        severity="error"
                    ))
                    result.is_valid = False

                # Check band count
                if src.count < 1:
                    result.errors.append(ValidationError(
                        field="bands",
                        message="No bands found in raster",
                        severity="error"
                    ))
                    result.is_valid = False

                # Check CRS
                if src.crs is None:
                    result.warnings.append(ValidationError(
                        field="crs",
                        message="No CRS defined for raster",
                        severity="warning"
                    ))

                # Check nodata values
                if src.nodata is None:
                    result.info.append(ValidationError(
                        field="nodata",
                        message="No nodata value specified",
                        severity="info"
                    ))

        except ImportError:
            result.errors.append(ValidationError(
                field="dependency",
                message="rasterio is required to validate GeoTIFF files",
                severity="error"
            ))
            result.is_valid = False
        except Exception as e:
            result.errors.append(ValidationError(
                field="file",
                message=f"Failed to open GeoTIFF: {str(e)}",
                severity="error"
            ))
            result.is_valid = False

        return result

    def check_required_columns(self, df: pd.DataFrame, required: list[str]) -> bool:
        """Check if required columns exist"""
        missing = [col for col in required if col not in df.columns]
        return len(missing) == 0

    def check_data_types_match(self, df: pd.DataFrame, schema: dict[str, str]) -> bool:
        """Check if columns match expected types"""
        dtype_map = {
            "int": [np.int8, np.int16, np.int32, np.int64],
            "float": [np.float16, np.float32, np.float64],
            "str": [object],
            "bool": [bool],
        }

        for col, expected in schema.items():
            if col not in df.columns:
                return False
            expected_types = dtype_map.get(expected, [])
            if df[col].dtype not in expected_types:
                return False
        return True
