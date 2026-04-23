"""
Remote Sensing Data Preprocessor

Handles GeoTIFF loading, band statistics, normalization, and tiling.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass

import numpy as np

try:
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    from rasterio.enums import ColorInterp
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    import xarray as xr
    HAS_XARRAY = True
except ImportError:
    HAS_XARRAY = False


@dataclass
class BandStatistics:
    """Band-wise statistics"""
    band: int
    min: float
    max: float
    mean: float
    std: float
    median: float
    percentile_1: float
    percentile_99: float
    no_data_count: int


@dataclass
class TileInfo:
    """Information about a tile"""
    index: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    width: int
    height: int


class RemoteSensingPreprocessor:
    """Preprocessor for remote sensing data"""

    def __init__(self):
        if not HAS_RASTERIO:
            raise ImportError("rasterio is required for remote sensing preprocessing")

    def load_geotiff(self, path: Path) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Load GeoTIFF image as numpy array.

        Args:
            path: Path to GeoTIFF file

        Returns:
            Tuple of (data array, metadata dict)
        """
        with rasterio.open(path) as src:
            data = src.read()  # Shape: (bands, height, width)
            metadata = {
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "crs": str(src.crs) if src.crs else None,
                "transform": src.transform.to_gdal(),
                "bounds": {
                    "left": src.bounds.left,
                    "right": src.bounds.right,
                    "top": src.bounds.top,
                    "bottom": src.bounds.bottom,
                },
                "dtype": str(src.dtypes[0]),
                "nodata": src.nodata,
                "color_interp": [str(src.colorinterp[i]) for i in range(src.count)] if hasattr(src, 'colorinterp') else None,
            }

            # Read band descriptions if available
            if src.descriptions:
                metadata["band_descriptions"] = [str(d) for d in src.descriptions if d]

        return data, metadata

    def load_as_datarray(self, path: Path) -> xr.DataArray:
        """
        Load GeoTIFF as xarray DataArray.

        Args:
            path: Path to GeoTIFF file

        Returns:
            xarray.DataArray with coordinates
        """
        if not HAS_XARRAY:
            raise ImportError("xarray is required for DataArray output")

        with rasterio.open(path) as src:
            data = src.read()

            # Create coordinates
            transform = src.transform
            x_coords = np.arange(src.width) * transform.a + transform.xoff
            y_coords = np.arange(src.height) * transform.e + transform.yoff

            coords = {
                "band": np.arange(1, src.count + 1),
                "y": y_coords,
                "x": x_coords,
            }

            da = xr.DataArray(
                data,
                dims=["band", "y", "x"],
                coords=coords,
                attrs={
                    "crs": str(src.crs) if src.crs else None,
                    "transform": str(src.transform),
                    "nodata": src.nodata,
                }
            )

        return da

    def extract_band_statistics(self, data: np.ndarray, nodata: Optional[float] = None) -> list[BandStatistics]:
        """
        Extract statistics for each band.

        Args:
            data: Array of shape (bands, height, width) or (height, width)
            nodata: Optional nodata value to exclude

        Returns:
            List of BandStatistics for each band
        """
        if data.ndim == 2:
            data = data[np.newaxis, :, :]

        stats = []
        for i in range(data.shape[0]):
            band = data[i]

            # Mask nodata values if specified
            if nodata is not None:
                mask = band != nodata
                band_masked = band[mask]
            else:
                band_masked = band.flatten()

            if len(band_masked) == 0:
                stats.append(BandStatistics(
                    band=i + 1,
                    min=np.nan,
                    max=np.nan,
                    mean=np.nan,
                    std=np.nan,
                    median=np.nan,
                    percentile_1=np.nan,
                    percentile_99=np.nan,
                    no_data_count=int(np.isnan(band).sum()) if not np.isnan(nodata) else 0,
                ))
            else:
                stats.append(BandStatistics(
                    band=i + 1,
                    min=float(np.min(band_masked)),
                    max=float(np.max(band_masked)),
                    mean=float(np.mean(band_masked)),
                    std=float(np.std(band_masked)),
                    median=float(np.median(band_masked)),
                    percentile_1=float(np.percentile(band_masked, 1)),
                    percentile_99=float(np.percentile(band_masked, 99)),
                    no_data_count=int(np.sum(band == nodata)) if nodata is not None else 0,
                ))

        return stats

    def normalize(
        self,
        data: np.ndarray,
        method: str = "minmax",
        nodata: Optional[float] = None
    ) -> np.ndarray:
        """
        Normalize data using specified method.

        Args:
            data: Input array
            method: 'minmax', 'zscore', or 'percentile'
            nodata: Optional nodata value to preserve

        Returns:
            Normalized array
        """
        if nodata is not None:
            mask = data != nodata
            data_copy = data.astype(np.float32).copy()
        else:
            mask = slice(None)
            data_copy = data.astype(np.float32).copy()

        if method == "minmax":
            min_val = np.nanmin(data_copy[mask])
            max_val = np.nanmax(data_copy[mask])
            if max_val > min_val:
                data_copy[mask] = (data_copy[mask] - min_val) / (max_val - min_val)

        elif method == "zscore":
            mean_val = np.nanmean(data_copy[mask])
            std_val = np.nanstd(data_copy[mask])
            if std_val > 0:
                data_copy[mask] = (data_copy[mask] - mean_val) / std_val

        elif method == "percentile":
            p1 = np.nanpercentile(data_copy[mask], 1)
            p99 = np.nanpercentile(data_copy[mask], 99)
            if p99 > p1:
                data_copy[mask] = (data_copy[mask] - p1) / (p99 - p1)
                data_copy = np.clip(data_copy, 0, 1)

        else:
            raise ValueError(f"Unknown normalization method: {method}")

        return data_copy

    def tile_image(
        self,
        data: np.ndarray,
        tile_size: int,
        overlap: int = 0,
        nodata: Optional[float] = None
    ) -> tuple[list[np.ndarray], list[TileInfo]]:
        """
        Split image into tiles.

        Args:
            data: Input array of shape (bands, height, width) or (height, width)
            tile_size: Size of each tile (square)
            overlap: Overlap between tiles in pixels
            nodata: Optional nodata value

        Returns:
            Tuple of (list of tiles, list of TileInfo)
        """
        if data.ndim == 2:
            data = data[np.newaxis, :, :]

        height, width = data.shape[1], data.shape[2]
        tiles = []
        tile_infos = []

        step = tile_size - overlap
        tile_idx = 0

        for row in range(0, height, step):
            for col in range(0, width, step):
                row_end = min(row + tile_size, height)
                col_end = min(col + tile_size, width)

                tile = data[:, row:row_end, col:col_end]

                # Pad if smaller than tile_size
                if tile.shape[1] < tile_size or tile.shape[2] < tile_size:
                    pad_row = tile_size - tile.shape[1]
                    pad_col = tile_size - tile.shape[2]
                    pad_width = ((0, 0), (0, pad_row), (0, pad_col))
                    tile = np.pad(tile, pad_width, mode='constant', constant_values=nodata or 0)

                tiles.append(tile)
                tile_infos.append(TileInfo(
                    index=tile_idx,
                    row_start=row,
                    row_end=row_end,
                    col_start=col,
                    col_end=col_end,
                    width=tile.shape[2],
                    height=tile.shape[1],
                ))

                tile_idx += 1

        return tiles, tile_infos

    def resample(
        self,
        data: np.ndarray,
        target_shape: tuple[int, int],
        resampling: str = "bilinear"
    ) -> np.ndarray:
        """
        Resample data to target shape.

        Args:
            data: Input array of shape (bands, height, width)
            target_shape: Target (height, width)
            resampling: Resampling method ('nearest', 'bilinear', 'cubic')

        Returns:
            Resampled array
        """
        resampling_map = {
            "nearest": Resampling.nearest,
            "bilinear": Resampling.bilinear,
            "cubic": Resampling.cubic,
            "lanczos": Resampling.lanczos,
        }

        method = resampling_map.get(resampling, Resampling.bilinear)

        from rasterio.warp import calculate_default_transform, reproject

        # Create source and destination arrays
        src_height, src_width = data.shape[1], data.shape[2]
        dst_height, dst_width = target_shape

        resampled = np.zeros((data.shape[0], dst_height, dst_width), dtype=data.dtype)

        for band_idx in range(data.shape[0]):
            src_band = data[band_idx]
            dst_band = resampled[band_idx]

            # Simple resampling using skimage or scipy
            try:
                from skimage.transform import resize
                resampled[band_idx] = resize(
                    src_band,
                    (dst_height, dst_width),
                    order=1 if resampling in ["bilinear", "cubic"] else 0,
                    preserve_range=True,
                    anti_aliasing=True
                )
            except ImportError:
                # Fallback to scipy
                from scipy.ndimage import zoom
                zoom_factors = (dst_height / src_height, dst_width / src_width)
                resampled[band_idx] = zoom(src_band, zoom_factors, order=1)

        return resampled

    def calculate_ndvi(
        self,
        data: np.ndarray,
        nir_band: int = 0,
        red_band: int = 1
    ) -> np.ndarray:
        """
        Calculate Normalized Difference Vegetation Index.

        Args:
            data: Array of shape (bands, height, width)
            nir_band: Index of NIR band
            red_band: Index of Red band

        Returns:
            NDVI array of shape (height, width)
        """
        nir = data[nir_band].astype(np.float32)
        red = data[red_band].astype(np.float32)

        # Avoid division by zero
        denominator = nir + red
        ndvi = np.where(
            denominator != 0,
            (nir - red) / denominator,
            0
        )

        return ndvi

    def calculate_ndwi(
        self,
        data: np.ndarray,
        green_band: int = 1,
        nir_band: int = 0
    ) -> np.ndarray:
        """
        Calculate Normalized Difference Water Index.

        Args:
            data: Array of shape (bands, height, width)
            green_band: Index of Green band
            nir_band: Index of NIR band

        Returns:
            NDWI array of shape (height, width)
        """
        green = data[green_band].astype(np.float32)
        nir = data[nir_band].astype(np.float32)

        denominator = green + nir
        ndwi = np.where(
            denominator != 0,
            (green - nir) / denominator,
            0
        )

        return ndwi

    def stack_bands(
        self,
        paths: list[Path],
        target_crs: Optional[str] = None
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Stack multiple band files into single array.

        Args:
            paths: List of band file paths
            target_crs: Optional target CRS for reprojection

        Returns:
            Tuple of (stacked array, metadata)
        """
        bands = []
        ref_meta = None

        for i, path in enumerate(paths):
            with rasterio.open(path) as src:
                band = src.read(1)

                if ref_meta is None:
                    ref_meta = {
                        "width": src.width,
                        "height": src.height,
                        "crs": str(src.crs),
                        "transform": src.transform,
                    }

                    if target_crs:
                        ref_transform, ref_width, ref_height = calculate_default_transform(
                            src.crs, target_crs, src.width, src.height, *src.bounds
                        )
                        ref_meta["width"] = ref_width
                        ref_meta["height"] = ref_height
                        ref_meta["transform"] = ref_transform

                bands.append(band)

        stacked = np.stack(bands, axis=0)
        return stacked, ref_meta

    def reproject_to_wgs84(
        self,
        data: np.ndarray,
        src_crs: str,
        src_transform
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """
        Reproject data to WGS84 (EPSG:4326).

        Args:
            data: Input array of shape (bands, height, width)
            src_crs: Source CRS string
            src_transform: Source transform

        Returns:
            Tuple of (reprojected data, new metadata)
        """
        dst_crs = "EPSG:4326"

        transform, width, height = calculate_default_transform(
            src_crs, dst_crs, data.shape[2], data.shape[1],
            *rasterio.transform.array_bounds(height, width, src_transform)
        )

        reprojected = np.zeros((data.shape[0], height, width), dtype=data.dtype)

        for band_idx in range(data.shape[0]):
            reproject(
                source=data[band_idx],
                destination=reprojected[band_idx],
                src_transform=src_transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear
            )

        metadata = {
            "width": width,
            "height": height,
            "crs": dst_crs,
            "transform": transform,
        }

        return reprojected, metadata
