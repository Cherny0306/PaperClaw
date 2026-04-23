"""
Data Service

Handles data upload, parsing, validation, and preprocessing.
"""

from pathlib import Path
from typing import Any, Optional, Union
import base64
import tempfile
import os

from researchclaw.data_upload import DataParser, DataValidator, RemoteSensingPreprocessor


class DataService:
    """Service for handling data operations"""

    def __init__(self):
        self.parser = DataParser()
        self.validator = DataValidator()
        self.preprocessor = RemoteSensingPreprocessor()
        self._datasets = {}  # In-memory dataset storage

    def upload_data(
        self,
        file_content: str,
        filename: str,
        data_type: str = "training",
        description: str = ""
    ) -> dict:
        """
        Upload and parse data file.

        Args:
            file_content: Base64 encoded file content
            filename: Original filename
            data_type: Type of data (training, validation, results)
            description: Optional description

        Returns:
            Dictionary with upload result
        """
        try:
            # Decode file content
            if file_content.startswith('data:'):
                # Handle data URL format
                file_content = file_content.split(',')[1]

            file_bytes = base64.b64decode(file_content)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
                tmp.write(file_bytes)
                tmp_path = Path(tmp.name)

            try:
                # Parse the file
                parsed_data = self.parser.parse(tmp_path)

                # Validate
                validation_result = self.validator.validate(parsed_data.data)

                # Generate dataset ID
                import uuid
                dataset_id = f"ds_{uuid.uuid4().hex[:8]}"

                # Store metadata
                self._datasets[dataset_id] = {
                    "id": dataset_id,
                    "filename": filename,
                    "data_type": data_type,
                    "description": description,
                    "data_type_format": parsed_data.data_type,
                    "source_file": str(parsed_data.source_file),
                    "metadata": parsed_data.metadata,
                    "is_valid": validation_result.is_valid,
                    "validation_summary": validation_result.summary(),
                }

                # Convert DataFrame to records for JSON serialization
                if hasattr(parsed_data.data, 'to_dict'):
                    self._datasets[dataset_id]["data"] = parsed_data.data.to_dict(orient='records')
                elif isinstance(parsed_data.data, dict):
                    self._datasets[dataset_id]["data"] = parsed_data.data

                # Preview data
                if parsed_data.preview is not None:
                    self._datasets[dataset_id]["preview"] = parsed_data.preview.to_dict(orient='records') if hasattr(parsed_data.preview, 'to_dict') else parsed_data.preview

                return {
                    "success": True,
                    "dataset_id": dataset_id,
                    "dataset": self._datasets[dataset_id],
                    "validation": {
                        "is_valid": validation_result.is_valid,
                        "error_count": validation_result.error_count,
                        "warning_count": validation_result.warning_count,
                        "errors": [{"field": e.field, "message": e.message} for e in validation_result.errors],
                        "warnings": [{"field": w.field, "message": w.message} for w in validation_result.warnings],
                    }
                }

            finally:
                # Clean up temp file
                if tmp_path.exists():
                    os.unlink(tmp_path)

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_dataset(self, dataset_id: str) -> Optional[dict]:
        """Get dataset by ID"""
        return self._datasets.get(dataset_id)

    def list_datasets(self) -> list[dict]:
        """List all datasets"""
        return [
            {
                "id": ds["id"],
                "filename": ds["filename"],
                "data_type": ds["data_type"],
                "data_type_format": ds["data_type_format"],
                "is_valid": ds["is_valid"],
                "metadata": ds.get("metadata", {})
            }
            for ds in self._datasets.values()
        ]

    def validate_dataset(self, dataset_id: str) -> dict:
        """Re-validate a dataset"""
        if dataset_id not in self._datasets:
            return {"success": False, "error": "Dataset not found"}

        dataset = self._datasets[dataset_id]

        # Re-parse and validate
        try:
            source_file = Path(dataset["source_file"])
            if source_file.exists():
                parsed_data = self.parser.parse(source_file)
                validation_result = self.validator.validate(parsed_data.data)

                dataset["is_valid"] = validation_result.is_valid
                dataset["validation_summary"] = validation_result.summary()

                return {
                    "success": True,
                    "is_valid": validation_result.is_valid,
                    "errors": [{"field": e.field, "message": e.message} for e in validation_result.errors],
                    "warnings": [{"field": w.field, "message": w.message} for w in validation_result.warnings],
                }
            else:
                return {
                    "success": False,
                    "error": "Source file not found"
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def preprocess_geotiff(self, dataset_id: str, operations: list[str]) -> dict:
        """Preprocess GeoTIFF data"""
        if dataset_id not in self._datasets:
            return {"success": False, "error": "Dataset not found"}

        dataset = self._datasets[dataset_id]

        try:
            source_file = Path(dataset["source_file"])

            if not source_file.exists():
                return {"success": False, "error": "Source file not found"}

            # Load GeoTIFF
            data, metadata = self.preprocessor.load_geotiff(source_file)

            results = {}

            for op in operations:
                if op == "normalize":
                    data_normalized = self.preprocessor.normalize(data)
                    results["normalized"] = {
                        "shape": data_normalized.shape,
                        "min": float(data_normalized.min()),
                        "max": float(data_normalized.max()),
                    }
                elif op == "statistics":
                    stats = self.preprocessor.extract_band_statistics(data)
                    results["statistics"] = [
                        {
                            "band": s.band,
                            "min": s.min,
                            "max": s.max,
                            "mean": s.mean,
                            "std": s.std,
                        }
                        for s in stats
                    ]
                elif op == "tile":
                    tiles, tile_infos = self.preprocessor.tile_image(data, tile_size=512)
                    results["tiles"] = {
                        "count": len(tiles),
                        "tile_size": tiles[0].shape if tiles else (0, 0, 0),
                    }

            return {
                "success": True,
                "metadata": metadata,
                "results": results
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_dataset(self, dataset_id: str) ->