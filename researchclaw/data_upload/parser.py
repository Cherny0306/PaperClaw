"""
Multi-format Data Parser

Supports: CSV, Excel, JSON, GeoTIFF, PNG/JPG, Parquet
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import pandas as pd
import numpy as np

try:
    import rasterio
    from rasterio.io import DatasetReader
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    DatasetReader = Any

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@dataclass
class ParsedData:
    """Parsed data container"""
    data: Union[pd.DataFrame, np.ndarray, dict]
    data_type: str  # 'tabular', 'raster', 'image', 'json'
    source_file: Path
    metadata: dict[str, Any]
    preview: Optional[pd.DataFrame] = None


class DataParser:
    """Multi-format data parser for research data"""

    SUPPORTED_FORMATS = {
        ".csv": "csv",
        ".xlsx": "excel",
        ".xls": "excel",
        ".json": "json",
        ".geojson": "geojson",
        ".tiff": "geotiff",
        ".tif": "geotiff",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".parquet": "parquet",
    }

    def __init__(self):
        self._parsers = {
            "csv": self._parse_csv,
            "excel": self._parse_excel,
            "json": self._parse_json,
            "geojson": self._parse_geojson,
            "geotiff": self._parse_geotiff,
            "image": self._parse_image,
            "parquet": self._parse_parquet,
        }

    def parse(self, file_path: Union[str, Path]) -> ParsedData:
        """
        Parse a data file based on its extension.

        Args:
            file_path: Path to the data file

        Returns:
            ParsedData object containing the parsed data and metadata
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported file format: {ext}")

        parser = self._parsers[self.SUPPORTED_FORMATS[ext]]
        return parser(path)

    def _parse_csv(self, path: Path) -> ParsedData:
        """Parse CSV file"""
        df = pd.read_csv(path)

        # Generate preview (first 5 rows)
        preview = df.head(5)

        # Generate metadata
        metadata = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "missing_values": df.isnull().sum().to_dict(),
            "numeric_columns": [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])],
            "categorical_columns": [col for col in df.columns if df[col].dtype == 'object'],
        }

        return ParsedData(
            data=df,
            data_type="tabular",
            source_file=path,
            metadata=metadata,
            preview=preview,
        )

    def _parse_excel(self, path: Path) -> ParsedData:
        """Parse Excel file"""
        # Read all sheets
        sheets = pd.read_excel(path, sheet_name=None)

        if len(sheets) == 1:
            # Single sheet - return as DataFrame
            sheet_name = list(sheets.keys())[0]
            df = sheets[sheet_name]
        else:
            # Multiple sheets - return as dict of DataFrames
            df = {name: sheet for name, sheet in sheets.items()}

        # Generate preview from first sheet
        if isinstance(df, dict):
            first_sheet = list(df.values())[0]
            preview = first_sheet.head(5)
            metadata = {
                "sheets": list(df.keys()),
                "rows_per_sheet": {name: len(sheet) for name, sheet in df.items()},
            }
        else:
            preview = df.head(5)
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
            }

        return ParsedData(
            data=df,
            data_type="tabular",
            source_file=path,
            metadata=metadata,
            preview=preview,
        )

    def _parse_json(self, path: Path) -> ParsedData:
        """Parse JSON file"""
        import json

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert to DataFrame if it's a list of records
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            df = pd.DataFrame(data)
            preview = df.head(5)
            metadata = {
                "records": len(data),
                "keys": list(data[0].keys()) if data else [],
            }
            result_data = df
        else:
            result_data = data
            preview = None
            metadata = {
                "type": type(data).__name__,
                "keys": list(data.keys()) if isinstance(data, dict) else None,
            }

        return ParsedData(
            data=result_data,
            data_type="json",
            source_file=path,
            metadata=metadata,
            preview=preview,
        )

    def _parse_geojson(self, path: Path) -> ParsedData:
        """Parse GeoJSON file"""
        import json
        import geopandas as gpd

        gdf = gpd.read_file(path)

        metadata = {
            "geometry_type": gdf.geom_type.unique().tolist(),
            "columns": list(gdf.columns),
            "rows": len(gdf),
            "crs": str(gdf.crs) if gdf.crs else None,
        }

        preview = gdf.head(5)

        return ParsedData(
            data=gdf,
            data_type="geospatial",
            source_file=path,
            metadata=metadata,
            preview=preview,
        )

    def _parse_geotiff(self, path: Path) -> ParsedData:
        """Parse GeoTIFF file"""
        if not HAS_RASTERIO:
            raise ImportError("rasterio is required to parse GeoTIFF files. Install with: pip install rasterio")

        with rasterio.open(path) as src:
            data = src.read()
            metadata = {
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "crs": str(src.crs),
                "bounds": src.bounds,
                "transform": src.transform.to_gdal(),
                "dtype": str(src.dtypes[0]),
                "nodata": src.nodata,
            }

            # Band statistics
            band_stats = []
            for i in range(src.count):
                band = src.read(i + 1)
                band_stats.append({
                    "band": i + 1,
                    "min": float(np.min(band)),
                    "max": float(np.max(band)),
                    "mean": float(np.mean(band)),
                    "std": float(np.std(band)),
                })
            metadata["band_statistics"] = band_stats

        preview_df = pd.DataFrame(band_stats)

        return ParsedData(
            data=data,
            data_type="raster",
            source_file=path,
            metadata=metadata,
            preview=preview_df,
        )

    def _parse_image(self, path: Path) -> ParsedData:
        """Parse image file (PNG, JPG)"""
        if not HAS_PIL:
            raise ImportError("PIL is required to parse image files. Install with: pip install Pillow")

        img = Image.open(path)

        metadata = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": path.stat().st_size,
        }

        # Convert to numpy array
        img_array = np.array(img)

        # Generate small preview
        preview_img = img.resize((100, 100))
        preview_array = np.array(preview_img)

        return ParsedData(
            data=img_array,
            data_type="image",
            source_file=path,
            metadata=metadata,
            preview=preview_df if (preview_df := self._image_to_df(preview_array)) is not None else None,
        )

    def _parse_parquet(self, path: Path) -> ParsedData:
        """Parse Parquet file"""
        df = pd.read_parquet(path)

        preview = df.head(5)

        metadata = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

        return ParsedData(
            data=df,
            data_type="tabular",
            source_file=path,
            metadata=metadata,
            preview=preview,
        )

    def _image_to_df(self, img_array: np.ndarray) -> Optional[pd.DataFrame]:
        """Convert image to preview DataFrame"""
        if len(img_array.shape) == 2:
            # Grayscale
            return pd.DataFrame(img_array)
        elif len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            # RGB - sample pixels
            rgb_data = img_array.reshape(-1, img_array.shape[2])[:, :3]
            return pd.DataFrame(rgb_data[:100], columns=["R", "G", "B"])
        return None

    def detect_format(self, path: Path) -> Optional[str]:
        """Auto-detect data format from file"""
        ext = path.suffix.lower()
        return self.SUPPORTED_FORMATS.get(ext)

    def is_supported(self, path: Union[str, Path]) -> bool:
        """Check if file format is supported"""
        ext = Path(path).suffix.lower()
        return ext in self.SUPPORTED_FORMATS
